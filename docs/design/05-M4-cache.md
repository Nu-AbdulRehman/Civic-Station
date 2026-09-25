# 05 — M4 Cache layer: design and implementation guide

**Owner:** Dev 1 (application side), Dev 2 (volumes, manifests, operations)
**Depends on:** `00-conventions.md`, M2 services
**Delivers:** `RUB-E-01`…`RUB-E-04`, and the correctness half of `RUB-H-05` — a limiter that is not distributed makes the scaling demonstration meaningless. Mark totals are not quoted in design documents (`AD-047`).
**Stack:** Redis 7, `redis.asyncio`, AOF persistence on a named volume

---

## 1. What this module is for

Redis does **four jobs** here across **five keys**, deliberately, so that infrastructure is understood as a capability rather than a single-purpose box. The brief names two jobs; the design adds two more that fall out of the other requirements. The fifth key is the single-flight lock, which is a mechanism belonging to job 1 rather than a job of its own.

| Job | Key shape | TTL | Requirement |
|---|---|---|---|
| Stats read-through cache | `cs:stats:v1` | 30 s + explicit invalidation | `FR-CACHE-001/002` |
| Distributed rate limiter | `cs:ratelimit:<ip>:<window>` | window length | `FR-CACHE-003` |
| Triage content-hash cache | `cs:triage:<sha256>` | 24 h | `FR-CACHE-004` |
| Triage outcomes ring buffer | `cs:outcomes:<PROMPT_VERSION>` (list, trimmed to 20) | none, by design | `AD-009`, `FR-AI-012` |
| Stats single-flight lock | `cs:stats:lock` | 5 s | `AD-055` |

All five go through one **cache port** module (`FR-BE-019`). Services depend on the port; nothing outside `providers/cache/` imports the Redis client.

**The outcomes key carries `PROMPT_VERSION`.** It has no TTL — 20 entries is a bounded size, so expiry would buy nothing — but without the version in the key, entries produced under a previous prompt or provider would be served as current by `/api/meta/providers`. The key changes when the meaning changes, which is the same reasoning as the triage cache key.

**All five keys share Redis database 0** (`REDIS_URL` ends `/0`), so they compete for one memory budget. `maxmemory 256mb` with `maxmemory-policy allkeys-lru` (§2.6) — the consequence is stated there rather than discovered in production.

The single most important sentence in this module: **the rate limiter must be in Redis, not in process.** The moment the HPA scales the backend to four pods, an in-process limiter permits four times the configured traffic. Understanding that is worth more than the marks attached to it.

---

## 2. Design

### 2.1 Stats read-through cache

Read: `GET cs:stats:v1`. Hit → deserialise, respond with `X-Cache: HIT`. Miss → aggregate in SQL, zero-fill every enum key (`AD-025`), `SET` with a 30-second TTL, respond `MISS`.

**Single-flight on a miss** (`AD-055`), because a miss is not a rare event here — every write invalidates the key, so a busy period produces a miss per write. Without this, N concurrent requests after one invalidation run N identical `GROUP BY` queries, which is the load the cache exists to prevent.

- The first caller takes `SET cs:stats:lock <token> NX EX 5`. It aggregates, caches, releases.
- Callers that do not get the lock poll for the cached key for up to **250 ms**, then fall through to a direct query rather than waiting longer. A bounded wait, so a stuck lock-holder degrades latency instead of stalling the endpoint.
- The 5-second lock TTL is the backstop for a holder that dies mid-aggregation.

**Two invalidation mechanisms, deliberately** (`BR-CACHE-001`):

- The **TTL** bounds staleness from causes the application cannot see — a direct database edit, a seed run, a second writer.
- **Explicit invalidation on write** removes staleness the application caused itself, so a citizen who submits a complaint and then opens the Stats view sees their own complaint counted, rather than waiting up to 30 seconds.

Be ready to defend at viva why both exist when either looks sufficient. The short answer: the TTL is a bound on *unknown* writes, the invalidation is a guarantee about *known* writes. Removing the TTL means an unobserved write is stale forever; removing the invalidation means the system lies about its own action.

Invalidation is a `DEL`, triggered by complaint creation **and** by a successful status change (`AD-024`, because the payload includes counts by status).

### 2.2 Distributed rate limiter

**Fixed window** (`AD-018`), because two Redis commands is the right amount of cleverness for this problem.

- Key: `cs:ratelimit:<client_ip>:<epoch_minute>`.
- Operation: `INCR`; if the returned value is 1, `EXPIRE` the key to the window length. Pipeline both so it is one round trip.
- Over the limit → `RateLimitExceededError`, mapped to 429 with `Retry-After` set to the seconds remaining in the current window.

**Limit: 10 requests per 60 seconds per IP**, configurable (`AD-017`).

**Client IP resolution** is the part that quietly breaks, and it is now specified rather than described (`AD-054`). Behind nginx and behind an Ingress the socket peer is a proxy, so every request appears to come from one address and the limiter becomes global.

- nginx and the Ingress set `X-Forwarded-For`, appending the peer they saw.
- The backend takes **the last entry** of that header, and only when the immediate peer's address falls inside `TRUSTED_PROXY_CIDRS` (default `10.0.0.0/8,172.16.0.0/12,192.168.0.0/16`). Otherwise it uses the socket address and ignores the header entirely.
- **The last entry, not the first.** The first entry is whatever the client sent, so trusting it lets any caller bypass the limiter with a single forged header — a limiter keyed on attacker-controlled input is not a limiter. The last entry is the one the nearest trusted proxy appended.
- The resolution lives in **one function** that both the limiter and the logger call, so there is one answer to "who is this" (`BR-CACHE-004`).

Getting this wrong is invisible with a single local client and obvious with two. Test it three ways: two distinct forwarded addresses are limited independently; a forged `X-Forwarded-For` from an untrusted peer is ignored; and a request with no header at all still gets limited by socket address.

**When Redis is unavailable: fail open, loudly** (`AD-008`). Allow the request, log `ratelimit.unavailable` at ERROR, increment `rate_limiter_unavailable_total`. The justification — which belongs in the engineering notes, not only in a comment — is that `/ready` is already returning 503 in this state, so Kubernetes removes the pod from the Service and the fail-open window is small and observable. That reasoning is what makes it a decision rather than a shrug.

**The load test does not touch this path**, and that means the limiter needs its own proof. `AD-017` sends k6 at the `GET` endpoints, so the limiter stays armed during the HPA demonstration and nothing has to be explained away — but it also means the HPA run proves nothing about the limiter.

**`FR-CACHE-007` is that proof:** 4 backend replicas, 30 `POST`s from one IP inside one window, **exactly 10 × 201 and 20 × 429**. Exact counts, because an in-process limiter would allow 40 and would pass any approximate assertion. This is the single test that distinguishes a correct implementation from the common wrong one, and `NFR-SCALE-001` names it as its measure.

### 2.3 Triage content-hash cache

Key: `cs:triage:<sha256>` where the hash covers `normalise(redacted_text)` + `normalise(location)` + provider name + `PROMPT_VERSION` (`AD-019`).

Normalisation: lower-case, collapse internal whitespace, strip leading and trailing punctuation.

**Two properties that are easy to lose:**

1. **Hashing happens on the redacted text** (`ADR-0004` + `AD-019`), so the cache and the prompt see the same content. If redaction is non-deterministic, the cache silently stops working — which is why `redact()` has its own deterministic-output test.
2. **Provider and prompt version are in the key**, so switching providers or editing the prompt cannot serve results produced by the previous configuration. This is the failure mode that makes content-hash caches embarrassing during a demo.

Value: the serialised `TriageResult` plus the provider name that produced it.

A hit therefore yields `triaged_by` of the provider that did the classification, and **`triage_latency_ms` of the cache hit** — a few milliseconds, not the original call's. That is the honest pairing: the classification is the model's, the wait was the cache's, and recording the original latency would overstate what the citizen experienced while hiding the cache's value from the metrics.

Note that the provider name is **already in the key** (`AD-019`), so a hit can only ever come from the currently configured provider. Earlier drafts described this as a nuance — "a hit yields the original provider, not `rules`" — which reads as though a cross-provider hit were possible. It is not: switching `TRIAGE_PROVIDER` changes the key and misses. What the stored provider name buys is a correct `triaged_by` on the hit path without re-deriving it, not cross-provider reuse.

TTL 24 hours. Hit rate is `triage_cache_hits_total / (triage_cache_hits_total + triage_cache_misses_total)`, both read from `/metrics`, and reported as a number in `docs/TRIAGE.md` over the population named in `NFR-PERF-004`. Two counters rather than one with a `result` label: a query that forgets the label selector silently returns the total instead of the hits, which produces a plausible wrong number rather than an error (`FR-BE-009`).

### 2.4 Outcomes ring buffer

`LPUSH cs:outcomes <json>` then `LTRIM cs:outcomes 0 19`, on every triage. `LRANGE 0 19` serves `/api/meta/providers`.

In Redis rather than in process (`AD-009`) so the answer is global once the HPA has scaled out, and so it survives a pod restart. Entries carry no complaint text and no contact data, because the endpoint is not access-controlled.

### 2.5 Degradation, summarised

| Redis state | Stats | Rate limiter | Triage cache | Outcomes | `/ready` |
|---|---|---|---|---|---|
| Up | Cached | Enforced | Active | Recorded | 200 |
| Down | Computed, `X-Cache: MISS` | **Fail open**, ERROR log, counter | Skipped, every call goes to the provider | Skipped | **503** naming `cache` |

Nothing in this table is a crash (`BR-CACHE-007`). The full per-feature table is in `FR-CACHE-006`, and the reasoning behind failing open rather than closed is in **`ADR-0005`** — a security-versus-availability trade on the only control guarding a paid resource earns a page, not a line.

### 2.6 Persistence — and the question to answer

AOF enabled (`appendonly yes`) on the named volume `redisdata` (`FR-CACHE-005`).

**Memory policy, because one Redis serves five keyspaces:** `maxmemory 256mb`, `maxmemory-policy allkeys-lru`. The consequence, stated rather than left to be discovered: under memory pressure LRU can evict **a live rate-limiter counter**, which silently resets that client's window. That path is *not* covered by the fail-open `ERROR` log, because Redis is up and answering — it is the one way this module's instrumentation can be bypassed. It is bounded by 256 MB being generous against five small keyspaces, and it is named in `ADR-0005`.

The brief asks: *why does the cache need a volume when the whole point of a cache is that it can be rebuilt?* A defensible answer for this system: **three of Redis's four jobs here are not caches.** The rate limiter is enforcement state — losing it on restart hands every client a fresh quota, which is precisely what an attacker restarting your pod would want. The outcomes buffer is observability history. The triage cache is real money, because each lost entry is a re-billed inference against a free-tier quota. Only the stats cache is a true cache, and it is the cheapest of the four to rebuild.

**This is the answer to write in the notes**, not a prompt to invent one. It was previously phrased as "write your own version — a different answer is fine if it is argued", which deferred the module's own justification to whoever implemented it. A different answer *is* defensible; this one is the design's, and `FR-CACHE-005` requires the notes to name which of the keyspaces would actually be missed after a restart.

---

## 3. Invariants this module must not violate

| Rule | Where it bites |
|---|---|
| `BR-CACHE-002` | `X-Cache` is set from where the data actually came, never optimistically |
| `BR-CACHE-004` | No in-process counters anywhere |
| `BR-CACHE-006` | The limiter runs before validation and before triage |
| `BR-CACHE-007` | Every degradation path is defined and tested |
| `BR-TRIAGE-011` | Identical content costs one inference |

---

## 4. Tasks

| ID | Task | Size | Owner | Depends on | Delivers | Done when |
|---|---|---|---|---|---|---|
| **T-M4-001** | Cache port module: connection handling, key builders, a uniform "Redis unavailable" path | S | Dev 1 | T-M2-003 | FR-BE-019 | No Redis import outside `providers/cache/` |
| T-M4-002 | Stats cache: read-through, 30 s TTL, `X-Cache` header wiring | S | Dev 1 | T-M4-001 | FR-CACHE-001 | Contract test 11 passes |
| T-M4-003 | Stats invalidation on create and on status change | S | Dev 1 | T-M4-002, T-M2-008 | FR-CACHE-002, AD-024 | Contract test 12 passes |
| **T-M4-004** | Rate limiter: fixed window `INCR`+`EXPIRE`, 429 + `Retry-After`, client-IP resolution via `X-Forwarded-For` | M | Dev 1 | T-M4-001 | FR-CACHE-003, BR-CACHE-004/005/006 | Contract test 5 passes; two distinct forwarded IPs are limited independently |
| T-M4-005 | Rate limiter fail-open path with ERROR log and counter | S | Dev 1 | T-M4-004 | AD-008, BR-CACHE-007 | Test with the port raising: request succeeds, `ratelimit.unavailable` logged once, counter increments |
| T-M4-006 | Triage cache: key derivation, get/set, 24 h TTL, hit/miss counters | M | Dev 1 | T-M4-001, M5 T-M5-007 | FR-CACHE-004, AD-019 | Contract test 18 passes: two identical submissions, one provider call |
| T-M4-007 | Outcomes list: `LPUSH`+`LTRIM`, `LRANGE` reader | S | Dev 1 | T-M4-001 | FR-AI-012, AD-009 | Contract test 19 passes; list never exceeds 20 entries |
| T-M4-008 | Redis AOF + `redisdata` named volume in both Compose files and in the Kubernetes manifests | S | Dev 2 | M6, M7 | FR-CACHE-005 | `appendonly yes` in effect; volume declared in all three places |
| T-M4-009 | Redis-volume justification written into `ENGINEERING-NOTES.md` | S | Dev 2 | T-M4-008 | RUB-E-04 | A written argument, not a restatement of the question |
| T-M4-010 | Multi-replica limiter check: 4 backend replicas, limit still binds in aggregate | S | Dev 2 | M7 T-M7-004 | NFR-SCALE-001, BR-CACHE-004 | Captured output showing 429 at the configured rate with 4 pods running |

---

## 5. Test plan

- **Stats:** miss → hit within TTL; invalidation on create; invalidation on status change; Redis-down path returns computed stats with `MISS`.
- **Rate limiter:** at the limit → 200; one over → 429 with `Retry-After`; two distinct client IPs counted separately; window expiry restores capacity; Redis-down → fail open with exactly one ERROR log.
- **Triage cache:** identical text submitted twice invokes the provider once; a `PROMPT_VERSION` change forces a miss; a provider change forces a miss; redaction is deterministic so the key is stable across calls.
- **Outcomes:** 25 triages leave exactly 20 entries, newest first.
- **Multi-replica (manual, on the cluster):** `T-M4-010`. This is the test that proves the limiter is genuinely distributed, and it cannot be done on one process.
