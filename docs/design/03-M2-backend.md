# 03 — M2 Backend: design and implementation guide

**Owner:** Dev 1 (`AD-013`)
**Depends on:** `00-conventions.md`, `01-api-contract.md`, M3 (data), M4 (cache), M5 (AI)
**Delivers:** `RUB-C-01`…`RUB-C-07`, plus the surface every other module is verified through. Mark totals are not quoted in design documents (`AD-047`).
**Stack:** FastAPI + Pydantic v2, fully async; SQLAlchemy 2.0 async + asyncpg; `redis.asyncio`; `httpx.AsyncClient` (`AD-005`)

---

## 1. What this module is for

The backend owns every business rule in the system. The frontend renders what it is told; the database stores what it is given; the providers do one narrow job each. Everything that decides anything lives here.

The design pressure is a single rule from the brief: *a route that opens a database session is a design failure worth marks*. Four layers, arrows pointing one way. This is not decoration — it is the thing that makes the classifier replaceable, the tests deterministic, and the SQL auditable.

---

## 2. Architecture

### 2.1 The four layers, and what each may not do

```
routes/        HTTP. Parse, call ONE service operation, serialise, set status code.
   │           May not: open a session, issue SQL, call a provider, decide a transition.
   ▼
services/      Business rules. Triage orchestration, state machine, statistics.
   │           May not: know about HTTP, raise HTTPException, import a concrete provider.
   ▼
repositories/  ALL SQL. Nothing else in the system issues a query.
               May not: know about HTTP, know about providers, contain a business rule.

providers/     Outbound integrations behind ports. Triage and cache.
               May not: import services or repositories.

domain/        Enums, TriageResult, the transition table, domain error types.
               Imports nothing from the application. Everything may import it.
```

**Error translation happens at exactly one seam.** Services raise domain errors (`ComplaintNotFoundError`, `InvalidTransitionError`, `RateLimitExceededError`). A single set of FastAPI exception handlers maps each domain error to its HTTP status and to the error body from `00-conventions.md` §4. No service imports `HTTPException`; no route catches a domain error individually.

### 2.2 Dependency wiring

The application is built by a factory function so that tests can construct an app with different dependencies without touching module-level state.

- **Settings** are constructed once and stored on application state.
- **Engine, session factory and Redis client** are created during lifespan startup and closed during shutdown.
- **The triage provider** is resolved once at startup by the factory (`M5.1`) and stored on application state. Resolution failure is a startup failure.
- **Routes obtain their dependencies through FastAPI's dependency injection**, never by importing a module-level singleton. This is what lets a test inject a raising provider or a raising session factory without monkeypatching internals — which is what `NFR-TEST-002` requires.

### 2.3 Request pipeline

Middleware order matters and is fixed:

```
1. CORS              — configured from CORS_ALLOW_ORIGINS; OUTERMOST
2. Request ID        — read X-Request-ID (validated) or generate; bind into log context; echo on response
3. Logging           — request.started / request.completed with duration
4. Metrics           — http_requests_total, http_request_duration_seconds (path_template labels)
5. Route handler
```

**CORS is outermost, and the order matters.** It was previously innermost, immediately before the route handler — which means a 4xx produced by any outer middleware carries **no CORS headers**, and the browser then reports an opaque CORS failure instead of the 429 or 400 the server actually sent. A rate-limited user would see "blocked by CORS policy" and a developer would debug the wrong layer. Contract test 27 asserts a 429 carries CORS headers, which is the assertion that pins this ordering.

**The request-id value is validated before use** (`01-api-contract.md` §0): accepted only if it matches `^[A-Za-z0-9._-]{1,64}$`, else discarded and regenerated. It is attacker-controlled and is echoed into both a response header and a JSON log line, so an unvalidated value can inject a header or split a log record.

**Preflight:** `OPTIONS` on any `/api` route returns 204 with `Access-Control-Allow-Methods` and `Access-Control-Allow-Headers` including `X-Request-ID`; from a disallowed origin, 403.

Rate limiting is **not** middleware. It is applied as a route dependency on `POST /api/complaints` only, because it is a business rule about one expensive path, not a property of all HTTP traffic. It runs before body validation so that a 429 costs nothing (`BR-CACHE-006`).

### 2.4 Services

**`ComplaintService.submit(text, location, reporter_contact)`** — the orchestration that `FR-BE-013` describes:

1. Rate limit already checked by the route dependency.
2. Call the triage pipeline (M5.6) with text and location. It returns a validated `TriageResult` plus attribution (`triaged_by`, `latency_ms`, whether it was a fallback).
3. Persist via the repository, in one transaction.
4. Record the outcome in the Redis outcomes list (M5.8).
5. Invalidate the stats cache (M4.1).
6. Return the created complaint.

The service depends on the `TriageProvider` **protocol** and the cache **port**, never on concrete classes. This is checkable by grep and is how `NFR-ARCH-002` is verified.

**`ComplaintService.change_status(id, target)`**:

1. Load the complaint. Missing → `ComplaintNotFoundError` (404 — checked before the transition, `BR-STATUS-007`).
2. Consult the transition table in `domain/`. Not permitted → `InvalidTransitionError` carrying both status names, so the 409 message can be authored in one place.
3. Update, in the same transaction, touching `updated_at`.
4. Invalidate the stats cache (`AD-024`).

A rejected transition writes nothing at all (`BR-STATUS-006`).

**`StatsService.get_stats()`**:

1. Read through the cache port. Hit → return with `HIT`.
2. Miss → repository aggregation (`GROUP BY` in SQL, `NFR-PERF-005`), fill in explicit zeroes for every enum value (`AD-025`), store with the 30 s TTL, return with `MISS`.
3. Redis unreachable → compute and return with `MISS`, do not fail.

### 2.5 The transition table

Lives in `domain/`, as a mapping from status to the frozen set of permitted successors — a data structure, consulted by one function (`BR-STATUS-004`). Terminal states map to an empty set, so termination is a property of the data rather than a special case in the code. Self-transitions are absent from every entry and are therefore rejected without needing a rule of their own.

The table is also what the tests enumerate: the suite is parametrised over the full cross-product of statuses, asserting permitted edges succeed and all others 409. That is 16 cases from four lines of test code, and it means a future edit to the table cannot silently widen the machine.

### 2.6 Repositories

Async functions taking and returning domain values. No HTTP types in, no HTTP exceptions out.

Required operations (`FR-BE-017`): create, get by id, list with filters + pagination returning `(rows, total)`, update status, aggregate counts.

Two details that are easy to get wrong:

- **`total` and the page come from the same logical query.** Count with a windowed count or a second query in the same transaction; do not count the returned list.
- **The order is `created_at DESC, id DESC`** (`AD-016`), applied in SQL. The tie-break on `id` is what makes pagination stable when two rows share a timestamp — which the seed data, inserted in a loop, will absolutely produce.

### 2.7 Lifecycle

**Startup:** build settings → create engine and Redis client → resolve the triage provider → verify nothing (startup does **not** run migrations and does **not** create schema, `BR-DATA-001`).

**Shutdown on SIGTERM** (`FR-BE-021`): the ASGI server's graceful shutdown stops accepting new connections and waits for in-flight requests; the lifespan shutdown then closes the database pool and the Redis client. Log `shutdown.started` and `shutdown.completed`.

The thing most teams get wrong: the container must actually receive SIGTERM. That requires exec-form `CMD` (`FR-CTR-001`) so the server is PID 1 rather than a child of a shell that swallows the signal. This is a Dockerfile property that only shows up as a backend bug, which is why it is called out in both places.

### 2.8 Health and readiness

`/health` returns 200 from process state alone. It must be provably independent of the database — the test injects a session factory that raises and asserts 200 (`BR-OPS-001`).

`/ready` checks PostgreSQL (`SELECT 1`) and Redis (`PING`), each with a ~1 second timeout so a hanging dependency yields a fast 503 rather than a hanging probe, and names the failed dependency in the body.

---

## 3. Invariants this module must not violate

| Rule | Where it bites |
|---|---|
| `BR-VAL-005` | The create request model has no `category`/`priority`/`status` fields, and extra fields are rejected |
| `BR-STATUS-002/004/006/007` | Transition table, 404-before-409 ordering, no write on rejection |
| `BR-TRIAGE-001` | No complaint row exists without category, priority and `triaged_by` |
| `BR-TRIAGE-006` | No 5xx reaches the citizen because a provider failed |
| `BR-CACHE-006` | Rate limit decided before validation and before triage |
| `BR-OPS-001` | `/health` opens no connection |
| `BR-DATA-003` | No SQL outside `repositories/` |
| `BR-OPS-005` | Logs to stdout only |

---

## 4. Tasks

| ID | Task | Size | Owner | Depends on | Delivers | Done when |
|---|---|---|---|---|---|---|
| **T-M2-001** | **Contract-first skeleton.** App factory, all 11 endpoints present returning static stub responses, real `/health` and `/ready` (dependency checks stubbed to ok), `/openapi.json` generated. Dockerfile-ready. | M | Dev 1 | — | FR-BE-010 | `uvicorn` serves every path in the contract table; `curl /openapi.json` returns a schema; **Dev 2 can containerise it** |
| T-M2-002 | `domain/`: enums, `Complaint` Pydantic models (create/read), `TriageResult`, domain error types, transition table | S | Dev 1 | T-M2-001 | BR-VOCAB-*, BR-STATUS-002 | Enums match `BR-VOCAB` exactly; transition table is a mapping, not conditionals |
| T-M2-003 | `config.py`: typed settings for every variable in `00-conventions.md` §3; fail fast on unknown `TRIAGE_PROVIDER` | S | Dev 1 | T-M2-001 | FR-BE-020, FR-BE-018 | Startup with `TRIAGE_PROVIDER=nonsense` exits with a message naming the variable |
| T-M2-004 | Error model: exception handlers mapping domain errors to the `§4` body shape; FastAPI validation errors reshaped to `fields` | M | Dev 1 | T-M2-002 | BR-VAL-004, error model | Contract test 20 passes: every error body has `error.code`, `error.message`, `request_id` |
| T-M2-005 | Observability middleware: request id, structured JSON logging via `structlog`, Prometheus metrics with `path_template` labels | M | Dev 1 | T-M2-001 | FR-BE-023/024/026, NFR-OBS-001 | Log lines parse as JSON and carry `request_id`; `/metrics` parses; no per-id time series |
| T-M2-006 | Repositories: create, get, list+filter+paginate+total, update status, aggregate | M | Dev 1 | M3 T-M3-002 | FR-BE-016/017, NFR-PERF-005 | Integration tests green against real PostgreSQL; order is `created_at DESC, id DESC` |
| T-M2-007 | `StatusService` + transition table wiring + 409 message authoring | S | Dev 1 | T-M2-002, T-M2-006 | FR-BE-014, BR-STATUS-* | Parametrised test over all 16 status pairs passes |
| T-M2-008 | `ComplaintService.submit` orchestration (triage → persist → outcome → invalidate) | M | Dev 1 | M5 T-M5-006, M4 T-M4-001 | FR-BE-013, BR-TRIAGE-001 | Contract tests 1, 2, 15, 16 pass |
| T-M2-009 | `StatsService` with read-through cache and explicit zeroes | S | Dev 1 | M4 T-M4-002 | FR-BE-015, AD-025 | Contract tests 11, 12 pass |
| T-M2-010 | Routes: replace all stubs with real service calls; rate-limit dependency on POST only | M | Dev 1 | T-M2-007/008/009 | FR-BE-001…006, FR-BE-011 | All contract tests 1–12 pass; static check finds no SQL/provider import under `routes/` |
| T-M2-011 | `/health`, `/ready`, `/metrics`, `/api/version` for real | S | Dev 1 | T-M2-005 | FR-BE-007/008/009, AD-014 | Contract tests 13, 14 pass |
| T-M2-012 | Lifespan + SIGTERM drain; log `shutdown.*` | S | Dev 1 | T-M2-001 | FR-BE-021, NFR-REL-003 | A request in flight at SIGTERM completes; process exits after |
| T-M2-013 | CORS configured from settings | S | Dev 1 | T-M2-003 | FR-BE-012 | Dev-server origin works; deployed same-origin path unaffected |
| T-M2-014 | Static layer check added to `scripts/check_submission.py` | S | Dev 1 | T-M2-010 | NFR-ARCH-001/002/004 | Script fails on a deliberately added reverse import, then passes when removed |
| T-M2-015 | Backend test suite to ≥ 14 tests and ≥ 65 % coverage | M | Dev 1 | all above | FR-BE-027, NFR-TEST-003 | `pytest --cov` reports ≥ 65 %; suite green three runs in a row |

**T-M2-001 is the head of the critical path.** Dev 2 cannot start M6 without it. It should be the first thing merged, before any real logic exists.

---

## 5. Test plan for this module

Unit (no I/O): transition table cross-product; error-body shaping; settings validation; stats zero-filling.

Integration (real PostgreSQL + Redis via service containers, `AD-010`): every contract test in `01-api-contract.md` §14 except the starred Compose-level ones, plus:

- `/health` with a raising session factory → 200.
- `/ready` with Redis stopped → 503 naming `cache`.
- Filtered pagination across two pages → no duplicate ids.
- A 409 leaves `updated_at` unchanged.

No test calls a hosted model. CI runs with `TRIAGE_PROVIDER=simulated` (`NFR-TEST-001`).
