# ADR-0005 — Network topology, and what the rate limiter does when Redis is gone

- **Status:** Accepted
- **Date:** 2026-09-25
- **Decides:** `AD-002` (three networks), `AD-008` (limiter fails open)
- **Related requirements:** `FR-CTR-005`, `FR-CTR-006`, `FR-CACHE-006`, `FR-CACHE-007`, `BR-SEC-001`, `BR-CACHE-007`, `NFR-SEC-001`, `NFR-REL-007`
- **Rubric:** `RUB-G-03` (4 marks), `RUB-E-03` (4 marks), engineering-notes Q7

## Why this ADR exists

Both decisions below are Tier 1 — they change the shape of the system and are expensive to reverse — and both were resolved in `OPEN-DECISIONS.md` and then implemented directly in module design documents, with no ADR. The specification audit (`docs/audit/01-specification-audit.md`, S2-19 and the deviation register) flagged that as the gap it is: the first deviates from the brief's prescribed topology, and the second trades security for availability on the only control protecting a paid resource. Those are exactly the two decisions a viva will probe, and "it is in a module design document" is a worse answer than a page.

Two decisions share one ADR because they share one cause: `internal: true` is a blunt instrument, and both the egress problem and the fail-open question follow from putting infrastructure behind it.

---

## Decision 1 — Three networks, not two

**Three Compose networks:**

| Network | Members | Property |
|---|---|---|
| `edge` | frontend, backend | Ordinary bridge. Browser-facing traffic. |
| `internal` | backend, database, cache, ollama | **`internal: true`** — no route to the outside world |
| `egress` | backend | Ordinary bridge. The backend's outbound path to Groq. |

The backend is the only service on more than one network; it is on all three. The frontend is on `edge` only. The database, cache and Ollama are on `internal` only.

### Context

The brief's §3.2 prescribes two networks, `edge` and `internal`, and marks the property that follows: `docker compose exec frontend ping database` must fail. It then points at the tension itself — "`internal: true` means those containers cannot reach the internet, so an `LLMTriage` provider calling Groq must live on a service that can. Work out where that leaves your architecture" — and makes it engineering-notes question 7.

So the brief asks for a resolution and does not prescribe one.

### Options

| Option | Consequence |
|---|---|
| **A. Two networks.** The backend joins `edge` and `internal`; outbound traffic leaves over `edge`, which is an ordinary bridge and permits it. | Zero extra surface. Matches the brief's YAML literally. But the backend's ability to reach the internet becomes a side effect of the network that exists for browser traffic — true by accident rather than by intent. |
| **B. Three networks.** Add a named `egress` bridge the backend also joins. | About six lines of YAML. The outbound path is named, so the architecture diagram and the ADR both say what it is for. The isolation property the rubric marks is unchanged. |
| **C. An egress proxy sidecar** on its own network, called by the backend over `internal`. | Closest to production practice. An extra container, an extra failure mode, extra latency, and more to build and defend. |

### Decision and reasoning

**Option B.** The deciding argument is that the marked property — the frontend cannot reach the data tier — holds identically under A and B, so the choice is free on marks and is decided entirely by which one explains itself. A network called `egress` that only the backend joins states the intent; the same capability arriving as a property of `edge` does not.

The honest counter-argument, recorded because it is real: a marker reading `RUB-G-03`, whose text says "Two networks with `internal: true`", may count networks rather than assess isolation. That risk is accepted and mitigated by stating the deviation in three places — here, in `FR-CTR-005`, and in engineering-notes Q7 — rather than by quietly conforming. `RUB-G-03` in `RUBRIC-TRACEABILITY.md` now carries the same note.

### Consequences

**Good.**
- Q7 has a real answer instead of an excuse.
- The three networks map one-to-one onto three sentences: browser traffic, data traffic, outbound traffic.
- `FR-CTR-005`, `AD-002` and `RUB-G-03` now say the same thing; before this ADR, the requirement said two and the decision said three, and the 4-mark rubric row cited both.

**Costs and limits — stated plainly.**
- **Ollama cannot pull its own weights.** It sits on `internal` with no egress, so `ollama pull` can never succeed from inside the running stack. This was previously hand-waved as "the pull happens into the volume". It is now `make pull-models` (`AD-046`): a one-time step running a throwaway container on `egress`, a named prerequisite in the README, with the Ollama healthcheck failing on an empty volume so the failure is legible rather than a hang.
- **This segmentation is a Compose property and does not carry to Kubernetes.** There is no `NetworkPolicy`, so any pod in the namespace can reach `postgres`. The `ClusterIP`-only Services prevent external exposure, not lateral movement. A compromised frontend pod on Kubernetes *can* reach the database. Recorded in `NFR-SEC-001`, `BR-SEC-001` and `docs/NON-GOALS.md`, with the fix named: a default-deny policy plus three allow rules. Claiming the marked property holds everywhere would be false.
- **The backend on three networks is a larger blast radius than on two**, in the sense that compromising it reaches everything. That was already true with two networks — it is the only bridge either way — so the third network adds a name, not an exposure.

---

## Decision 2 — When Redis is unreachable, the rate limiter fails open, loudly

**Allow the request. Emit one `ERROR` log per occurrence. Increment `rate_limiter_unavailable_total`.**

### Context

The limiter protects `POST /api/complaints`, the only path that spends LLM quota. If Redis is gone the limiter cannot count, and something has to happen. Failing closed rejects every submission; failing open accepts every submission with no limit.

This is a security-versus-availability trade on the one control guarding a paid resource, which is why it earns a page.

### Options

| Option | Consequence |
|---|---|
| **Fail closed.** No counter, no request. | The quota is never exceeded. But a cache outage becomes a total submission outage: a citizen reporting a burst main gets a 503 because a cache is down. The system's whole reason for existing stops working for a dependency that is, by definition, rebuildable. |
| **Fail open.** Allow, log, count. | Submissions keep working. For the duration of the outage there is no rate limit, so a caller who happens to be looping during it can burn quota. |
| **Fail open with a local fallback limiter** — an in-process counter while Redis is down. | Partial protection. But an in-process limiter across N replicas permits N times the limit, which is the exact bug `BR-CACHE-004` exists to forbid; implementing it as a fallback means shipping the wrong thing on purpose and having to explain why it is acceptable here and not there. |

### Decision and reasoning

**Fail open, loudly** — and the reasoning is not "availability matters more", which would be a preference rather than an argument. It is that **the exposure window is bounded by a mechanism already present.** `/ready` returns 503 when Redis is unreachable (`FR-BE-008`), so Kubernetes removes the pod from the Service. The pod stops receiving traffic. The window in which an unlimited path is reachable is the readiness probe's detection time — `periodSeconds: 5` × `failureThreshold: 2`, so roughly 10 seconds — not the duration of the outage.

Failing closed would trade that bounded, observable, already-instrumented window for a total outage of the system's primary function. That is a worse trade, and it is worse for a specific reason rather than as a matter of taste.

### Consequences

**Good.**
- A cache outage degrades one property instead of stopping the service.
- The condition is observable three ways: an `ERROR` log per occurrence, a counter, and a 503 on `/ready`. It cannot happen silently, which is the part that makes failing open defensible at all.
- The full per-feature degradation table is in `FR-CACHE-006`, so every Redis-dependent behaviour has a stated answer rather than just this one.

**Costs and limits — stated plainly.**
- **For that window, `POST /api/complaints` is unlimited.** A caller looping during it spends real quota. Accepted, because the window is short and instrumented.
- **The counter name matters and was wrong.** `AD-008` originally wrote `rate_limiter_unavailable` while `BR-CACHE-007` wrote `rate_limiter_unavailable_total`. A metric with two spellings has none — an alert on one would never fire. Fixed to `rate_limiter_unavailable_total` in both, matching the `_total` suffix every other counter uses.
- **Redis eviction can produce the same effect without Redis being down.** One Redis serves four workloads on database 0 with `maxmemory-policy allkeys-lru` (`FR-CACHE-005`), so under memory pressure a live limiter counter can be evicted. The effect is a silently reset window rather than a logged outage — this path is *not* covered by the `ERROR` log above. It is bounded by `maxmemory 256mb` against four small workloads, and named here because it is the one way this decision's instrumentation can be bypassed.
- **The limiter bounds one caller, not aggregate spend.** Ten IPs at ten requests a minute each is a hundred requests a minute, above a typical free tier. No global cap exists; recorded in `BR-CACHE-005` and `docs/NON-GOALS.md`. Failing open is therefore the second-order risk, and the absence of a global cap is the first-order one.

---

## Verification

| Claim | How it is proven |
|---|---|
| The frontend cannot reach the database (Compose) | `FR-CTR-005`: `ping` and `getent hosts` both fail, captured to `docs/evidence/network-isolation.txt` |
| The backend can reach the database and the internet | The same capture, from the backend, succeeding |
| Ollama works with no egress | `make pull-models` then a triage with `TRIAGE_PROVIDER=ollama` and no network |
| The limiter is distributed, not per-process | `FR-CACHE-007`: 4 replicas, 30 requests, exactly 10 × 201 and 20 × 429 |
| Fail-open behaviour is real and logged | `FR-CACHE-006`: with Redis stopped, `POST` returns 201, one `ERROR` is logged, the counter increments, `/ready` returns 503 naming Redis |
