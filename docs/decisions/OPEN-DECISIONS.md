# Civic-Station — Open Architectural Decisions

**Status:** **RESOLVED.** All 44 Round 1 decisions were accepted in Round 2; the audit
remediation of 2026-09-25 revised eight of them and added `AD-045`–`AD-056`. The resolution
log is at the bottom of this file and is authoritative — if a design document disagrees with
it, the log wins.
**Companion documents:** `../requirements/MODULE-MAP.md`, `../requirements/FUNCTIONAL-REQUIREMENTS.md`, `../requirements/BUSINESS-RULES.md`

## How this document works

Round 1 extracted the requirements and the rules. This page lists every decision those requirements leave open, and **no design document may be written until the decisions it depends on are marked RESOLVED here.** All of them now are, so that gate is open.

Each entry states: the question, why it matters, the realistic options with their consequences, what it blocks, and a recommendation. The recommendation is what a competent team would pick by default; it is not a decision until a human accepts it.

Decisions are grouped into three tiers:

- **Tier 1 — Architectural.** Change the shape of the system. A wrong answer is expensive to reverse. These are the ones to actually think about.
- **Tier 2 — Contractual.** Fix a behaviour that other code depends on. Cheap to decide, expensive to leave ambiguous.
- **Tier 3 — Tooling.** Preference and convention. Listed for the record; accepting the recommendation is a fine answer.

Four of these decisions must become committed ADRs regardless of what is chosen, because the rubric marks them:

| ADR | Decisions it records |
|-----|----------------------|
| ADR-0001 — provider interface | `AD-005`, `AD-006`, `AD-007`, `AD-009` |
| ADR-0002 — frontend runtime config | `AD-001` |
| ADR-0003 — deploy by SHA | `AD-034` |
| ADR-0004 — PII and data governance | `AD-003` |

A fifth, ADR-0005, records `AD-002` (network topology) and `AD-008` (limiter fail-open), because both are Tier 1 architectural decisions that deviate from or extend the brief.

**The resolution log is at the bottom of this file and is complete.**

---

# Tier 1 — Architectural decisions

## AD-001 — How does the frontend learn the backend's address?
**Why it matters.** A Vite build inlines `import.meta.env` values into static JavaScript at build time. If the API URL is baked in, the image is environment-specific and build-once-deploy-many is destroyed for the frontend. This is 3 marks directly (rubric B) and underpins `NFR-PORT-001`.

| Option | Consequence |
|---|---|
| **A. nginx reverse-proxies `/api` to the backend.** The frontend uses relative URLs only and never knows a backend host. | Simplest correct answer. No CORS at all in the browser's view — same origin. The proxy target is an nginx config value templated from an environment variable at container start. Adds one hop and means nginx config differs per environment (via `envsubst`), not the JavaScript. |
| **B. `/config.js` generated at container start** from environment variables, loaded before the app bundle, exposing `window.__CONFIG__`. | Keeps the network path direct (browser → backend). Requires real CORS configuration on the backend, and a small entrypoint script. The typed client must read config at runtime rather than at module load. |
| **C. Both** — proxy in Kubernetes via Ingress path routing, `/config.js` in Compose. | Two mechanisms, two failure modes, one more thing to explain at viva. Not recommended. |

**Blocks:** M1.5, M1.4, M6.2, M6.3, M7.4 (Ingress), `FR-FE-014`, `FR-BE-012` (CORS scope).
**Recommendation: A.** It removes CORS as a category of bug, matches the Ingress `/` and `/api` routing already required by `FR-K8S-004`, and makes `NFR-PORT-001` trivially demonstrable.

---

## AD-002 — Where does outbound traffic to a hosted LLM leave the system?
**Why it matters.** `internal: true` means containers on that network have no route to the internet. The backend must reach Groq/Gemini. This conflict is a named engineering-notes question (§5.2 Q7) and a marked design point.

| Option | Consequence |
|---|---|
| **A. Backend is on both networks and the triage call originates from the backend.** The backend is already the only bridge; `edge` is a normal bridge network with outbound access. | Zero extra components. The point of `internal: true` is preserved exactly — the *data tier* has no egress, the frontend has no route to data. The backend's dual membership is the deliberate, documented exception. |
| **B. Separate egress network** (`edge` stays frontend-facing; add an `egress` bridge network the backend also joins) so the outbound path is explicit rather than incidental. | More honest architecture diagram: three networks, each with one purpose. Slightly more Compose surface. Reads very well in an ADR and at viva. |
| **C. Route triage through a dedicated sidecar/service** that lives on the egress network and is called by the backend over `internal`. | Most segregated, closest to a real egress-proxy pattern. Extra container, extra failure mode, extra latency, and more to build in one week. |

**Blocks:** M6.5, M5.2, engineering notes Q7.
**Recommendation: B.** It costs about six lines of YAML over option A and turns an "incidental" property into a stated design decision, which is exactly what the notes question is asking for.

---

## AD-003 — What complaint data is allowed to leave the machine, and to whom?
**Why it matters.** Citizen complaints contain names, addresses and phone numbers. Free-tier Gemini may use inputs to improve models. This is a required ADR (`ADR-0004`) and the problem statement says a thoughtful answer here is worth more in an interview than the rest of the repository.

| Option | Consequence |
|---|---|
| **A. Send only the complaint body and location; never send `reporter_contact`; redact detectable phone numbers, emails and long digit strings from the text before sending.** | Strongest position, small implementation cost (one regex-based redaction function, one test). Slight classification-quality cost that is measurable and worth reporting. |
| **B. Send only the complaint body and location, no redaction of in-text PII; accept and document the exposure.** | Honest and defensible if the provider's terms are stated and the residual risk named. Cheaper. Weaker at viva than A. |
| **C. Use a self-hosted model (Ollama) as the production path** so nothing leaves the machine at all. | Eliminates the governance question entirely; costs classification quality and speed, and the assignment explicitly accepts this trade-off with no mark penalty. |

**Blocks:** M5.2, M5.7, `NFR-PRIV-001/002/003`, ADR-0004.
**Recommendation: A**, with the redaction function and its limitations documented. Note that A and C are compatible: redact *and* keep Ollama as the offline path.

---

## AD-004 — Is triage synchronous within `POST /api/complaints`?
**Why it matters.** The API contract says the POST response carries the category, priority and summary, which implies synchronous triage — but a 10-second call inside a request handler has real consequences for worker pool sizing and for the HPA's CPU-based scaling signal.

| Option | Consequence |
|---|---|
| **A. Synchronous.** POST validates, triages inline, persists, returns 201 with the result. | Matches the stated contract (`FR-BE-001`) and the required "honest loading state" in the UI. Requires an async framework or enough workers so that a slow provider does not exhaust the pool. Timeout plus one retry bounds the worst case. |
| **B. Asynchronous with a pending state.** POST returns 202 immediately; a worker triages; the UI polls. | Better under load, but it contradicts the contract, introduces an "untriaged" state that `BR-TRIAGE-001` forbids, and adds a queue and a worker to a one-week build. |

**Blocks:** M2.2, M2.5, M1.1, the entire test design.
**Recommendation: A**, implemented on an async stack so that a blocked outbound call yields rather than occupying a worker. This is effectively mandated by the contract; it is listed here so the consequence is explicit rather than accidental.

---

## AD-005 — Backend framework and concurrency model
**Why it matters.** This becomes `ADR-0001` (provider interface) context and determines how everything else is written. It also determines whether `AD-004`'s synchronous triage is safe.

| Option | Consequence |
|---|---|
| **A. FastAPI + Pydantic v2, fully async** (async routes, `httpx.AsyncClient`, `SQLAlchemy 2.0` async engine with `asyncpg`, `redis.asyncio`). | Recommended by the problem statement. OpenAPI schema for free, which `FR-FE-012` and `FR-BE-010` depend on. Pydantic serves double duty: HTTP validation *and* LLM output validation — one mental model, two uses. A 10-second outbound call costs a task, not a worker. |
| **B. FastAPI, synchronous handlers** with a larger worker count. | Simpler to write and to test. A slow provider occupies a worker for up to 10 seconds; under the HPA's load test this is the first thing to fall over. |
| **C. Flask.** | Permitted, must be declared in the README. Loses the automatic OpenAPI schema that the typed frontend client is checked against, so `FR-FE-012` costs real work. Not recommended. |

**Blocks:** Everything in M2, M3, M5. This is the single highest-fan-out decision on the page.
**Recommendation: A.**

---

## AD-006 — Which hosted model provider is the production path?
**Why it matters.** Determines `triaged_by` values, the SDK, the structured-output mechanism, the rate limits to design against, and the PII position in `AD-003`.

| Option | Consequence |
|---|---|
| **A. Groq**, OpenAI-compatible endpoint, small instruct model. | The official `openai` SDK works by changing `base_url`, so the client code is boring. Very fast inference, which matters while a citizen watches a spinner. Free tier with no credit card; limits are per organisation and per model. `triaged_by = llm:groq`. |
| **B. Google AI Studio (Gemini Flash / Flash-Lite).** | Generous daily allowance, native structured output. Free-tier inputs may be used to improve models — which makes `AD-003` a sharper decision, in a way that is good for the ADR and bad for the data. |
| **C. Ollama only** (a 1B model in the Compose stack). | No key, no network, no rate limit, no PII egress. Slower on CPU and measurably worse at classification — which is itself the buy-versus-host lesson. Explicitly costs no marks. |

**Blocks:** M5.2, M5.3, `BR-VOCAB-004`, ADR-0004, the rate-limit sizing in `AD-024`.
**Recommendation: A as primary, C implemented as a real second provider.** `OllamaTriage` is required anyway (`FR-AI-002`), so building both gives the measured comparison that `docs/TRIAGE.md` needs.
**Action for the team regardless of choice:** check the provider's live limits page and cite the numbers actually seen, with the date, in the notes.

---

## AD-007 — Is a schema-validation failure retried, or does it fall straight through to rules?
**Why it matters.** `BR-TRIAGE-007` currently says validation failure goes straight to fallback. A single re-prompt ("your output did not match the schema, return only JSON matching …") often succeeds and would raise the measured LLM-served rate — at the cost of a second call and more latency.

| Option | Consequence |
|---|---|
| **A. No re-prompt.** Invalid output → `RuleBasedTriage`, `triaged_by = rules:fallback`. | Simplest, fastest worst case, easiest to reason about and to test. The fallback rate becomes an honest quality metric of the prompt. |
| **B. One re-prompt on validation failure**, still bounded by the overall timeout budget, then fallback. | Higher LLM-served rate, a more interesting number to report. Doubles worst-case latency and complicates the retry accounting in tests. |

**Blocks:** M5.6, the retry tests.
**Recommendation: A** for the one-week build. If B is wanted, it must share the same 10-second total budget, not double it.

---

## AD-008 — When Redis is down, does the rate limiter fail open or fail closed?
**Why it matters.** Fail-open means a Redis outage removes the only protection on the expensive LLM path. Fail-closed means a Redis outage stops citizens from filing complaints. It is a genuine security-versus-availability trade-off and must be a stated decision, not an accident of a `try/except`.

| Option | Consequence |
|---|---|
| **A. Fail open, loudly.** Allow the request, emit an ERROR log per occurrence, increment a metric. `/ready` is already 503, so Kubernetes stops sending traffic to the pod anyway — which bounds the exposure. | Citizens can still report a burst main during a cache outage. The LLM quota is exposed for the duration, mitigated by the readiness behaviour. |
| **B. Fail closed.** Return 429 (or 503) while the limiter cannot be consulted. | Quota is protected absolutely. A Redis blip becomes a citizen-visible outage on the primary user journey. |

**Blocks:** M4.2, `BR-CACHE-007`, `FR-CACHE-006`.
**Recommendation: A**, precisely because readiness already removes the pod from service, so the fail-open window is small and observable.

---

## AD-009 — Where does the "last 20 triage outcomes" buffer live?
**Why it matters.** `/api/meta/providers` is the observability surface. With 2–10 backend replicas, an in-process buffer answers "the last 20 outcomes *on whichever pod you happened to hit*", which is a different — and weaker — claim.

| Option | Consequence |
|---|---|
| **A. Redis list, trimmed to 20.** | Genuinely global, survives a pod restart, consistent under the HPA. Three lines using `LPUSH` + `LTRIM`. Adds one more Redis dependency to the endpoint. |
| **B. In-process ring buffer**, with the per-replica caveat documented and visible in the response. | Zero infrastructure. Behaves confusingly in exactly the demo where the HPA has scaled to six pods. |

**Blocks:** M5.8, `FR-AI-012`, `NFR-ARCH-005`.
**Recommendation: A.** Redis is already a hard dependency of readiness; the cost is negligible and it makes the demo honest.

---

## AD-010 — How do integration tests get a real PostgreSQL and Redis?
**Why it matters.** `NFR-TEST-004` forbids SQLite substitution, because database constraints and cache semantics are part of what is under test. The mechanism affects local developer experience and CI runtime.

| Option | Consequence |
|---|---|
| **A. GitHub Actions service containers** for CI, plus `compose.yaml` for local runs, selected by environment variables. | Fastest in CI, no Docker-in-Docker. Two slightly different paths to keep working. |
| **B. `testcontainers-python`** — tests start their own containers in both environments. | One path everywhere, excellent developer experience, genuinely reproducible. Slower startup and requires a working Docker socket in the runner (available on GitHub-hosted runners). |
| **C. Run the tests inside the Compose stack** as a one-shot service. | Closest to the deployed topology; awkward to run a single test while developing. |

**Blocks:** M2.7, M3.1, M4, M8.1.
**Recommendation: A** for speed in a one-week build, with the connection details read from environment variables so switching to B later is a configuration change.

---

## AD-011 — Kustomize or Helm?
**Why it matters.** Both are permitted; the choice needs an ADR if Helm is used.

| Option | Consequence |
|---|---|
| **A. Kustomize** with `base/` and `overlays/{dev,prod}`, exactly as the required layout describes. | Matches the prescribed repository layout, `kubeconform` validation is a one-liner, no templating language to debug. |
| **B. Helm.** | More powerful, more to learn, requires an ADR justifying it, and the prescribed directory layout has to be defended as a deviation. |

**Blocks:** M7.7, M8.1 (`manifests` job), M8.2 (deploy job).
**Recommendation: A.**

---

## AD-012 — How is the one-week timeline scoped against a four-week assignment?
**Why it matters.** §5.1 estimates 35–45 hours per student over four weeks. The plan is one week with two students using AI assistance heavily. That is achievable, but it requires deciding *now* what gets cut if the week runs short, rather than discovering it on the last day.

The problem statement gives the priority order explicitly: **F (AI layer) > C (backend) > I (CI/CD) > H (Kubernetes)**, and says never skip the fallback test.

| Option | Consequence |
|---|---|
| **A. Full scope, bonuses excluded.** All 150 marks targeted; the `+15` bonus items are explicitly out of scope. | Realistic. Zero-downtime rollout (+4) is nearly free once `preStop` and SIGTERM handling exist, so it may be picked up opportunistically. |
| **B. Full scope plus selected bonuses** (zero-downtime rollout, digest deploy). | Adds Cosign and digest plumbing to CI in the same week the core is being built. |
| **C. Depth-first on A–G (110 marks), Kubernetes and CI/CD time-boxed.** | The safest plan, and the one §5.1 itself suggests, if the week goes badly. |

**Blocks:** The entire Round 4 schedule, and the critical path.
**Recommendation: A**, with a declared cut order for the last day: VPA loop → release.yml → bonus items → Ollama provider (keeping three providers, which satisfies the rubric) — in that order, and never touching the AI-layer or backend requirements.

---

## AD-013 — How is work split between the two developers?
**Why it matters.** The viva multiplies the individual mark by how well each partner can explain *the other's* code. A clean vertical split maximises throughput and maximises viva risk simultaneously.

| Option | Consequence |
|---|---|
| **A. Split by layer, with scheduled cross-review.** Developer 1 owns backend + AI + data; Developer 2 owns frontend + Docker + Kubernetes + CI. Every PR is reviewed by the other; two scheduled walkthrough sessions. | Maximum parallelism. Highest viva risk, mitigated by review discipline and the walkthroughs. |
| **B. Split by feature slice.** Both work across the stack; each owns end-to-end vertical slices. | Best viva outcome, lowest throughput, and constant merge friction in a one-week build. |
| **C. Hybrid.** Layer ownership for the first two-thirds of the week, then deliberate swap: each developer implements one task inside the other's area and writes the corresponding engineering note. | Keeps most of A's throughput and buys the cross-knowledge the viva requires. The forced swap also produces the deliberate merge conflict `FR-PROC-004` needs, on real code. |

**Blocks:** The entire Round 4 schedule and the PR/review plan.
**Recommendation: C.**

---

# Tier 2 — Contractual decisions

## AD-014 — What is the tenth endpoint?
The rubric marks "all ten endpoints". The behavioural contract lists nine. The tenth is taken to be the OpenAPI schema endpoint (`/openapi.json`, with `/docs`), which the frontend client is typed against.
**Options:** (A) Treat `/openapi.json` as the tenth and say so in the README API table. (B) Add a root or version endpoint (`GET /api/version` returning the build SHA) as the tenth — which also serves `NFR-OPS-004`.
**Recommendation: both** — document the schema endpoint in the API table *and* add `GET /api/version`. It is four lines and it answers "what is production running?" from inside the running system.

## AD-015 — `page_size` over the cap: clamp or reject?
**Options:** (A) Reject with 400 naming the limit. (B) Clamp silently to 100. (C) Clamp and report the effective page size in the response body.
**Recommendation: A.** Explicit, testable, and consistent with the field-level-error contract (`BR-VAL-004`).

## AD-016 — Does the list endpoint have a defined default order?
An unordered paginated list can return the same row on two pages. A deterministic order is required for pagination to be correct at all.
**Recommendation:** `ORDER BY created_at DESC, id DESC` as the default, with the `created_at` index (`FR-DATA-003`) serving exactly this query — which is the justification the engineering notes need.

## AD-017 — What is the rate limit, numerically?
**Inputs:** the free-tier LLM limit (tens of requests per minute, per organisation), the seed/demo traffic, and the load test which must *not* be blocked by the limiter while driving the HPA.
**Options:** (A) 10 requests/minute per IP, fixed window. (B) 20/minute. (C) Token bucket, burst 5, refill 10/minute.
**Recommendation: A** as the default, configurable by environment variable, with the load test either targeting a read endpoint or running with a raised limit — and that arrangement documented, because "we disabled the limiter for the load test" is a viva answer that needs to be a deliberate one.

## AD-018 — Fixed window or token bucket?
**Recommendation: fixed window** using `INCR` + `EXPIRE` on a per-IP, per-minute key. Two Redis commands, trivially correct, easy to explain. Token bucket is a better limiter and a worse use of the week.

## AD-019 — What exactly is hashed for the triage cache key?
Defines what "duplicate complaint" means (`BR-TRIAGE-011`).
**Options:** (A) SHA-256 of normalised text only. (B) SHA-256 of normalised text + normalised location. (C) (B) plus the provider name and prompt version.
**Recommendation: C.** Including the provider and a prompt version string means a prompt change or a provider switch does not serve stale results from the previous configuration — which is the failure mode that makes content-hash caches embarrassing in a demo. Normalisation: lower-case, collapse whitespace, strip surrounding punctuation.

## AD-020 — Native PostgreSQL enum types or `varchar` + `CHECK`?
**Options:** (A) Native `CREATE TYPE` enums — strongest typing, but adding a value later requires `ALTER TYPE` and Alembic needs explicit handling on downgrade. (B) `varchar` with a `CHECK` constraint — trivially reversible migrations, slightly weaker typing.
**Recommendation: A** for `category`, `priority` and `status` (closed sets that will not change during this project), and **B** for `triaged_by` (which grows whenever a provider is added).

## AD-021 — Who generates the UUID?
**Options:** (A) PostgreSQL `gen_random_uuid()` as a column default — satisfies "server-generated" literally, requires `pgcrypto` or PostgreSQL 13+ built-in. (B) The application generates `uuid4` before insert — the id is known before the round trip, which simplifies logging and the response path.
**Recommendation: A**, with the database default as the guarantee; the row is returned by `RETURNING` so the id is available immediately anyway.

## AD-022 — How is the seed made idempotent?
**Options:** (A) Deterministic UUIDv5 derived from a namespace plus the complaint text, inserted with `ON CONFLICT (id) DO NOTHING`. (B) A natural unique key on `(text, location)`. (C) A `seed_key` column with a unique index.
**Recommendation: A.** It needs no schema change, requires no additional unique constraint on user data, and running it twice provably changes nothing.

## AD-023 — Does the fallback path also populate `ai_summary`?
`ai_summary` is nullable, but a dashboard where half the rows have no summary looks broken.
**Options:** (A) `RuleBasedTriage` produces a deterministic one-line summary (for example, a truncated first clause plus the matched category). (B) Leave it null on the rules path, and render "no summary" in the UI.
**Recommendation: A**, so that `RuleBasedTriage` satisfies the same contract as every other provider — which is the whole point of the interface.

## AD-024 — Does a status change invalidate the stats cache?
`BR-CACHE-003` says yes. Confirm, because it costs one more invalidation call on a hot path.
**Recommendation: yes** — the stats endpoint aggregates by category and priority; if a future stat also groups by status (likely, for an operations dashboard), stale data after a transition is a visible bug.

## AD-025 — What does `GET /api/stats` actually return?
**Recommendation:** counts grouped by category, counts grouped by priority, counts grouped by status, and a total — all as objects keyed by enum value with explicit zeroes for absent values, so the frontend never has to guess which keys exist.

## AD-026 — Is `confidence` persisted?
`TriageResult` carries `confidence`, but the required schema has no column for it.
**Options:** (A) Do not persist it; use it only for logging and for the `/api/meta/providers` buffer. (B) Add a nullable `triage_confidence` column.
**Recommendation: B.** It is one column, it makes "how good is the classifier?" answerable from the data, and the schema is a *minimum*, not a maximum.

## AD-027 — Kubernetes Secret provisioning for real runs
Committed manifests carry placeholders only (`FR-K8S-005`). Something has to supply the real values.
**Options:** (A) `kubectl create secret generic … --from-literal` documented in the runbook and executed in CI from GitHub Secrets. (B) A Kustomize `secretGenerator` reading from a git-ignored `.env` file. (C) Sealed Secrets / SOPS.
**Recommendation: A** for the runbook and CI, with B documented as the local-development convenience. C is a bonus-tier concern.

## AD-028 — Local Kubernetes: k3d or kind?
**Recommendation: k3d.** Traefik ships as the default Ingress controller, which removes an installation step and a class of "why is my Ingress pending" debugging from a one-week build. Choose `kind` only if the team already has it working, in which case an ingress-nginx install step must be added to the deploy job.

## AD-029 — Which Ingress host name is used?
**Recommendation:** a fixed host such as `civic-station.localhost` in the dev overlay, and the same host in CI with the request carrying an explicit `Host` header so the smoke test does not depend on DNS.

---

# Tier 3 — Tooling decisions (accept unless there is a preference)

| ID | Question | Recommendation |
|----|----------|----------------|
| AD-030 | Product name — the problem statement permits renaming | Keep **Civic-Station**; Kubernetes objects use the RFC 1123 form `civic-station` (the namespace in §3.3 is written with a capital, which Kubernetes rejects — this is a deliberate, documented correction) |
| AD-031 | Python dependency management | `pyproject.toml` with `uv` for speed in CI, or plain `pip` + `requirements.txt` + `requirements-dev.txt`. Recommendation: `pyproject.toml` + `uv`, with a lock file committed |
| AD-032 | ORM style | SQLAlchemy 2.0 async, typed `Mapped[...]` models, `select()` constructs in repositories |
| AD-033 | Migration autogeneration | Alembic `--autogenerate` as a starting point, every revision hand-reviewed before commit |
| AD-034 | Deploy-by-reference — SHA tag or digest | **SHA tag** for the required marks; digest is a documented bonus. This becomes `ADR-0003` either way |
| AD-035 | Node package manager | `npm` with a committed `package-lock.json` (fewest moving parts in CI) |
| AD-036 | Frontend data fetching | TanStack Query, or plain `fetch` inside the typed client with local state. Recommendation: **plain typed client + local state** — three views do not justify a data-fetching library, and fewer dependencies means a smaller bundle and fewer Trivy findings |
| AD-037 | Frontend routing | `react-router` with three routes |
| AD-038 | Frontend styling | Plain CSS modules or a single stylesheet. No component library — it inflates the image past the 60 MB budget conversation for no marks |
| AD-039 | Metrics library | `prometheus-client` (Python), exposed through a route, instrumented in middleware |
| AD-040 | Structured logging library | `structlog` with a JSON renderer, or stdlib `logging` with a JSON formatter. Recommendation: **`structlog`** — request-id binding via context variables is the feature being bought |
| AD-041 | Test HTTP client | `httpx.AsyncClient` against the ASGI app, plus the Compose stack for the CI integration job |
| AD-042 | Commit and branch naming | Conventional Commits; branches `feat/<area>-<short-desc>`, `fix/…`, `docs/…` |
| AD-043 | Load tool | **k6** (the repository layout already names `load/k6-script.js`) |
| AD-044 | Where the replicas-vs-load chart is produced | A small committed script that reads the captured `hpa -w` output and k6 summary and emits a PNG into `docs/evidence/` — so the chart is reproducible rather than a screenshot of a spreadsheet |

---

# Round 2 — Resolution log

**All decisions are RESOLVED.** Design documents may cite any row below as settled. A change to a resolved row requires a note of what changed and why, because rules and tests cascade from these.

**Accepted:** Round 2, by both developers jointly. **Revised:** 2026-09-25, by both developers, following the specification audit in `docs/audit/01-specification-audit.md`. Rows revised in that pass are marked **[rev 2026-09-25]** and state what changed. Rows `AD-045`–`AD-056` were added in that pass.

## Tier 1 — Architectural

| ID | Question | Decision | Consequences to honour |
|----|----------|----------|------------------------|
| **AD-001** | Frontend → backend addressing | **nginx reverse-proxies `/api` to the backend.** Frontend uses relative URLs only. | No CORS in the browser's view (same origin). Proxy target templated from an environment variable at container start via `envsubst`. Backend CORS config still exists but is narrow. Ingress routes `/` and `/api` to the same two Services. → **ADR-0002** |
| **AD-002** | Outbound egress under `internal: true` | **Three networks:** `edge` (frontend ↔ backend), `internal` (`internal: true`, backend ↔ postgres ↔ redis ↔ ollama), `egress` (backend → internet). | **[rev 2026-09-25]** Backend joins all three; it is the only service that does. Frontend joins `edge` only. Postgres, Redis and Ollama join `internal` only. **The brief's §3.2 prescribes two networks; this is a deliberate deviation, now recorded in ADR-0005 and reflected in `FR-CTR-005` and `RUB-G-03`** so the marked rubric line and the requirement agree. **Ollama's model pull** is resolved by `AD-046`: a one-time `make pull-models` step on the `egress` network, not a silent assumption. → **Engineering notes Q7** |
| **AD-003** | PII egress | **Send complaint body + location only. Never send `reporter_contact`. Redact detectable phone numbers, email addresses and long digit strings from the text before it leaves the process.** | A `redact()` function in the triage provider layer, applied before prompt construction, with its own unit test and its known limitations written down. Redaction happens before hashing for the triage cache, so the cache key is computed on the redacted text. → **ADR-0004** |
| **AD-004** | Synchronous triage | **Synchronous within `POST /api/complaints`**, on an async stack. | Worst case bounded at 10 s + one jittered retry. A blocked outbound call yields the event loop rather than occupying a worker. No pending/untriaged state exists (`BR-TRIAGE-001` holds). |
| **AD-005** | Backend framework | **FastAPI + Pydantic v2, fully async**: async routes, SQLAlchemy 2.0 async engine + `asyncpg`, `httpx.AsyncClient`, `redis.asyncio`. | OpenAPI schema is generated, and is the contract the frontend client is checked against. Pydantic validates HTTP input *and* LLM output. All repository functions are `async def`. Tests use `pytest-asyncio` + `httpx.ASGITransport`. → **ADR-0001** context |
| **AD-006** | Model provider | **Groq primary**, model **`llama-3.1-8b-instant`** (OpenAI-compatible endpoint via the official `openai` SDK with `base_url` changed). **Ollama as the second real provider**, model **`llama3.2:1b`**. | **[rev 2026-09-25]** Models are now pinned by name rather than described; both are set through `TRIAGE_MODEL` and `OLLAMA_MODEL`, whose defaults are these values (`AD-045`). `triaged_by` values in play: `llm:groq`, `llm:ollama`, `rules`, `rules:fallback`, `simulated` (`AD-020`). Four implementations total with `RuleBasedTriage` and `SimulatedTriage`. `docs/TRIAGE.md` carries the measured buy-vs-host comparison. **Observed Groq free-tier limits, checked 2026-09-25: re-verify before submission and record the date seen in `docs/TRIAGE.md` — this is a required line in that file, not an optional note (`AD-052`).** |
| **AD-007** | Re-prompt on validation failure | **No re-prompt.** Invalid output → `RuleBasedTriage`, `triaged_by = "rules:fallback"`. | The fallback rate is reported as an honest prompt-quality metric in `docs/TRIAGE.md`. Retry accounting stays simple: at most one retry, only for timeout / 429 / 5xx. |
| **AD-008** | Rate limiter when Redis is down | **Fail open, loudly.** Allow the request, emit one ERROR log per occurrence, increment `rate_limiter_unavailable_total`. | **[rev 2026-09-25]** Counter name fixed to `rate_limiter_unavailable_total`, matching `BR-CACHE-007` and the `_total` suffix convention every other counter uses. Justified by `/ready` already returning 503 in this state, so Kubernetes removes the pod from the Service and bounds the exposure window. Recorded in **ADR-0005** because it trades security for availability on the only control guarding the paid path. |
| **AD-009** | Triage outcome buffer location | **Redis list**, `LPUSH` + `LTRIM` to 20. | `/api/meta/providers` answers globally rather than per-pod, which keeps the answer honest once the HPA has scaled to six replicas. Survives pod restarts. |
| **AD-010** | Integration test infrastructure | **GitHub Actions service containers in CI; `compose.yaml` locally.** Connection details from environment variables in both. | Switching to `testcontainers` later is a configuration change, not a rewrite. No SQLite anywhere — DB constraints are part of what is under test. |
| **AD-011** | Manifest tooling | **Kustomize**, `base/` + `overlays/{dev,prod}`. | Matches the prescribed `§5.7` layout. `kustomize build overlays/prod \| kubeconform` is the CI `manifests` job. No ADR needed. |
| **AD-012** | Scope | **Full marked scope targeted; the `+15` bonus items are out of scope except the zero-downtime rollout, which is in scope.** | **[rev 2026-09-25]** Three changes. (a) **The zero-downtime rollout moves into scope**: the brief states it as a §3.3 body requirement at `:293`, not only as a `+4` bonus at `:486`, and `NFR-REL-003` is a `MUST` whose only measure is that demonstration. It is nearly free once `preStop` and SIGTERM handling exist, both of which are required anyway. (b) **`OllamaTriage` is removed from the cut order.** Cutting it would break `FR-AI-002` (`MUST`, four implementations) and `FR-CTR-007` (`MUST`, three named volumes), and would delete the zero-egress mitigation that ADR-0004 relies on. (c) The mark total is stated as "the full marked scope" rather than a number, because the brief's §4 section weights sum to 175, not the 150 it claims — see `AD-047`. **Revised cut order:** (1) VPA loop, (2) `release.yml`, (3) remaining bonuses. **Never cut:** the AI layer, the backend, the fallback test, or `OllamaTriage`. |
| **AD-013** | Developer split | **Dev 1 owns the application: M1 frontend, M2 backend, M3 data, M5 AI. Dev 2 owns the platform: M6 containers, M7 Kubernetes, M8 CI/CD.** M4 cache is implemented by Dev 1 (application-side) and operated by Dev 2 (volumes, manifests). M9–M11 are shared. | **Two consequences the schedule must absorb.** (a) Dev 2 is blocked on day 1 without something to containerise, so Dev 1's first deliverable is a contract-first backend skeleton — all routes present returning stub responses, real `/health` and `/ready` — which becomes the head of the critical path. (b) Viva risk concentrates: Dev 1 must be able to defend the HPA/VPA conflict and the network topology; Dev 2 must be able to defend the triage fallback pipeline. Mitigated by two mandatory cross-walkthrough sessions and by each developer writing one engineering-note answer from the other's area. |

## Tier 2 — Contractual (all accepted as recommended)

| ID | Decision |
|----|----------|
| **AD-014** | **[rev 2026-09-25]** `/openapi.json` is the tenth endpoint and appears in the README API table. **Additionally** `GET /api/version` returns the running commit SHA, serving `NFR-OPS-004`. **The SHA is injected at runtime** through the `APP_VERSION` environment variable, set from the Deployment manifest and from `compose.prod.yaml` — **never as a Docker build argument.** This keeps one image digest valid in every environment, so `FR-FE-014` and the answer to engineering-notes Q3 both hold. The README API table states eleven endpoints and notes that the rubric's "ten" counts the nine behavioural endpoints plus `/openapi.json`; `/api/version` is an eleventh, defined by `FR-BE-029`. |
| **AD-015** | `page_size > 100` is **rejected with 400** naming the limit. Not silently clamped. |
| **AD-016** | Default list order is **`created_at DESC, id DESC`**. This is the named query the `created_at` index serves, and that pairing is what the engineering notes cite. |
| **AD-017** | **[rev 2026-09-25]** Rate limit **10 requests per 60 s per client IP**, fixed window, set by `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS`. **Only `POST /api/complaints` is rate-limited**; the `GET` endpoints are not. **The k6 load test drives `GET /api/complaints` with varied filters and pages** — uncached, so it produces real CPU load — **plus a low-rate `GET /api/stats`** to exercise the cache path. Because `/api/stats` is cached for 30 s it cannot generate sustained CPU on its own, which is why the list endpoint carries the load. The limiter is exercised separately by `FR-CACHE-007`'s multi-replica test (`AD-053`), not by the HPA run. |
| **AD-018** | **Fixed window** via `INCR` + `EXPIRE` on a per-IP, per-minute key. |
| **AD-019** | Triage cache key = **SHA-256 of `normalise(redacted_text)` + `normalise(location)` + provider name + prompt version string**. Normalisation: lower-case, collapse whitespace, strip surrounding punctuation. Including provider and prompt version means a prompt change never serves stale results from the previous configuration. |
| **AD-020** | **[rev 2026-09-25]** **Native PostgreSQL enums** for `category`, `priority`, `status` (closed sets). **`varchar(32)` + `CHECK`** for `triaged_by` (grows when a provider is added). The `CHECK` set is written out in full, not abbreviated: **`'llm:groq'`, `'llm:ollama'`, `'rules'`, `'rules:fallback'`, `'simulated'`.** `'simulated'` is included because CI runs `TRIAGE_PROVIDER=simulated` and a successful simulated triage must persist a legal value; recording it truthfully keeps the fallback-rate metric in `docs/TRIAGE.md` honest, which reporting `'rules'` instead would not. |
| **AD-021** | `id` default is **`gen_random_uuid()`** in the database; the row is returned via `RETURNING`. |
| **AD-022** | **[rev 2026-09-25]** Seed idempotency via **deterministic UUIDv5** with **`ON CONFLICT (id) DO NOTHING`**. The namespace is the fixed literal **`6f2a1c94-3e5b-4d80-9a17-c0b8e4f21d63`**, declared as `SEED_UUID_NAMESPACE` in the seed module, so the ids are reproducible on any machine. No schema change, no unique constraint on user data, provably unchanged on a second run. **The seed is an explicit exemption** from `BR-VAL-006` (server-generated ids), `BR-STATUS-001` (initial status `open`) and `BR-DATA-003` (SQL only in `repositories/`); each of those rules now names the exemption, because a seed is an administrative fixture loader, not a client. `AD-021`'s `gen_random_uuid()` default remains the path for every real insert. |
| **AD-023** | **[rev 2026-09-25]** **`RuleBasedTriage` produces an `ai_summary` too** — a deterministic one-line summary — so it satisfies the same contract as every other provider. Because every path populates it, the column is **`NOT NULL`**, not nullable: a guarantee the contract makes and the database does not enforce is not a guarantee. The algorithm is specified, not exemplified: **take the text up to the first sentence terminator (`.`, `!`, `?`, newline) or the first 120 characters, whichever is shorter; collapse whitespace; prefix `"<category>: "`; truncate the whole result to 140 characters on a word boundary.** |
| **AD-024** | **A status change invalidates the stats cache**, because the stats response includes counts by status. |
| **AD-025** | `GET /api/stats` returns counts **by category, by priority, by status, plus a total**, each as an object keyed by every enum value with **explicit zeroes**, so the frontend never guesses which keys exist. |
| **AD-026** | **[rev 2026-09-25]** **Add a `NOT NULL` `triage_confidence` column** with `CHECK (triage_confidence BETWEEN 0 AND 1)`. Every provider sets it, including the rules path, which uses a **fixed `0.35`** — deliberately low, because a keyword match is weak evidence and an honest low number is more useful than a flattering one. Not nullable, for the same reason as `ai_summary`. The required schema is a minimum, not a maximum, and this column makes classifier quality answerable from the data. Defined by `FR-DATA-002`. |
| **AD-027** | Kubernetes Secrets provisioned by **`kubectl create secret generic --from-literal`**, documented in the runbook and executed in CI from GitHub Secrets. A Kustomize `secretGenerator` over a git-ignored `.env` is the documented local-development convenience. Committed manifests carry placeholders only. |
| **AD-028** | **k3d**, using its bundled Traefik as the Ingress controller. Used locally and in the `cd.yml` ephemeral cluster. |
| **AD-029** | Ingress host **`civic-station.localhost`** in dev and in CI, with the CI smoke test sending an explicit `Host` header so it does not depend on DNS. |

## Tier 3 — Tooling (accepted at the recommended defaults)

| ID | Decision |
|----|----------|
| **AD-030** | Product name **Civic-Station**; all Kubernetes object names use the RFC 1123 form **`civic-station`**. The capitalised namespace in the brief's §3.3 is invalid for Kubernetes and this correction is documented in the engineering notes. |
| **AD-031** | `pyproject.toml` + **`uv`**, lock file committed. |
| **AD-032** | **SQLAlchemy 2.0 async**, typed `Mapped[...]` models, `select()` constructs, all inside `repositories/`. |
| **AD-033** | Alembic `--autogenerate` as a starting point; every revision hand-reviewed before commit; every revision has a working `downgrade`. |
| **AD-034** | **[rev 2026-09-25]** Deploy by **commit SHA tag**. Digest deployment and Cosign remain an out-of-scope bonus. The running SHA reaches `GET /api/version` through the **`APP_VERSION` environment variable at runtime**, not through a build argument (`AD-014`), so the image stays environment-independent. → **ADR-0003** |
| **AD-035** | **npm** with a committed `package-lock.json`. |
| **AD-036** | **Plain typed client + local React state.** No data-fetching library — three views do not justify one, and fewer dependencies means a smaller bundle and fewer Trivy findings. |
| **AD-037** | **`react-router`**, three routes. |
| **AD-038** | Plain CSS (modules or a single stylesheet). **No component library** — it inflates the image against the ~60 MB budget for zero marks. |
| **AD-039** | **`prometheus-client`**, exposed through a route, instrumented in middleware. |
| **AD-040** | **`structlog`** with a JSON renderer; `request_id` bound via context variables. |
| **AD-041** | **`httpx.AsyncClient`** against the ASGI app for API tests; the Compose stack for the CI integration job. |
| **AD-042** | Conventional Commits. Branches `feat/<area>-<desc>`, `fix/…`, `docs/…`, `ci/…`. |
| **AD-043** | **k6**, script at `load/k6-script.js`. |
| **AD-044** | The replicas-vs-load chart is produced by a **committed script** that reads the captured `hpa -w` output and the k6 summary and writes a PNG into `docs/evidence/` — reproducible, not a screenshot of a spreadsheet. |

## Derived constraints the design documents must carry

These fall out of the decisions above and are easy to lose:

1. **Redaction happens before hashing.** `AD-003` + `AD-019`: the triage cache key is computed on redacted text, so redaction is deterministic or the cache silently stops working.
2. **The load test targets read endpoints.** `AD-017`: the k6 script generates CPU load through `GET /api/complaints` with varied filters and pages, which is uncached. `GET /api/stats` is cached for 30 s and therefore cannot sustain load on its own, so it appears in the script only at a low rate to exercise the cache path. The limiter is verified separately (`AD-053`), not by this run.
3. **Ollama has no internet at runtime.** `AD-002` + `AD-046`: `OllamaTriage` works because the weights are already in the `ollama_models` volume. Getting them there is `make pull-models`, a one-time step that runs a throwaway container on the `egress` network. It is a documented prerequisite in the README quickstart, and the Compose stack fails loudly with a named error if the volume is empty rather than hanging on a pull it cannot perform.
4. **The frontend never sees a backend URL.** `AD-001`: this removes CORS from the browser's view, but the backend still needs a CORS configuration for the direct-access case used in development and by the integration tests. The allowed origins are `http://localhost:5173` (Vite dev server) and `http://localhost:8080` (the Compose frontend), set through `CORS_ALLOW_ORIGINS`; the production default is the empty list.
5. **`GET /api/version` reads the SHA at runtime.** `AD-014` + `AD-034`: `APP_VERSION` is an environment variable set by the Deployment manifest and by `compose.prod.yaml`, never a Docker build argument. The image therefore stays identical across environments, which is what makes the answer to engineering-notes Q3 true rather than aspirational.
6. **Every marked deliverable has an owning requirement.** The audit found two prerequisites with no requirement at all: credential rotation after a leak, and obtaining the provider key. These are now `FR-PROC-006` and `FR-PROC-007`.

---

# Round 5 — audit remediation, 2026-09-25

Added by the specification audit in `docs/audit/01-specification-audit.md`. These close defects that were open questions dressed as settled design: a placeholder where a value belonged, or a `MUST` with nothing to measure it against.

| ID | Question | Decision |
|----|----------|----------|
| **AD-045** | Model names and request parameters | **Groq `llama-3.1-8b-instant`, Ollama `llama3.2:1b`**, both as the defaults of `TRIAGE_MODEL` and `OLLAMA_MODEL`. Request parameters, identical on both: **`temperature=0`** (classification, not composition — and it makes the production path close to repeatable), **`max_tokens=200`** (a category, a priority, a ≤140-character summary and a float do not need more, and it bounds the cost of a model that starts rambling), **`response_format={"type": "json_object"}`** on Groq, **`format="json"`** on Ollama. JSON mode is chosen over a tool-call schema because both providers support it identically, which keeps one code path. |
| **AD-046** | How Ollama's weights reach the volume | **`make pull-models`**, a documented one-time step that runs `ollama pull` in a throwaway container attached to `egress`, writing into the `ollama_models` volume. Not part of `docker compose up`. The Ollama service's healthcheck fails with a named message if the volume holds no model, so the failure is legible instead of a hang. |
| **AD-047** | The brief's mark total does not add up | **Target every rubric line; do not reconcile the total.** The brief's §4 section weights sum to **175** (plus 15 bonus), not the 150 stated at `:389`, and §5.1's "A–G = 110" sums to 120. Both are arithmetic errors in the brief. **Action: raise it with the instructor before submission.** Until answered, `RUBRIC-TRACEABILITY.md` records each line's stated weight and shows the true sum, because silently picking a denominator would misreport what each line is worth. No design document states a mark total any more; each cites the rubric rows it delivers. |
| **AD-048** | Resource requests and limits | Per container, as the starting guess that `FR-LOAD-003`'s VPA loop then corrects: **backend** `requests 100m / 256Mi`, `limits 500m / 512Mi`; **frontend** `requests 20m / 32Mi`, `limits 100m / 128Mi`; **postgres** `requests 200m / 512Mi`, `limits 1000m / 1Gi`; **redis** `requests 50m / 64Mi`, `limits 200m / 256Mi`. The backend request is deliberately small so that a plateau above 60 % utilisation is reachable with a load a laptop can generate. **These are a calibration starting point, not a measurement** — recording them is what makes step 1 of the VPA loop possible. |
| **AD-049** | Indexes | **Three, not two.** `ix_complaints_created_at_id` on `(created_at DESC, id DESC)` — serves the default listing *and* the `id` tie-break that `AD-016`'s stable pagination depends on. `ix_complaints_status_priority_created` on `(status, priority, created_at DESC)` — serves the filtered operations view, including the sort, so a filtered page is not a scan plus a sort. `ix_complaints_category_created` on `(category, created_at DESC)` — `category` is a first-class filter and was previously unindexed. The audit found that no index served the query the API actually issues; `RUB-D-03` marks two indexes each justified by a named query, and three justified indexes satisfy that line. |
| **AD-050** | Load profile | k6, four stages: **ramp 0→40 VUs over 60 s, plateau 40 VUs for 180 s, ramp 40→0 over 30 s, idle 0 VUs for 330 s** (longer than the HPA's 300 s scale-down stabilisation window, so scale-in is observable). Request mix per iteration: **8 × `GET /api/complaints`** with randomised `page`, `page_size` and filter combinations, **1 × `GET /api/stats`**. Thresholds, which fail the run: **`http_req_failed: rate<0.01`**, **`http_req_duration: p(95)<2000`**. Acceptance: backend CPU utilisation exceeds 60 % during the plateau, replicas rise above `minReplicas`, and replicas return to 2 within 600 s of the idle stage starting. |
| **AD-051** | HPA lag measurement | The `hpa -w` capture alone has no timestamps, so **the capture is piped through a timestamping wrapper** (`kubectl get hpa -w \| ts '%Y-%m-%dT%H:%M:%S'`, or `awk` prefixing `strftime`) into `docs/evidence/hpa-watch.txt`, and **k6 writes `--out json=docs/evidence/k6-timeseries.json`** rather than only a summary. Lag is then the difference between the first sample where offered load rises and the first where `replicas` rises, both readable from the two files. Without this the chart required at `Problem_Statement.md:320` and the Q5 answer have no data source. |
| **AD-052** | `docs/TRIAGE.md` required contents | Seven sections, each of which something else depends on: the **pinned model names**; the **prompt, verbatim**; the **output JSON schema**; the **observed provider rate limits with the date seen** (`AD-006`); the **measured triage cache hit rate** with the counter it came from; the **measured fallback rate**; and the **Groq-versus-Ollama comparison** over the same seeded inputs, latency and agreement rate. |
| **AD-053** | Verifying the distributed limiter | A dedicated test, not the HPA run: **4 backend replicas, 30 requests to `POST /api/complaints` from one source within 60 s, expect exactly 10 × 201 and 20 × 429**, each 429 carrying `Retry-After`. This is what proves the limiter is in Redis rather than in process — an in-process limiter would allow 40. Owned by `FR-CACHE-007`. |
| **AD-054** | Client IP resolution behind proxies | The backend reads **the last entry of `X-Forwarded-For`**, and only when the immediate peer is in `TRUSTED_PROXY_CIDRS` (default `10.0.0.0/8,172.16.0.0/12,192.168.0.0/16`); otherwise it uses the socket peer address. Taking the last entry rather than the first is deliberate: the first is client-supplied and therefore forgeable, which would let anyone bypass the limiter by setting one header. |
| **AD-055** | Cache stampede on `/api/stats` | **Single-flight via a short Redis lock.** On a miss, `SET cs:stats:lock <token> NX EX 5`: the winner computes and caches, the losers wait up to 250 ms for the key to appear and then serve a direct query. Bounded, simple, and it keeps a burst after an invalidating write from becoming N identical aggregations. |
| **AD-056** | Authentication on operator actions | **Explicitly out of scope, and documented as a non-goal** rather than left unstated. `PATCH /api/complaints/{id}/status` is unauthenticated: any caller can advance any complaint. The brief does not ask for authentication and the rubric does not mark it, so building it would be unmarked scope. `docs/NON-GOALS.md` records the gap, the exposure it leaves, and the exact place a `Depends(require_operator)` would attach. A known, documented limitation is defensible at viva; an unnoticed one is not. |

---

# Round 6 — implementation decisions

Recorded during implementation, before the code that depends on them (`CLAUDE.md` §5).

| ID | Question | Decision |
|----|----------|----------|
| **AD-057** | Which log field names are fixed? `00-conventions.md` §5 lists `timestamp`, `level`, `event`, `request_id` as required and then, two paragraphs later, fixes `ts`, `level`, `msg`, `request_id`, `logger` citing `FR-BE-023`. | **The `FR-BE-023` five: `ts`, `level`, `msg`, `request_id`, `logger`.** The stable event names in §5's table (`request.completed`, `triage.fallback`, …) are the value of `msg`. `request_id` is the validated inbound `X-Request-ID` or a generated UUIDv4 inside a request, and JSON `null` on lines emitted outside any request (startup, shutdown), so the key is never omitted. **Rejected:** (a) `timestamp`/`event` — only the first paragraph uses it, while `FR-BE-023`, `NFR-OBS-001` and the second paragraph of §5 all fix `ts`/`msg`/`logger` and say tests parse them; (b) emitting both spellings — doubles every line to paper over a documentation defect, and a parser written against either set still has to pick one. `00-conventions.md` §5's first paragraph is the bug. |
| **AD-058** | What does an unhandled exception return? `00-conventions.md` §4 lists no 500 code. | **500 with the standard envelope, `code: internal_error`, message `Internal server error.`**, produced by the request middleware so the response still carries `X-Request-ID`; the traceback goes to the log at `ERROR`, never to the body. Likewise an unknown route is `404 not_found`, an undefined method `405 method_not_allowed`, a non-JSON write `415 unsupported_media_type`, and a body over 64 KiB `413 payload_too_large`. **Rejected:** (a) Starlette's default plain-text `Internal Server Error` — violates "one error body shape for the whole API" and carries no `request_id`; (b) a handler registered for `Exception` — Starlette runs it in `ServerErrorMiddleware`, outside the request-id middleware, so the response loses its `X-Request-ID` header and the request is never logged as completed. |
| **AD-059** | Who owns the database transaction? `CLAUDE.md` rule 3 forbids `session` under `services/`, yet `03-M2-backend.md` §2.4 has the service load, check the transition table and update "in the same transaction". | **The repository owns it.** `ComplaintRepository` is constructed with the session factory, and each public method is one transaction. `change_status(id, target, ensure_allowed)` loads the row `FOR UPDATE`, calls the domain's `ensure_transition_allowed` passed in by the service, and updates with `updated_at = now()` only if that returns — so a rejected transition writes nothing (`BR-STATUS-006`), a missing row raises `ComplaintNotFoundError` before the table is consulted (`BR-STATUS-007`), and two concurrent operators serialise on the row lock. **Rejected:** (a) a unit-of-work object the service opens and passes down — a second abstraction with one user, and the service would still hold a session-shaped handle the layer check exists to forbid; (b) optimistic `UPDATE … WHERE status = :expected` with a retry — correct, but needs a second read to tell 404 from 409 and puts a retry loop in the service for a race the brief never demonstrates. |
| **AD-060** | Where is model output validated? `ADR-0001` fixes `triage() -> TriageResult`, while `06-M5-ai-triage.md` §2.2 step 6 has the pipeline validate "the response" and `SimulatedTriage`'s `malformed` mode "returns output that fails validation". | **Each provider parses its raw output with `TriageResult.model_validate(...)` at its own boundary, so a bad response surfaces as Pydantic's `ValidationError`; the pipeline treats that exception as `error_class = ValidationFailed` (no retry, `AD-007`) and additionally re-validates whatever a provider returns, so an instance built with `model_construct` cannot slip through.** The protocol signature stays exactly as `ADR-0001` states. **Rejected:** (a) providers return a raw `dict`/`str` and only the pipeline validates — changes the frozen `FR-AI-001` signature and makes every test double speak a wire format; (b) validate only inside providers — trusts four implementations to remember, which is the drift `ADR-0001` puts retry and fallback in one place to avoid. |
| **AD-061** | How can the fallback WARNING carry `complaint_id`, and how can there be exactly one? `FR-BE-025` requires `complaint_id` on the `triage.fallback` line, but triage runs before persistence and the id is generated by the database (`AD-021`). `00-conventions.md` §5 lists `triage.retry` and `triage.validation_failed` as WARNING, while `FR-BE-025`/`NFR-OBS-004` require exactly one WARNING per fallback, "not one per retry". | **The pipeline has two entry points, both in `pipeline.py`:** `run(text, location)` does redact, cache, timeout, retry, validation and fallback and returns a `TriageOutcome`; `report(outcome, complaint_id)` is called by the service after the row is persisted and emits the single `triage.fallback` WARNING (carrying `complaint_id`, `from_provider`, `provider`, `error_class`) and pushes the entry to `cs:outcomes`. **`triage.retry` and `triage.validation_failed` are logged at INFO**, so a fallback produces exactly one WARNING whatever path led to it. Metrics are observed in `run()`. **Rejected:** (a) generate the id in the application before triage — contradicts `AD-021`/`BR-VAL-006` (the database is the only id source); (b) log the WARNING in `run()` without `complaint_id` — fails `FR-BE-025`'s field list; (c) keep `triage.retry` at WARNING — two WARNINGs for a timeout-then-fallback, which is exactly the bug `NFR-OBS-004`'s test exists to catch. `00-conventions.md` §5's two WARNING rows are the documentation bug. |
