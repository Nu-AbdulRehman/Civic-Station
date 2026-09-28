# Civic-Station — Functional Requirements

**Status:** Authoritative. Revised 2026-09-25 by the specification audit (`docs/audit/01-specification-audit.md`).
**Source of truth:** `docs/planning/Civic-Station_Problem_Statement.md` — §2, §3 and §4 for behaviour and marks, and §5.2 and §5.3 for the engineering notes and the automatic deductions, which several requirements below derive from.
**Companion documents:** `MODULE-MAP.md`, `NON-FUNCTIONAL-REQUIREMENTS.md`, `BUSINESS-RULES.md`

## How to read this document

Every requirement carries an ID, a normative statement, acceptance criteria, and a verification method. The words **MUST**, **MUST NOT**, **SHOULD** and **MAY** are used in the RFC 2119 sense. A requirement marked **MUST** is not negotiable and is directly marked by the rubric or protected by an automatic deduction.

`Verify:` names how the requirement is proven. `Test` means an automated test in the repository. `CI` means a pipeline job. `Manual` means **a named command that a reader can run, plus the capture it produces in `docs/evidence/`** — a screenshot alone does not satisfy a `Manual` verification, because a screenshot cannot be re-run.

Where this document names a decision (`AD-nnn`), the resolution is in the log at the bottom of `docs/decisions/OPEN-DECISIONS.md`. **All 56 decisions are RESOLVED.** Do not re-decide one; if a design document and the log disagree, the log wins.

---

# M1 — Frontend

## M1.1 Submit view

### FR-FE-001 — Complaint submission form
**MUST.** The Submit view presents a form with a free-text complaint field, a location field, and an optional reporter contact field. Submitting the form issues exactly one `POST /api/complaints` request.
**Acceptance:** All three fields are present and labelled. No additional field is sent to the server that the API contract does not define.
**Verify:** Test (component), Manual.

### FR-FE-002 — Client-side validation mirrors server rules
**MUST.** The form validates complaint text length (10–2000 characters) and location length (3–200 characters) before submitting, and blocks submission with an inline, field-level message when either fails.
**Acceptance:** A 9-character complaint cannot be submitted and shows a message naming the field and the rule. The same input sent directly to the API returns 400 with a field-level error body.
**Constraint:** This validation *mirrors* the server rule; it never replaces it, and it is never the only place the rule exists. See `BR-VAL-001`.
**Verify:** Test (component).

### FR-FE-003 — Honest loading state
**MUST.** While a submission is in flight, the view shows a loading state that communicates that classification is in progress and disables resubmission.
**Acceptance:** The submit control is disabled and a progress indicator is visible for the entire duration of the request, **including a request that takes 21 seconds** — the worst case is a 10 s timeout plus one retry of up to 10 s plus jitter (`AD-004`), not 10 s. The client sets no timeout of its own below that bound and aborts the in-flight request on unmount.
**Rationale:** Triage is a synchronous network call to a third party; a form that appears idle invites double submission.
**Verify:** Test (component), Manual.

### FR-FE-004 — Render the triage outcome
**MUST.** On a 201 response the view renders the returned `category`, `priority`, `ai_summary` and `triaged_by` values from the response body.
**Acceptance:** All four values appear in the UI. `triaged_by` is displayed in a form a human can read (for example "classified by: rules (fallback)").
**Constraint:** The frontend renders the server's values verbatim. It MUST NOT compute, infer, or default any of them.
**Verify:** Test (component), Manual.

### FR-FE-005 — Submission error surfacing
**MUST.** The view distinguishes and surfaces, at minimum: a 400 field-level validation error (mapped back to the offending field), a 429 rate-limit response (including the wait implied by `Retry-After`), and any other failure (a generic but non-silent error state).
**Acceptance:** Each of the three cases renders a distinct, non-empty element identified by a stable `data-testid` — `error-field`, `error-ratelimit`, `error-generic` — and the 429 state displays the `Retry-After` value in seconds. A component test asserts the correct testid appears for each of the three responses.
**Verify:** Test (component).

## M1.2 Dashboard view

### FR-FE-006 — Paginated complaint list
**MUST.** The Dashboard lists complaints from `GET /api/complaints` with working pagination controls, showing the current page and the server-reported total.
**Acceptance:** Page size never exceeds 100. Navigating pages issues a new request with the correct `page` parameter; it does not slice a client-side array.
**Verify:** Test (component), Manual.

### FR-FE-007 — Filters
**MUST.** The Dashboard filters by `category`, `priority` and `status`, individually and in combination, by passing the filters to the server as query parameters.
**Acceptance:** Applying a filter issues a new request and resets pagination to the first page.
**Constraint:** Filtering MUST be server-side. Fetching all rows and filtering in the browser is a defect.
**Verify:** Test (component), Manual.

### FR-FE-008 — Status transition control
**MUST.** An operator can change a complaint's status from the Dashboard, issuing `PATCH /api/complaints/{id}/status`. The control offers **every** status value the schema defines, not only the ones the client guesses are reachable — the server owns the state machine (`BR-STATUS-005`), and `FR-FE-009` requires an invalid attempt to be possible so the 409 path is reachable from the UI.
**Acceptance:** The list reflects the new status after a successful transition without a full page reload. Selecting a status the state machine forbids issues the request and surfaces the 409, rather than being blocked client-side.
**Note:** This endpoint is unauthenticated. See `docs/NON-GOALS.md` and `AD-056`.
**Verify:** Test (component), Manual.

### FR-FE-009 — Surface the server's 409 verbatim
**MUST.** When a status transition is rejected with 409, the Dashboard displays the server's message text, which names the attempted transition. A generic "error" message is a defect.
**Acceptance:** Attempting `resolved → open` shows the server's message string in the UI, not a client-authored substitute.
**Constraint:** The frontend MUST NOT contain a list of valid transitions, and MUST NOT pre-empt the request by disabling "invalid" options based on client-side knowledge of the state machine. See `BR-STATUS-005`.
**Verify:** Test (component), Manual.

## M1.3 Stats view

### FR-FE-010 — Aggregate rendering
**MUST.** The Stats view renders counts grouped **by category, by priority and by status**, plus the total, from `GET /api/stats` (`AD-025`).
**Acceptance:** Every category, priority and status enum value the server returns is rendered, including zero counts, and the total is displayed.
**Verify:** Test (component), Manual.

### FR-FE-011 — Cache-state display
**MUST.** The Stats view displays whether the response was a cache hit or miss, read from the `X-Cache` response header.
**Acceptance:** Two consecutive loads within the TTL window show `MISS` then `HIT`.
**Verify:** Test (component), Manual.

## M1.4 API client and types

### FR-FE-012 — Typed API client
**MUST.** All backend calls go through a single typed API client module whose types are **generated** from the backend's OpenAPI schema by `openapi-typescript` and committed. Hand-written types that merely resemble the schema do not satisfy this.
**Acceptance:** No component issues `fetch`/`axios` directly. Regenerating types after a backend contract change and running `tsc --noEmit` fails on a breaking change — that failure is the mechanism, so the regeneration script is committed and named in the README.
**Verify:** CI (type check), code review.

### FR-FE-013 — Request ID propagation (frontend side)
**SHOULD.** The client generates and sends an `X-Request-ID` header (a UUIDv4) on every request, and displays it in every error state so a user-reported failure can be found in the logs.
**Acceptance:** A component test asserts the header is present on an outgoing request and that the value appears in the rendered error element.
**Verify:** Test (component), Manual.

## M1.5 Runtime configuration and serving

### FR-FE-014 — No baked-in backend URL
**MUST.** One frontend image runs unchanged in every environment. The backend address is resolved at container start or avoided entirely, never compiled into the bundle at build time.
**Acceptance:** The same image digest serves the Compose stack and the Kubernetes cluster, pointing at different backends, with no rebuild.
**Constraint:** The chosen mechanism is recorded in an ADR (`ADR-0002`). See `AD-001` in `OPEN-DECISIONS.md`.
**Verify:** Manual (one image, two environments), ADR.

### FR-FE-015 — Served by nginx from a multi-stage image
**MUST.** The production frontend is static assets served by `nginx:alpine`. The final image contains no Node runtime, no `node_modules`, and no source.
**Verify:** CI (image inspection), `NFR-PORT-002`.

### FR-FE-016 — No service-to-service `localhost`
**MUST.** No frontend artefact, configuration file or default refers to `localhost` for reaching the backend in any containerised environment. Services address each other by DNS service name (`BR-SEC-004`).
**Acceptance:** `scripts/check_submission.py` fails on a match for the regex `(?:https?://)?(?:localhost|127\.0\.0\.1)(?::\d+)?` in any tracked file under `frontend/`, `backend/`, `k8s/` or `compose*.yaml`, **excluding**: `vite.config.ts` and `.env.example` dev defaults, any line carrying the marker comment `# localhost-ok`, and the Ingress host `civic-station.localhost` (`AD-029`), which is a DNS name for a browser and a `Host` header, not a service-to-service address.
**Rationale:** §5.3 — automatic −8 deduction. The exclusion list exists because a bare grep for `localhost` flags legal strings; a check that cries wolf gets disabled.
**Verify:** CI (`scripts/check_submission.py`), with one unit test per exclusion.

## M1.6 Application shell

### FR-FE-017 — Error boundary
**MUST.** A React error boundary wraps the application so that a render-time exception produces a recoverable UI state rather than a blank page.
**Acceptance:** A component that throws during render is wrapped in the boundary; the rendered output contains a `data-testid="error-boundary"` element and a control that resets the boundary, and the test asserts the rest of the shell (navigation) is still present.
**Verify:** Test (component).

### FR-FE-018 — No business rules in the frontend
**MUST.** The frontend owns presentation and interaction only. Valid status transitions, category lists used for decisions, priority derivation, and any other domain rule originate from the backend.
**Clarification, drawing the line precisely.** Permitted: rendering a control whose options come from an enum in the generated OpenAPI types, because that enum *is* the server's answer and cannot drift from it. Forbidden: any value or predicate the frontend authors itself that duplicates a server rule — a hard-coded transition map, a hard-coded category list, a function deciding which statuses follow which, or a priority computed from text.
**Acceptance:** `frontend/src/` contains no literal array or object mapping one status to another, and no category or priority string literal outside test fixtures and display labels. A grep for the status values in non-test source returns only the generated types module and label lookups.
**Verify:** Code review, CI grep, `BR-STATUS-005`.

### FR-FE-019 — No secrets in frontend code
**MUST.** No API key, token or credential appears in frontend source, environment files consumed at build time, or the served bundle.
**Acceptance:** CI greps the built `dist/` output for the patterns in `NFR-SEC-008`'s named set (`gsk_[A-Za-z0-9]{20,}` for Groq keys, `AIza[A-Za-z0-9_-]{35}` for Google keys, `-----BEGIN .* PRIVATE KEY-----`, and any assignment to a name matching `(?i)(api[_-]?key|secret|token|password)` whose value is a literal of 16 or more characters) and fails on any match.
**Verify:** CI (secret scan with the pattern set above), code review.

## M1.7 Frontend tests

### FR-FE-020 — Component test suite
**MUST.** At least five Vitest component tests pass in CI, **one per requirement in the mapping below**. Each asserts a specific rendered output for a specific input or response — a test that only asserts a component renders without throwing does not count toward the five.
**Required mapping**, so "meaningful" is a checklist rather than a judgement: validation blocking (`FR-FE-002`), loading state including the 21 s case (`FR-FE-003`), triage result rendering (`FR-FE-004`), 409 message surfaced verbatim (`FR-FE-009`), cache-state display MISS then HIT (`FR-FE-011`).
**Acceptance:** Five named test files exist, one per row above, each asserting on a `data-testid` or on exact text; `vitest run` passes in CI; each test fails if its requirement's behaviour is removed.
**Verify:** CI.

---

# M2 — Backend

## M2.1 Routes layer — the API contract

The endpoint table below is normative. Status codes not listed are not part of the contract and MUST NOT be returned for the listed conditions.

### FR-BE-001 — `POST /api/complaints`
**MUST.** Accepts a complaint, validates it, triages it, persists it, and returns **201** with the created resource. The response body is **exactly** the `Complaint` schema — `id`, `text`, `location`, `reporter_contact`, `category`, `priority`, `status`, `ai_summary`, `triaged_by`, `triage_confidence`, `triage_latency_ms`, `created_at`, `updated_at` — with no additional fields, so the generated client and the contract cannot drift.
**Error behaviour:**
- **400** with a field-level error body when validation fails (body identifies each offending field and the rule violated).
- **429** with a `Retry-After` header when the caller exceeds the rate limit.
- It MUST NOT return 5xx because the triage provider failed. See `BR-TRIAGE-006`.
**Verify:** Test (integration), CI (Compose smoke).

### FR-BE-002 — `GET /api/complaints/{id}`
**MUST.** Returns **200** with the complaint, or **404** when no complaint with that id exists.
**Acceptance:** A malformed (non-UUID) id returns **400** with the standard error body naming the `id` path parameter — not 404, not 422, and never 500. FastAPI's default 422 for a path-parameter coercion failure is remapped to 400 by the error handler, so the API has one validation status code rather than two.
**Verify:** Test.

### FR-BE-003 — `GET /api/complaints`
**MUST.** Returns a filtered, paginated list. Filters: `category`, `priority`, `status` — each optional, combinable. Pagination: `page` (integer ≥ 1, default 1) and `page_size` (integer 1–100, default 20). The response includes `items`, `total` (rows matching the filters, not the page length), `page` and `page_size`. Default order is `created_at DESC, id DESC` (`AD-016`).
**Acceptance:** `page_size=1000` is **rejected with 400** naming the limit (`AD-015`) — never silently clamped. `page` beyond the last page returns **200 with an empty `items` array** and the true `total`, not a 404. An unknown enum value in a filter is a 400. Filtering, ordering and pagination happen in SQL, not in Python after loading all rows.
**Verify:** Test.

### FR-BE-004 — `PATCH /api/complaints/{id}/status`
**MUST.** Applies a status transition, enforcing the state machine. Returns **200** on success, **400** when the requested value is not a member of the status enum, **404** for an unknown id, and **409** for a well-formed but forbidden transition, with a message naming both the current and the requested status.
**Precedence, so the same request cannot yield two answers:** body validation first (**400**), then existence (**404**), then the transition table (**409**). A `PATCH` on an unknown id carrying an invalid status value therefore returns **400**, not 404 — the request is malformed regardless of which row it addresses.
**Acceptance:** Parametrised over the full 4 × 4 matrix of current and requested status: 4 legal edges return 200, the 4 self-transitions and the 8 remaining forbidden edges return 409, and the message contains both status names.
**Note:** Unauthenticated. See `docs/NON-GOALS.md` and `AD-056`.
**Verify:** Test (parametrised over all 16 edges).

### FR-BE-005 — `GET /api/stats`
**MUST.** Returns aggregate counts **by category, by priority and by status, plus a total** (`AD-025`), each as an object keyed by every enum value with explicit zeroes, so the client never has to guess which keys exist. Also returns `generated_at`, **the time the aggregation was computed** — not the time it was served — so a cached response carries the age of its data. The response is served through the Redis read-through cache with a 30-second TTL and carries an `X-Cache: HIT` or `X-Cache: MISS` header.
**Acceptance:** First call `MISS`, second call within 30 s `HIT` with an identical `generated_at`. **Any successful insert or status update** invalidates the cached value immediately (`AD-024`, `FR-CACHE-002`), so the next call is a `MISS` with a newer `generated_at`.
**Verify:** Test (integration), CI (Compose smoke).

### FR-BE-006 — `GET /api/meta/providers`
**MUST.** Returns `configured` (the `TRIAGE_PROVIDER` value), `active_provider` (the resolved `triaged_by` identity, for example `llm:groq`), and `recent`: the last 20 triage outcomes, held in a Redis list so the answer is global rather than per-pod once the HPA has scaled (`AD-009`).
**Each `recent` entry carries exactly:** `complaint_id` (UUID), `provider` (the `triaged_by` value), `latency_ms` (integer), `fallback` (boolean), `error_class` (string, null unless `fallback` is true), `at` (timestamp). Stated as a closed field list because `FR-AI-013` reads it to report per-provider latency.
**Acceptance:** After a forced provider failure, the most recent entry has `fallback: true`, `provider: "rules:fallback"` and a non-null `error_class` naming the exception type.
**Verify:** Test.

### FR-BE-007 — `GET /health`
**MUST.** Liveness only. Returns 200 whenever the process is alive and able to serve HTTP.
**Constraint:** It **MUST NOT** open a database connection, query Redis, or depend on any external dependency. See `BR-OPS-001`.
**Verify:** Test (assert no DB session is created — for example by injecting a session factory that raises).

### FR-BE-008 — `GET /ready`
**MUST.** Readiness. Returns 200 only when both PostgreSQL and Redis are reachable. Otherwise returns **503** with a body naming the dependency that failed.
**"Reachable" is defined, so the check is writable:** PostgreSQL answers `SELECT 1` and Redis answers `PING`, each within a **1-second timeout** (`READINESS_TIMEOUT_SECONDS`, default 1). A timeout counts as unreachable. The two checks run concurrently, so the worst case for the whole endpoint is 1 second, not 2 — a readiness probe that takes longer than its own `periodSeconds` is a second failure mode.
**Acceptance:** With Redis stopped, `/ready` returns 503 and the body's `failed` field is `"redis"`, while `/health` still returns 200. With both stopped, both dependencies are named.
**Verify:** Test (integration), Manual (`docker compose stop cache && curl -i localhost:8000/ready`).

### FR-BE-009 — `GET /metrics`
**MUST.** Prometheus text exposition format. The exposed series are named, because a test cannot assert on "at minimum":

| Series | Type | Labels | Unit |
|---|---|---|---|
| `http_requests_total` | Counter | `method`, `path_template`, `status` | — |
| `http_request_duration_seconds` | Histogram | `method`, `path_template` | seconds |
| `triage_duration_seconds` | Histogram | `provider` | seconds |
| `triage_fallback_total` | Counter | `from_provider`, `error_class` | — |
| `triage_cache_hits_total` | Counter | — | — |
| `triage_cache_misses_total` | Counter | — | — |
| `stats_cache_hits_total` | Counter | — | — |
| `stats_cache_misses_total` | Counter | — | — |
| `rate_limiter_unavailable_total` | Counter | — | — |

Histogram buckets for both duration histograms: `0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25`, chosen to straddle the 10 s triage timeout. `path_template` is the route template, never the raw path, or one complaint id becomes one time series. `error_class` is restricted to a closed set — `Timeout`, `RateLimited`, `ServerError`, `ValidationFailed`, `Other` — mapped from the exception, for the same cardinality reason.
**The four cache counters exist so `FR-AI-014`'s hit rate has a source**; without them the measured hit rate is a number with no origin.
**Acceptance:** Output parses with `prometheus_client.parser.text_string_to_metric_families`; every series above is present; `triage_fallback_total` increases by 1 when a fallback occurs; `triage_cache_hits_total` increases on a duplicate submission.
**Verify:** Test.

### FR-BE-010 — Machine-readable schema endpoint
**MUST.** The service publishes its OpenAPI schema over HTTP at `/openapi.json`. This is the contract the frontend client in `FR-FE-012` is generated from.
**Interactive docs at `/docs`** are served in every environment. They expose no data the API does not already expose and no write the API does not already permit, and they are the fastest route to a live demonstration at viva, so gating them by environment would cost more than it protects.
**Note on the count:** the rubric refers to "all ten endpoints". The nine behavioural endpoints above plus this schema endpoint are those ten. `GET /api/version` (`FR-BE-029`) is an eleventh, added by `AD-014`; the README API table lists all eleven and says which ten the rubric line refers to.
**Verify:** CI (client generation and schema diff).

### FR-BE-011 — Routes contain no business rules
**MUST.** Route handlers parse input, call exactly one service operation, map the result to a response model and status code, and return. A route MUST NOT open a database session, issue SQL, call a provider directly, or decide a transition.
**Acceptance, two checks because a grep alone is not enough:** (a) `scripts/check_submission.py` fails if any module under `routes/` imports `sqlalchemy`, `session`, `engine`, or a `repositories.*` symbol; (b) a test injects a session factory that raises on use and asserts every route in the OpenAPI schema that is not `/health` still returns its documented status — proving no route acquires a session outside the service layer, which the grep cannot show.
**Verify:** Code review, CI (`scripts/check_submission.py`), Test.

### FR-BE-012 — CORS
**MUST.** The backend carries a CORS configuration for the **direct-access topologies** — the Vite dev server and the CI integration tests — where the browser or client origin differs from the API origin. In the Compose and Kubernetes topologies the frontend reaches the API same-origin through the nginx `/api` proxy and the Ingress (`AD-001`), so no preflight occurs there and CORS is not exercised.
**Allowed origins** come from `CORS_ALLOW_ORIGINS`, a comma-separated list, never a hard-coded string and never `*`. Defaults: `http://localhost:5173,http://localhost:8080` in dev, **empty in production**.
**Ordering:** the CORS middleware is **outermost**, so a 4xx produced by rate limiting, request-id or validation middleware still carries CORS headers — otherwise the browser reports an opaque CORS failure instead of the 429 the server actually sent.
**Preflight:** `OPTIONS` on any `/api` route returns **204** with `Access-Control-Allow-Methods` and `Access-Control-Allow-Headers` including `X-Request-ID`; an `OPTIONS` from a disallowed origin returns 403.
**Acceptance:** A request from `http://localhost:5173` succeeds with the header present; one from `http://evil.example` is rejected; a 429 response carries CORS headers.
**Verify:** Test, Manual.

## M2.2 Services layer

### FR-BE-013 — Triage orchestration service
**MUST.** A single service operation owns the submission flow: validate, consult the triage cache, invoke the selected provider through the resilience pipeline, apply the fallback rule, persist, invalidate the stats cache, and record the triage outcome for observability.
**Constraint:** The service depends on the `TriageProvider` interface, never on a concrete provider class.
**Verify:** Test (unit, with injected fakes).

### FR-BE-014 — Status transition service
**MUST.** A service operation applies a status change by consulting an explicit transition table and raising a domain error carrying the attempted transition when the edge is not permitted.
**Constraint:** The implementation is a data structure (a mapping of current status to permitted next statuses), not a chain of `if` statements. See `BR-STATUS-004`.
**Verify:** Test (parametrised over every legal and illegal edge), code review.

### FR-BE-015 — Statistics service
**MUST.** A service operation computes aggregate counts **by category, by priority and by status, plus a total** (`AD-025`), and is the only caller of the stats cache.
**Acceptance:** Counts are computed by the database (`GROUP BY`), not by loading rows into Python. Every enum value appears in the result with an explicit zero when no row matches. On a cache miss the single-flight lock of `AD-055` applies, so a burst of concurrent misses runs one aggregation, not N.
**Verify:** Test.

## M2.3 Repositories layer

### FR-BE-016 — All SQL lives in repositories
**MUST.** Every SQL statement and every ORM query in the system is issued from a module under `repositories/`. No other package imports the database session, engine, or ORM query API.
**Verify:** Code review, static check.

### FR-BE-017 — Repository operations
**MUST.** The repository layer exposes, at minimum: create complaint, get complaint by id, list complaints with filters and pagination returning rows plus a total count, update complaint status, and aggregate counts.
**Constraint:** Repository functions accept and return domain-level values; they do not accept HTTP request objects and do not raise HTTP exceptions.
**Verify:** Test (integration against a real PostgreSQL).

## M2.4 Provider ports

### FR-BE-018 — Provider selection by configuration
**MUST.** The active triage provider is chosen at startup from the `TRIAGE_PROVIDER` environment variable. An unknown value fails fast at startup with a clear error rather than silently defaulting.
**Verify:** Test.

### FR-BE-019 — Cache port
**MUST.** Redis access goes through a provider/port module. Services depend on the port, not on the Redis client library.
**Acceptance:** `redis` is imported in exactly one package, `providers/cache/`; `scripts/check_submission.py` fails if it is imported anywhere under `routes/`, `services/` or `repositories/`. A unit test substitutes an in-memory fake implementing the port and the stats service passes unchanged.
**Verify:** Code review, CI, Test.

## M2.5 Application lifecycle

### FR-BE-020 — Configuration from environment
**MUST.** All configuration is read from the environment into a single typed settings object at startup. No literal credential, host or port appears in application code, and no module calls `os.environ` directly.
**The complete set**, which `docs/design/00-conventions.md` §3 mirrors: `DATABASE_URL`, `REDIS_URL`, `TRIAGE_PROVIDER`, `TRIAGE_MODEL`, `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, `GROQ_API_KEY`, `TRIAGE_TIMEOUT_SECONDS`, `TRIAGE_CACHE_TTL_SECONDS`, `PROMPT_VERSION`, `STATS_CACHE_TTL_SECONDS`, `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`, `TRUSTED_PROXY_CIDRS`, `READINESS_TIMEOUT_SECONDS`, `CORS_ALLOW_ORIGINS`, `LOG_LEVEL`, `APP_VERSION`, `BACKEND_PORT` (default 8000), `SIMULATED_SEED`, `SIMULATED_FAILURE_MODE`.
**Acceptance:** Startup with `TRIAGE_PROVIDER=nonsense` exits non-zero with a message naming the variable and listing the legal values (`FR-BE-018`). A test asserts the settings object has one attribute per name above, and `scripts/check_submission.py` fails on any `os.environ` or `os.getenv` outside the settings module.
**Verify:** Code review, Test, CI secret scan.

### FR-BE-021 — Graceful shutdown on SIGTERM
**MUST.** On SIGTERM the process stops accepting new connections, allows in-flight requests to complete, closes database and Redis pools, and exits cleanly within the termination grace period.
**Values:** `terminationGracePeriodSeconds: 30` on the backend Deployment, and a `preStop` hook of **`sleep 5`**. The ordering is the point: `preStop` runs *before* SIGTERM, and 5 seconds is long enough for the Endpoints controller to remove the pod from the Service across all nodes, so no new request is routed to a pod that is about to stop. 30 seconds then leaves 25 for in-flight work against a 21-second worst-case request (`FR-FE-003`).
**Acceptance:** A request in flight when SIGTERM arrives completes with a normal response; the process does not exit until it does. Measured: `docker compose exec backend kill -TERM 1` during an in-flight `POST` yields a 201, and the container exits 0 within 30 s.
**Verify:** Test, Manual (`scripts/demo_sigterm.sh`, output captured to `docs/evidence/sigterm.txt`), used again by `FR-LOAD-004`.

### FR-BE-022 — No schema DDL at startup
**MUST.** The application never creates, alters or drops schema objects at startup. Schema changes come only from Alembic migrations.
**Rationale:** Rubric D, 4 marks.
**Verify:** Code review, static check (no `create_all`, no `CREATE TABLE` outside `alembic/versions/`).

## M2.6 Observability

### FR-BE-023 — Structured JSON logging to stdout
**MUST.** Every log line is a single-line JSON object written to stdout. No log file is written.
**Field names and formats are fixed**, so a log-parsing test can be written: `ts` (RFC 3339 with milliseconds, UTC, for example `2026-09-25T14:03:11.482Z`), `level` (one of `DEBUG`, `INFO`, `WARNING`, `ERROR`), `msg` (string), `request_id` (UUID string), `logger` (module path). Handlers may add fields; none of the five above may be renamed or omitted.
**Never logged at any level:** `reporter_contact`, the API key, or any `Authorization` header value. Complaint `text` is logged **only at `DEBUG`**, and `LOG_LEVEL` is `INFO` in every committed configuration, so citizen text does not reach a log shipper by default (`NFR-PRIV-002`).
**Acceptance:** A captured log line parses as JSON and contains all five fields with the types above; a test at `INFO` asserts complaint text is absent from the output.
**Verify:** Test (log capture), Manual (`docker compose logs backend | head -1 | python -m json.tool`).

### FR-BE-024 — Request ID propagation
**MUST.** Every request has a `request_id` taken from the inbound `X-Request-ID` header, or generated when absent, attached to every log line emitted while handling that request, and returned in the response headers.
**The inbound header is validated before use**, because it is attacker-controlled and is echoed into both responses and logs: accept it only if it matches `^[A-Za-z0-9._-]{1,64}$`, otherwise discard it and generate a UUIDv4. Without this, a crafted header can inject newlines into JSON logs or split a response header.
**Acceptance:** A request with a valid `X-Request-ID` gets it back unchanged; one carrying `a\r\nX-Injected: 1` or a 500-character value gets a generated UUID instead, and the log line for that request contains the generated value.
**Verify:** Test.

### FR-BE-025 — Fallback warning log
**MUST.** Every triage fallback emits exactly one `WARNING` line carrying `complaint_id`, `from_provider`, and `error_class` from the closed set in `FR-BE-009`.
**Acceptance:** A forced provider failure produces exactly one `WARNING` — not zero, not one per retry attempt — and the line contains all three fields.
**Verify:** Test.

### FR-BE-026 — Metrics instrumentation
**MUST.** The metrics named in `FR-BE-009` are incremented or observed by middleware and by the triage pipeline, not by route handlers individually.
**Acceptance:** No route module imports the metrics registry; a test drives one request through the app and asserts `http_requests_total` rose by exactly 1 for the matching `path_template`.
**Verify:** Test, code review.

## M2.7 Backend tests

### FR-BE-027 — Test suite size, determinism and coverage
**MUST.** At least 14 backend tests spanning unit and integration levels, deterministic on every run, with statement coverage of `app/` at or above 65 %, enforced in CI.
**Constraint:** No test may call a hosted LLM. No test may contain `sleep` as a synchronisation mechanism. CI runs with `TRIAGE_PROVIDER=simulated`.
**Verify:** CI.

### FR-BE-028 — The mandatory fallback test
**MUST.** A test injects a triage provider that always raises and asserts that `POST /api/complaints` still returns **201** and that the persisted `triaged_by` equals `"rules:fallback"`.
**Note:** The problem statement calls this out as the single most important test in the assignment.
**Verify:** CI.

### FR-BE-029 — `GET /api/version`
**MUST.** Returns **200** with `{"version": "<commit sha>", "provider": "<the active_provider value>"}`, where `version` is read from the `APP_VERSION` environment variable at runtime and `provider` is the same resolved identity that `FR-BE-006` reports as `active_provider` — not the `configured` value, so the two endpoints cannot disagree.
**Constraint:** `APP_VERSION` is supplied by the Deployment manifest and by `compose.prod.yaml`. It **MUST NOT** be a Docker build argument or baked into the image in any form, because that would make the image commit-specific and break `FR-FE-014` (`AD-014`, `AD-034`).
**Acceptance:** Two containers started from the **same image digest** with different `APP_VERSION` values report their own value. When `APP_VERSION` is unset the response is `"unknown"`, never an error.
**Rationale:** Answers "what is production running?" in one request, which is the operational question `ADR-0003` exists to make answerable. Serves `NFR-OPS-004`.
**Verify:** Test, Manual (one digest, two environments — the same capture that serves `FR-FE-014`).

---

# M3 — Data layer

### FR-DATA-001 — Alembic-managed schema
**MUST.** The schema is created and evolved exclusively by Alembic revisions committed under `backend/alembic/versions/`. Every revision has a working `downgrade`.
**Verify:** CI (migrate up from empty, then down, then up again).

### FR-DATA-002 — Complaint table columns
**MUST.** The `complaints` table contains at least:

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | primary key, **server-generated**, `DEFAULT gen_random_uuid()` (`AD-021`) |
| `text` | text | `NOT NULL`, `CHECK (char_length(text) BETWEEN 10 AND 2000)`, enforced in the database as well as in the application. **The trimmed value is what is persisted** — the application strips leading and trailing whitespace before validating, so the app and the database measure the same string |
| `location` | text | `NOT NULL`, `CHECK (char_length(location) BETWEEN 3 AND 200)`, trimmed as above |
| `reporter_contact` | text | nullable, `CHECK (char_length(reporter_contact) <= 200)` — bounded because an unbounded free-text field is an unbounded storage and log-exposure surface |
| `category` | enum | `NOT NULL`; `water`, `electricity`, `sanitation`, `roads`, `streetlights`, `other` |
| `priority` | enum | `NOT NULL`; `high`, `normal`, `low` |
| `status` | enum | `NOT NULL`; `open`, `in_progress`, `resolved`, `rejected`; default `open` |
| `ai_summary` | text | **`NOT NULL`**, `CHECK (char_length(ai_summary) <= 140)`. Not nullable because `AD-023` makes every provider produce one, including the rules path — a guarantee the contract makes must be one the database keeps |
| `triaged_by` | `varchar(32)` | `NOT NULL`, `CHECK (triaged_by IN ('llm:groq','llm:ollama','rules','rules:fallback','simulated'))` (`AD-020`). `'simulated'` is in the set because CI runs `TRIAGE_PROVIDER=simulated` and a successful simulated triage must persist a legal, truthful value |
| `triage_confidence` | double precision | **`NOT NULL`**, `CHECK (triage_confidence BETWEEN 0 AND 1)` (`AD-026`). The rules path uses a fixed `0.35` |
| `triage_latency_ms` | integer | `NOT NULL`, `CHECK (triage_latency_ms >= 0)`; measured wall clock on every path, not estimated |
| `created_at` | timestamptz | `NOT NULL`, default `now()`, UTC |
| `updated_at` | timestamptz | `NOT NULL`, default `now()`, UTC, maintained on update; `CHECK (updated_at >= created_at)` |

**Retention:** none. Rows are kept indefinitely and there is no delete endpoint. This is a deliberate, documented limitation rather than an oversight — see `ADR-0004` and `docs/NON-GOALS.md`, which name what a real municipal deployment would require.
**Verify:** Test (integration asserts each `CHECK` rejects: text of 9 and 2001 characters, location of 2, `ai_summary` of 141, `triage_confidence` of 1.5, `triaged_by` of `'nope'`, `updated_at` before `created_at`), migration review.

### FR-DATA-003 — Required indexes
**MUST.** Three indexes exist (`AD-049`), each paired with the exact query it serves, and `docs/ENGINEERING-NOTES.md` states that pairing:

| Index | Query it serves |
|---|---|
| `ix_complaints_created_at_id` on `(created_at DESC, id DESC)` | The unfiltered default listing: `… ORDER BY created_at DESC, id DESC LIMIT :n OFFSET :m`. Includes `id` because `AD-016`'s stable pagination depends on the tie-break, and an index on `created_at` alone cannot supply it |
| `ix_complaints_status_priority_created` on `(status, priority, created_at DESC)` | The operations view: `… WHERE status = :s AND priority = :p ORDER BY created_at DESC`. Carries `created_at` so a filtered page is an index scan, not a scan plus a sort |
| `ix_complaints_category_created` on `(category, created_at DESC)` | The category filter: `… WHERE category = :c ORDER BY created_at DESC`. `category` is a first-class filter in `FR-BE-003` and was previously unindexed |

**Acceptance:** Each named query appears in `repositories/`, and `EXPLAIN` on it shows the paired index in use with no separate sort step. `RUB-D-03` marks two justified indexes; three justified indexes satisfy that line.
**Verify:** Migration review, Test (`EXPLAIN` assertions), notes cross-check.

### FR-DATA-004 — Idempotent seed command
**MUST.** `python -m seeds.complaints` loads **exactly 30** complaints written in Urdu-influenced English. Running it a second time changes no rows and creates no duplicates.
**Distribution, stated as counts so "a mix" is checkable:** at least 4 rows in each of the six categories; at least 8 `high`, 8 `normal` and 8 `low`; and statuses **12 `open`, 8 `in_progress`, 6 `resolved`, 4 `rejected`** — the terminal statuses matter because the Dashboard's 409 demonstration needs a `resolved` row to attempt an invalid transition against.
**"Realistic" is defined by construction:** each row is hand-written, names a plausible Karachi-area street or sector, and uses the register of the brief's own example ("burst water main flooding Street 12 since fajr, water entering ground floors"). Seeded rows carry `triaged_by = 'rules'` and a plausible `triage_latency_ms`, because no model saw them — inventing `llm:groq` attribution would make `BR-VOCAB-004` false.
**Idempotency:** deterministic UUIDv5 over the fixed namespace `6f2a1c94-3e5b-4d80-9a17-c0b8e4f21d63` plus the complaint text, with `ON CONFLICT (id) DO NOTHING` (`AD-022`).
**Exemptions, granted explicitly:** the seed supplies `id` (`BR-VAL-006`), writes non-`open` statuses (`BR-STATUS-001`) and issues SQL from outside `repositories/` (`BR-DATA-003`). It is an administrative fixture loader, not a client; each of those three rules names this exemption.
**Acceptance:** `SELECT count(*)` is 30 after the first run and 30 after the second; the per-category, per-priority and per-status counts match the table above; ids are identical across two fresh databases on different machines.
**Verify:** Test, CI (run twice, compare counts and a checksum of ordered ids).

### FR-DATA-005 — Persistence across restarts
**MUST.** `docker compose down` followed by `docker compose up` preserves every row. Deleting the PostgreSQL pod on Kubernetes preserves every row.
**Acceptance, so the demonstration has a pass condition:** seed, record `SELECT count(*)` and the `id` of the newest row; restart; assert the count is unchanged and that `id` is still retrievable through `GET /api/complaints/{id}`. Both the Compose and the Kubernetes case use the same two assertions. Note that `docker compose down -v` **does** destroy data — the volume flag is the difference, and the demonstration must show the form without it.
**Verify:** CI (Compose case, scripted), Manual (Kubernetes case: `kubectl delete pod postgres-0 -n civic-station`, captured to `docs/evidence/persistence-k8s.txt`), both on video.

---

# M4 — Cache layer

### FR-CACHE-001 — Stats read-through cache
**MUST.** `GET /api/stats` reads through Redis with a 30-second TTL (`STATS_CACHE_TTL_SECONDS`) and reports `X-Cache: HIT|MISS` accurately.
**Stampede control (`AD-055`):** on a miss the caller takes a short Redis lock (`SET cs:stats:lock <token> NX EX 5`); the winner aggregates and caches, losers poll for the cached key for up to 250 ms and then fall through to a direct query. Without this, every invalidating write is followed by N concurrent identical aggregations, which is exactly the load the cache exists to prevent.
**Acceptance:** First call `MISS`, second within the TTL `HIT`. Twenty concurrent requests against a cold cache produce **one** aggregation query, asserted by counting `stats_cache_misses_total` and the query count.
**Verify:** Test (integration, including the concurrent case), CI (Compose smoke asserts MISS then HIT).

### FR-CACHE-002 — Write invalidation
**MUST.** A successful complaint creation, and any successful status change, invalidates the cached stats value immediately rather than waiting for the TTL.
**Acceptance:** Submit a complaint, then request stats: the new complaint is included and the header reports `MISS`.
**Verify:** Test (integration).

### FR-CACHE-003 — Distributed rate limiter
**MUST.** `POST /api/complaints` is rate-limited per client IP by a **fixed-window** counter in Redis — `INCR` on a key of `cs:rl:<ip>:<epoch_minute>` followed by `EXPIRE` to the window length (`AD-018`). **10 requests per 60 seconds** (`RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`). Exceeding the limit returns **429** with `Retry-After` set to **the whole seconds remaining in the current window, as delta-seconds** — not an HTTP date, and never a fixed constant.
**Fixed window, not token bucket:** the algorithm is named because the two differ in burst behaviour at the boundary, and a test asserting "the 11th request is a 429" is only well-defined once one of them is chosen.
**Client IP (`AD-054`):** behind nginx and an Ingress the socket peer is a proxy, so the limiter reads the **last** entry of `X-Forwarded-For`, and only when the immediate peer falls inside `TRUSTED_PROXY_CIDRS`; otherwise it uses the socket address. The last entry rather than the first, because the first is client-supplied and therefore forgeable — trusting it lets any caller bypass the limiter with one header.
**Constraint:** The limiter state MUST live in Redis. An in-process dictionary is a defect, because it multiplies the effective limit by the replica count once the HPA scales out. Verified by `FR-CACHE-007`.
**Only `POST /api/complaints` is limited.** The `GET` endpoints are not, which is what lets the k6 load test drive them freely (`AD-017`).
**Acceptance:** Requests 1–10 in a window return 201, the 11th returns 429 with `Retry-After` between 1 and 60. A request forging `X-Forwarded-For: 1.2.3.4` from an untrusted peer is still counted against its real address.
**Verify:** Test (integration, exceed the limit and assert 429 + header; plus the spoofing case).

### FR-CACHE-004 — Triage content-hash cache
**MUST.** Triage results are cached in Redis with a **24-hour TTL** (`TRIAGE_CACHE_TTL_SECONDS`, default 86400). A cache hit skips the provider call entirely.
**The key is fully specified** (`AD-019`), because "a hash of the normalised complaint content" leaves three of its four inputs unstated: `SHA-256` of `normalise(redacted_text) + "|" + normalise(location) + "|" + provider_name + "|" + PROMPT_VERSION`, where `normalise` lower-cases, collapses runs of whitespace to one space, and strips surrounding punctuation. Provider and prompt version are in the key so that changing either never serves a result produced under the old configuration. Redaction happens **before** hashing (`AD-003`), so `redact()` must be deterministic or the cache silently stops hitting.
**Acceptance:** Submitting identical text twice results in one provider invocation and increments `triage_cache_hits_total` once. Changing `PROMPT_VERSION` causes the next identical submission to miss.
**Verify:** Test (assert the provider is called once for two identical submissions; assert a miss after a prompt-version change).

### FR-CACHE-005 — Redis persistence
**MUST.** Redis runs with `appendonly yes` on the named volume `redisdata`, and `docs/ENGINEERING-NOTES.md` contains the team's written justification for why a cache is given durable storage.
**Memory policy, because one Redis serves four workloads** (stats cache, triage cache, rate-limiter counters, outcomes list — all on database 0): `maxmemory 256mb` with `maxmemory-policy allkeys-lru`. The consequence is stated rather than discovered: under pressure LRU may evict a rate-limiter counter, which fails open by the same reasoning as `AD-008`, and may evict the outcomes list, which only degrades `/api/meta/providers`. Neither loses durable data, because durable data is in PostgreSQL.
**Acceptance:** `CONFIG GET appendonly` returns `yes`; `CONFIG GET maxmemory-policy` returns `allkeys-lru`; the volume is named in both Compose files and in the Kubernetes PVC. The justification names which of the four workloads would actually be missed after a restart.
**Verify:** Compose/manifest review, Test (`CONFIG GET` assertions), notes cross-check.

### FR-CACHE-006 — Degradation behaviour
**MUST.** Each Redis-dependent feature has a defined, implemented and tested behaviour when Redis is unavailable:

| Feature | Behaviour when Redis is down |
|---|---|
| Rate limiter | **Fail open**, allow the request, one `ERROR` log per occurrence, increment `rate_limiter_unavailable_total` (`AD-008`) |
| Stats cache | Serve a direct database aggregation with `X-Cache: MISS` |
| Triage cache | Call the provider; no caching |
| Outcomes list | `/api/meta/providers` returns `recent: []` and still reports `configured` and `active_provider` |

`/ready` returns 503 naming Redis throughout, so Kubernetes removes the pod from the Service and bounds how long the fail-open window is reachable (`FR-BE-008`). That bound is the whole argument for failing open rather than closed, and it belongs in the engineering notes and in `ADR-0005`.
**Acceptance:** With Redis stopped, `POST /api/complaints` returns 201, `GET /api/stats` returns 200 with `MISS`, `/api/meta/providers` returns 200 with an empty `recent`, `/ready` returns 503 naming Redis, and `/health` returns 200.
**Verify:** Test (integration with Redis stopped), `ADR-0005`.

### FR-CACHE-007 — The limiter is provably distributed
**MUST.** A test proves the limiter's state is shared across replicas rather than per-process (`AD-053`): with **4 backend replicas** behind one Service, **30 `POST /api/complaints` requests from a single client IP within one 60-second window** yield **exactly 10 × 201 and 20 × 429**.
**Rationale:** This is the assertion that distinguishes a correct implementation from the common wrong one. An in-process limiter would allow 40 — four times the configured limit — and would still pass every single-replica test. `NFR-SCALE-001` names this as its measure, and the k6 HPA run does not exercise it because that run drives un-rate-limited `GET` endpoints (`AD-017`).
**Acceptance:** The counts are exact, not approximate, and each 429 carries `Retry-After`.
**Verify:** Test (integration, Compose with `--scale backend=4`), CI.

---

# M5 — AI / triage layer

### FR-AI-001 — The provider interface
**MUST.** A `TriageProvider` protocol exposes a `name` and an **`async triage(text, location) -> TriageResult`** operation. `TriageResult` is a Pydantic model with `category`, `priority`, `summary` (≤ 140 characters) and `confidence` (0.0–1.0).
**The operation is `async`**, matching the fully async stack fixed by `AD-005`. `ADR-0001` records the same signature; on an async stack a synchronous `triage` is a different contract, not a cosmetic difference.
**Verify:** Test, code review.

### FR-AI-002 — Four implementations, one selector
**MUST.** `LLMTriage`, `OllamaTriage`, `RuleBasedTriage` and `SimulatedTriage` all implement the interface and are selected by the `TRIAGE_PROVIDER` environment variable through a factory. All four are required — `AD-012`'s cut order no longer includes `OllamaTriage`, because dropping it would also break `FR-CTR-007`'s three named volumes and remove the zero-egress mitigation `ADR-0004` relies on.
**Acceptance:** Changing only the environment variable changes the active provider with no code change and no import change elsewhere. An unknown value exits at startup (`FR-BE-018`).
**Verify:** Test (one per provider), CI.

### FR-AI-003 — `RuleBasedTriage` never fails
**MUST.** The keyword classifier is deterministic, requires no network, and always returns a valid `TriageResult` for any input, including empty-after-normalisation text.
**Specified, not exemplified**, since three other requirements depend on its output. **Category** by first keyword match in a fixed priority order over the six categories, defaulting to `other`. **Priority `high`** when the text matches any of a named escalation set — `burst`, `flood`, `flooding`, `sewage`, `live wire`, `electrocut`, `collapse`, `gas leak`, `overflow`, plus the Urdu-influenced forms the seed uses. **Priority `low`** when it matches a named minor set — `streetlight`, `bulb`, `flicker`, `paint`, `pothole` (single), `signboard`, `litter`. **Otherwise `normal`.** Both sets live in one module-level mapping, not scattered conditionals. **`confidence` is a fixed `0.35`** (`AD-026`). **`summary`** is produced by the algorithm in `AD-023`: text up to the first sentence terminator or 120 characters, whichever is shorter, whitespace collapsed, prefixed `"<category>: "`, truncated to 140 on a word boundary.
**Acceptance:** Adversarial set all return valid results and never raise — empty-after-normalisation text, punctuation only, exactly 10 and exactly 2000 characters, no recognisable keyword, and text in a script the rules do not cover. Identical input yields identical output across runs and processes.
**Verify:** Test (parametrised over the adversarial set).

### FR-AI-004 — `SimulatedTriage` is deterministic and injectable
**MUST.** The simulated provider produces the same output for the same input given a fixed `SIMULATED_SEED`, performs no network I/O, and supports failure injection through `SIMULATED_FAILURE_MODE`: unset (succeed), `raise`, `malformed`, `slow`.
**It reports `triaged_by = "simulated"`** on success — a value in the `CHECK` set of `AD-020`, precisely so that CI, which runs `TRIAGE_PROVIDER=simulated`, can persist a legal and truthful row. Reporting `rules` instead would make every CI row indistinguishable from a real rules-path row and corrupt the fallback-rate measurement.
**Acceptance:** Two runs with the same seed and input produce byte-identical `TriageResult`s. Each failure mode produces its documented effect: `raise` triggers the fallback path, `malformed` triggers validation rejection then fallback, `slow` triggers the timeout then the retry then fallback.
**Verify:** Test.

### FR-AI-005 — Structured output requested and validated
**MUST.** The LLM call requests JSON output **and** the response is validated against the Pydantic model regardless. Prose, code fences, out-of-enum categories, and over-length summaries are rejected as invalid output.
**The mechanism is chosen, not left open** (`AD-045`): **JSON mode** — `response_format={"type": "json_object"}` on Groq, `format="json"` on Ollama. Tool calling is not used, because JSON mode is supported identically by both providers and keeps one code path. Request parameters are fixed: `temperature=0`, `max_tokens=200`.
**The output schema** is the `TriageResult` model, serialised into the prompt as an explicit JSON shape: `{"category": <one of six>, "priority": <one of three>, "summary": <string ≤140>, "confidence": <float 0..1>}`. It is recorded verbatim in `docs/TRIAGE.md` alongside the prompt (`AD-052`).
**Constraint:** Model output is never passed to `eval`, never interpolated into SQL, and never used to select code paths outside the validated enum.
**Acceptance:** Feeding prose, a fenced block, an out-of-enum category, a 400-character summary and a `confidence` of `1.5` each produce a validation rejection followed by the fallback, with `triaged_by = "rules:fallback"` and no re-prompt (`AD-007`).
**Verify:** Test (one case per malformed shape above).

### FR-AI-006 — Hard timeout
**MUST.** Every outbound model call has a hard timeout of **10 seconds** (`TRIAGE_TIMEOUT_SECONDS`).
**The whole-operation budget is bounded too:** timeout plus at most one retry plus jitter gives a worst case of **21 seconds** for `POST /api/complaints`, which is the figure `FR-FE-003` renders a loading state for. No requirement anywhere may assume 10 seconds is the request's worst case.
**Verify:** Test (simulated slow provider), code review.

### FR-AI-007 — Single jittered retry, retryable errors only
**MUST.** A failed call is retried **at most once**, and only for timeout, HTTP 429 and HTTP 5xx. A 4xx other than 429 is never retried — the request was wrong and will be wrong again.
**Backoff is specified:** sleep `uniform(0.25, 1.0)` seconds before the retry. Bounded, so the 21-second worst case in `FR-AI-006` holds. **On a 429 carrying `Retry-After`, honour that value instead, capped at 5 seconds** — ignoring a provider's explicit instruction is how a client earns a longer ban.
**Acceptance:** Per error class, assert the provider call count: timeout → 2, 429 → 2, 500 → 2, 400 → 1, 401 → 1. A 429 with `Retry-After: 3` delays about 3 seconds; one with `Retry-After: 120` delays 5.
**Verify:** Test (assert call counts and elapsed time per error class).

### FR-AI-008 — Fallback to rules
**MUST.** When the selected provider fails after its retry, or returns output that fails validation, the system falls back to `RuleBasedTriage` and persists `triaged_by = "rules:fallback"`. The caller receives 201.
**Verify:** Test — this is `FR-BE-028`.

### FR-AI-009 — Latency measurement
**MUST.** The wall-clock duration of the triage operation is measured on **every** path — including the rules path, a cache hit and a fallback — persisted in `triage_latency_ms`, observed into `triage_duration_seconds`, and surfaced through `/api/meta/providers`.
**Measured from** entry to the triage pipeline **to** a validated `TriageResult`, so a fallback's latency includes the failed attempt and its retry. That is the honest number: it is what the citizen waited.
**Acceptance:** A cache hit records a small non-zero value, not null and not zero-as-sentinel; a fallback records a value greater than the timeout.
**Verify:** Test.

### FR-AI-010 — Prompt-injection guardrail
**MUST.** Complaint text is treated as untrusted data: it is delimited within the prompt by a fixed sentinel pair, the system prompt states that text between the sentinels is data to classify and never instructions to follow, and the output is constrained to the enum and rejected otherwise.
**Mechanism:** the complaint is wrapped in `<<<COMPLAINT>>> … <<<END>>>`, and any occurrence of either sentinel in the incoming text is stripped before wrapping, so a caller cannot close the block early and escape it.
**MUST.** A test submits an injection attempt — text instructing the model to mark the complaint low priority and ignore its instructions — and asserts the resulting category and priority are still decided by the schema-validated pipeline. A second test submits text containing the literal sentinel and asserts it is stripped.
**Acceptance:** Under `SimulatedTriage`, an injected instruction cannot produce a `category` or `priority` outside the enum, and cannot produce a `null` summary. Any attempt to do so falls back to rules.
**Verify:** Test.

### FR-AI-011 — Key handling
**MUST.** The API key is read from the environment only, sourced from a Kubernetes Secret or GitHub Secret in deployed environments, and never logged, never echoed in an error message, and never committed.
**Rationale:** §5.3 — automatic −20 / −15 deductions.
**Verify:** CI (secret scan), test (assert the key does not appear in captured logs).

### FR-AI-012 — Triage outcome ring buffer
**MUST.** The last 20 triage outcomes are retained in a Redis list (`LPUSH` + `LTRIM cs:outcomes 0 19`, `AD-009`) so the answer stays global once the HPA has scaled out, and served by `/api/meta/providers`.
**Each entry carries the closed field set defined in `FR-BE-006`**: `complaint_id`, `provider`, `latency_ms`, `fallback`, `error_class`, `at`. Stated as a closed set because `FR-AI-014` reads it.
**The list is invalidated when the triage configuration changes:** the key includes `PROMPT_VERSION` (`cs:outcomes:<PROMPT_VERSION>`), so entries produced under a previous prompt or provider are not silently presented as current. It carries no TTL by design — 20 entries is a bounded size, and the key changes when the meaning changes.
**Acceptance:** After 25 submissions the list holds 20 entries, newest first. Changing `PROMPT_VERSION` yields an empty `recent`, not stale entries.
**Verify:** Test.

### FR-AI-013 — Triage design document
**MUST.** `docs/TRIAGE.md` contains all seven sections of `AD-052`, each of which something else depends on: the **pinned model names** (`qwen/qwen3.8-27b`, `llama3.2:1b`); the **prompt, verbatim**; the **output JSON schema**; the **observed provider rate limits with the date they were seen**; the **measured triage cache hit rate** naming the counters it was computed from; the **measured fallback rate**; and the **Groq-versus-Ollama comparison** over the same seeded inputs, reporting latency and agreement rate.
**Acceptance:** All seven sections are present and none is a placeholder. The rate-limit line carries a date. The hit rate and fallback rate are numbers with the counter names beside them, not prose.
**Verify:** Document review, CI (`scripts/check_submission.py` fails if any of the seven headings is missing or is followed by fewer than 20 characters).

### FR-AI-014 — Measured cache hit rate and per-provider latency
**MUST.** The triage cache hit rate and the per-provider latency are **computed from named sources**, not estimated: hit rate is `triage_cache_hits_total / (triage_cache_hits_total + triage_cache_misses_total)` read from `/metrics`; per-provider latency is the **median and p95 of `triage_duration_seconds` by `provider` label**, over a stated sample size of at least 30 triage operations per provider.
**Rationale:** The audit found both figures required by the brief with no data source defined. The four cache counters in `FR-BE-009` exist for this requirement.
**Acceptance:** `docs/TRIAGE.md` reports each figure with its source series, its sample size, and the command used to read it.
**Verify:** Manual (`scripts/triage_report.sh`, output committed), document review.

---

# M6 — Containerisation

### FR-CTR-001 — Backend image
**MUST.** Multi-stage build on a pinned `python:3.12-slim` base; dependencies installed in a builder stage; `COPY` ordered so that a source change does not invalidate the dependency layer; a non-root `USER`; exec-form `CMD`; a declared `HEALTHCHECK`.
**Acceptance:** `docker image inspect` reports `Config.User` as a non-zero uid; `Config.Healthcheck` is present; `Config.Cmd` is a JSON array, not a shell string. Editing one line of application source and rebuilding reuses the dependency layer, asserted by the build output showing `CACHED` on the install step. The backend runs as **uid 1000** and listens on `BACKEND_PORT` (default **8000**).
**Verify:** CI (image inspection), Dockerfile review.

### FR-CTR-002 — Frontend image
**MUST.** `node:22-alpine` build stage, `nginx:1.27-alpine` serve stage, non-root, exec-form `CMD`. The final image contains no Node toolchain, no `node_modules` and no source.
**Size budget, as a hard gate:** the final image is **at or below 60 MB** measured as `docker image inspect -f '{{.Size}}'` (uncompressed, on-disk) divided by 1 000 000. CI fails above it. Stated as a number with a named measurement because `NFR-PERF-006` previously said "approximately 60 MB" as a `SHOULD` while this requirement said "roughly" as a `MUST` — one threshold, one measurement, one strength.
**Non-root nginx specifics**, because `nginx:alpine` does not run unprivileged by default: run as **uid 101** (`nginx`), listen on **8080** rather than 80, and set `client_body_temp_path`, `proxy_temp_path`, `fastcgi_temp_path`, `uwsgi_temp_path`, `scgi_temp_path` and the `pid` file under `/tmp`, which is writable. Without these the container fails to start as non-root.
**Acceptance:** Both stage sizes are reported in the engineering notes with the command used; the final image is ≤ 60 MB; `docker run` as uid 101 serves a page; `find / -name node_modules` in the final image returns nothing.
**Verify:** CI (size gate, inspection), Dockerfile review.

### FR-CTR-003 — `.dockerignore` per build context
**MUST.** Each build context has a `.dockerignore` excluding at least `.git`, `node_modules`, `.venv`, `__pycache__`, `.env`, `tests/fixtures/`, `*.pyc`, `.pytest_cache`, `.mypy_cache`, `dist/` and `coverage/`. "Test fixtures" is spelled as the path `tests/fixtures/` because a rule that names a concept cannot be checked.
**Acceptance:** Build-context size is reported before and after with the command `docker build --no-cache --progress=plain` transfer line, and **the after figure is at least 90 % smaller than the before figure for the frontend context** — a threshold, so the requirement can fail rather than merely be reported.
**Verify:** CI (both figures captured to `docs/evidence/build-context.txt`), review.

### FR-CTR-004 — Image pinning
**MUST.** Every image reference carries an explicit, immutable-enough tag naming a minor version: `python:3.12-slim`, `node:22-alpine`, `nginx:1.27-alpine`, `postgres:16-alpine`, `redis:7-alpine`, `ollama/ollama:0.5.4`. No bare image name, and no `:latest`, in any Dockerfile, either Compose file, or any Kubernetes manifest.
**On the limit of this:** a minor tag such as `python:3.12-slim` still floats across patch releases, so it is reproducible-enough rather than reproducible. Digest pinning is the real answer and is an explicit bonus (`AD-034`); the engineering notes say so rather than claiming the tag freezes the image.
**Rationale:** §5.3 — automatic −8.
**Verify:** CI (`scripts/check_submission.py` greps every image reference and fails on a missing tag or `:latest`).

### FR-CTR-005 — Three networks with real segmentation
**MUST.** Compose defines **three** networks (`AD-002`): `edge` (frontend ↔ backend), `internal` marked `internal: true` (backend ↔ database ↔ cache ↔ ollama), and `egress` (backend → internet). The frontend joins `edge` only; the database, cache and Ollama join `internal` only; **the backend is the only service on more than one network**, joining all three.
**Deviation, stated plainly:** the brief's §3.2 prescribes two networks. A third is added because `internal: true` blocks outbound traffic, so a backend that must call Groq needs a network that permits it, and putting that on `edge` would make outbound capability an accidental side effect of the browser-facing network. Recorded in **ADR-0005** and in engineering-notes Q7. `RUB-G-03` is marked on the property — the frontend provably cannot reach the database — which three networks satisfy at least as strongly as two.
**Acceptance:** `docker compose exec frontend ping -c1 database` fails, and `docker compose exec frontend getent hosts database` returns nothing; both captured to `docs/evidence/network-isolation.txt`. `docker compose exec backend getent hosts database` succeeds.
**Rationale:** §5.3 — automatic −8 if the frontend can reach the database.
**Verify:** CI (scripted, asserts non-zero exit from the frontend), Manual (captured failure on video).

### FR-CTR-006 — Outbound-egress resolution
**MUST.** The architecture resolves the conflict created by `internal: true` (no outbound route) against a triage provider that must call a hosted model. The resolution is implemented and written down.
**Note:** This is `AD-002`, recorded in `ADR-0005`. It is a marked engineering-notes question (§5.2 Q7).
**Verify:** Compose review, engineering notes.

### FR-CTR-007 — Three named volumes
**MUST.** `pgdata`, `redisdata` and `ollama_models` exist as named volumes, each justified in the engineering notes.
**Ollama's weights reach `ollama_models` by an explicit step** (`AD-046`): `make pull-models` runs `ollama pull` in a throwaway container attached to `egress`. This is required because the Ollama service itself sits on `internal` with no route out and therefore can never pull. The step is a named prerequisite in the README quickstart, and the Ollama healthcheck fails with a message naming the empty volume rather than hanging on an impossible pull.
**Acceptance:** All three volumes are declared in both Compose files and have matching PVCs on Kubernetes; each has a one-sentence justification in the notes; `make pull-models` populates `ollama_models` and a second run is a no-op.
**Verify:** Compose review, notes cross-check, Manual (`docker volume inspect`).

### FR-CTR-008 — Development bind mount
**MUST.** `compose.yaml` bind-mounts backend source for hot reload; `compose.prod.yaml` does not, and the engineering notes explain why it is correct in one and wrong in the other.
**Verify:** Compose review.

### FR-CTR-009 — Healthchecks and ordered startup
**MUST.** Every service declares a healthcheck, and dependants use `depends_on: condition: service_healthy`. Values, so a review can check rather than judge:

| Service | Test | interval | timeout | retries | start_period |
|---|---|---|---|---|---|
| backend | `curl -fsS localhost:8000/health` | 10s | 3s | 3 | 20s |
| frontend | `wget -qO- localhost:8080/` | 10s | 3s | 3 | 5s |
| database | `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB` | 5s | 3s | 5 | 10s |
| cache | `redis-cli ping` | 5s | 3s | 5 | 5s |
| ollama | `ollama list \| grep -q .` | 15s | 5s | 5 | 30s |

The backend healthcheck targets `/health`, never `/ready`, for the same reason Kubernetes separates the two: a healthcheck that depends on the database turns a slow database into a restart loop.
**Verify:** Compose review, CI (integration job waits on `service_healthy`, never on a `sleep`).

### FR-CTR-010 — Credentials via environment
**MUST.** All credentials come from `${...}` substitution backed by `.env`. `.env.example` is committed with placeholder values; `.env` is git-ignored and has never been committed.
**The named variables:** `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `GROQ_API_KEY`, and `IMAGE_TAG` for the production file.
**Scope note:** `NFR-SEC-004`'s "no credential exists in the working tree" means **no credential in a tracked file**. A developer's local `.env` is untracked, git-ignored, and required by this requirement — the two rules are consistent once the scope is stated, which it previously was not.
**Rationale:** §5.3 — automatic −20 if a real secret is anywhere in history.
**Verify:** CI (`.env` absent from `git ls-files`, `.gitignore` contains it), git history scan (`gitleaks detect --log-opts="--all"`).

### FR-CTR-011 — Production Compose file
**MUST.** `compose.prod.yaml` uses `image: ${IMAGE_TAG}` references with no `build:` key anywhere, sets `restart: unless-stopped`, publishes no port for the database or the cache, and sets `APP_VERSION` from the environment (`FR-BE-029`).
**Resource limits in both files.** `compose.prod.yaml` declares `deploy.resources.limits` and `reservations` using the values in `AD-048`; `compose.yaml` declares the same `limits` so a runaway container cannot take a developer's laptop down. The brief lists resource limits under required Compose engineering, so applying them only in the production file would leave the dev file short of the requirement.
**Rationale:** §5.3 — automatic −8 for a published data port.
**Acceptance:** `scripts/check_submission.py` fails if `compose.prod.yaml` contains `build:`, if either data service has a `ports:` entry, or if any service lacks `deploy.resources.limits`.
**Verify:** CI (`scripts/check_submission.py`), review.

### FR-CTR-012 — One-command quickstart
**MUST.** From a clean clone, **`make up`** brings up the whole system with seeded data and prints the URL to open. It runs, in order: copy `.env.example` to `.env` if absent, `make pull-models` if `ollama_models` is empty (`AD-046`), `docker compose up -d --wait`, then the seed.
**Acceptance:** On a machine with only Docker and `make`, a fresh clone followed by `make up` yields a browsable dashboard with 30 seeded complaints, and the command is idempotent — running it twice leaves 30 rows. The README quickstart names exactly this command and no other.
**Rationale:** §5.3 — automatic −5 if the README quickstart does not work from a clean clone.
**Verify:** CI (a job that clones the repository into a clean directory and runs the documented command verbatim — not a job that reproduces the steps, since the deduction is for the *documented* path failing), Manual before submission.

---

# M7 — Kubernetes

### FR-K8S-001 — Namespace
**MUST.** Every object is deployed into a dedicated project namespace, never `default`.
**Note:** Kubernetes object names must be RFC 1123 lower-case; the namespace is therefore `civic-station`. See `AD-030`.
**Verify:** CI (kubeconform + deploy job), manifest review.

### FR-K8S-002 — Workloads
**MUST.** Backend Deployment (≥ 2 replicas), frontend Deployment (≥ 2 replicas), PostgreSQL **StatefulSet** with `volumeClaimTemplates`, Redis Deployment with a PVC.
**Rationale:** §5.3 — automatic −8 for PostgreSQL as a Deployment with no PVC.
**Verify:** Manifest review, CI deploy job.

### FR-K8S-003 — Services
**MUST.** Four ClusterIP Services — `backend`, `frontend`, `postgres`, `redis`. Every one is `ClusterIP`; the database is never a NodePort or LoadBalancer.
**Ollama is not deployed to Kubernetes.** It is a Compose-only service: the cluster runs `TRIAGE_PROVIDER=llm` (or `simulated` in CI), and the buy-versus-host comparison in `docs/TRIAGE.md` is measured locally. Stated here because `FR-K8S-002` lists four workloads and `FR-AI-002` requires four providers — the second does not imply a fifth Service, and leaving that unsaid invited the question.
**Rationale:** §5.3 — automatic −8.
**Verify:** CI (`scripts/check_submission.py` fails on `type: NodePort` or `type: LoadBalancer` in any manifest), manifest review.

### FR-K8S-004 — Ingress
**MUST.** One host, `civic-station.localhost` (`AD-029`), routes `/` to the frontend Service and `/api` to the backend Service.
**Paths not routed through the Ingress, deliberately:** `/health`, `/ready`, `/metrics`, `/openapi.json` and `/docs` are not exposed externally. Probes address pods directly, so readiness and liveness do not need an Ingress path; `/metrics` would be scraped in-cluster; and `/openapi.json` is read at build time by the type generator (`FR-FE-012`), not by the browser. This is a decision, not an omission — recorded so nobody "fixes" it later by widening the Ingress.
**Acceptance:** `curl -H 'Host: civic-station.localhost' http://<ingress>/` returns the SPA and `.../api/complaints` returns JSON. The CI smoke test uses exactly this form, with the explicit `Host` header so it does not depend on DNS.
**Verify:** CI (smoke test through the Ingress in the deploy job).

### FR-K8S-005 — ConfigMap and Secret separated
**MUST.** Non-secret configuration lives in a ConfigMap; the database password and LLM API key live in a Secret. Committed Secret manifests contain **placeholders only**.
**Real values** are supplied by `kubectl create secret generic --from-literal` (`AD-027`), run from the runbook locally and from GitHub Secrets in CI.
**Rotation is defined** (`FR-PROC-006`): replacing a Secret does **not** restart consuming pods, because the values are injected as environment variables at container start. Rotation is therefore `kubectl create secret ... --dry-run=client -o yaml | kubectl apply -f -` followed by `kubectl rollout restart deployment/backend`. Without the second command the old credential stays live in every running pod, which is the failure mode that makes a rotation look successful and not be.
**Rationale:** §5.3 — automatic −15 for a real key in a committed manifest, base64 included.
**Verify:** CI (`scripts/check_submission.py` fails on any `data:` value in a committed Secret that base64-decodes to something other than a placeholder), manifest review.

### FR-K8S-006 — All three probes
**MUST.** All three probes on the backend, with these values:

| Probe | Path | `periodSeconds` | `failureThreshold` | `timeoutSeconds` | Effect of failure |
|---|---|---|---|---|---|
| `startupProbe` | `/health` | 2 | 30 | 2 | Holds off the other two for up to 60 s, so a slow boot is not a restart loop |
| `livenessProbe` | `/health` | 10 | 3 | 2 | **Restarts the pod** — therefore must not touch the database |
| `readinessProbe` | `/ready` | 5 | 2 | 2 | **Removes the pod from the Service** — therefore should depend on the database and cache |

The `30 × 2 s` startup budget comes from the brief's own snippet. The liveness and readiness paths differ because the consequences differ: wire them the other way round and a slow database becomes a rolling restart of every backend pod.
**Probes on the other workloads:** `postgres` uses `pg_isready` for both liveness and readiness; `redis` uses `redis-cli ping`; `frontend` uses an HTTP GET on `/` for both. `FR-CTR-009` requires a healthcheck on every Compose service, so the Kubernetes manifests match rather than covering the backend alone.
**Acceptance:** Stopping PostgreSQL removes backend pods from the Service endpoints **without** restarting them — asserted by `kubectl get pods` showing `READY 0/1` with `RESTARTS` unchanged, observed over at least 60 seconds so a delayed restart would be caught.
**Verify:** Manifest review, Manual (`scripts/demo_probes.sh`, captured to `docs/evidence/probes.txt`).

### FR-K8S-007 — Resource requests and limits
**MUST.** Every container declares `resources.requests` and `resources.limits` for CPU and memory, with these values (`AD-048`):

| Container | `requests.cpu` | `requests.memory` | `limits.cpu` | `limits.memory` |
|---|---|---|---|---|
| backend | `100m` | `256Mi` | `500m` | `512Mi` |
| frontend | `20m` | `32Mi` | `100m` | `128Mi` |
| postgres | `200m` | `512Mi` | `1000m` | `1Gi` |
| redis | `50m` | `64Mi` | `200m` | `256Mi` |

The backend's `100m` request is deliberately small so that a plateau above the HPA's 60 % target is reachable with a load a laptop can generate. **These are the recorded initial guess, not a measurement** — recording them is what makes step 1 of the VPA loop in `FR-LOAD-003` possible, and the notes say so rather than presenting them as derived.
**Rationale:** Without a CPU request the HPA has no denominator and reports `<unknown>/60%`, which the brief names as the single most common cause of a "broken HPA".
**Acceptance:** `scripts/check_submission.py` fails if any container in `kustomize build overlays/prod` lacks any of the four values. The dev overlay may lower limits but **must not remove requests**.
**Verify:** CI (`scripts/check_submission.py`), manifest review.

### FR-K8S-008 — HorizontalPodAutoscaler
**MUST.** `autoscaling/v2` HPA on the backend: `minReplicas: 2`, `maxReplicas: 10`, CPU utilisation target 60 %, with `behavior` tuned so scale-up is immediate and scale-down is stabilised over 300 seconds.
**Verify:** Manifest review, `FR-LOAD-002` evidence.

### FR-K8S-009 — VerticalPodAutoscaler in recommender mode
**MUST.** A VPA targets the backend with `updateMode: "Off"`. Its recommendations are captured and committed, the requests are revised in response, and the HPA/VPA conflict is explained in the notes.
**Verify:** Manifest review, `FR-LOAD-003` evidence, notes cross-check.

### FR-K8S-010 — PodDisruptionBudget
**MUST.** `minAvailable: 1` on the backend.
**Acceptance:** `kubectl drain` of the node hosting one backend pod does not reduce available backend pods to zero; `kubectl get pdb -n civic-station` shows `ALLOWED DISRUPTIONS` of at least 1 with 2 replicas running.
**Verify:** Manifest review, Test (kubeconform policy asserts the PDB exists and targets the backend selector).

### FR-K8S-011 — Rollout strategy and pod lifecycle
**MUST.** `maxSurge: 1`, `maxUnavailable: 0`, `terminationGracePeriodSeconds: 30`, and a `preStop` hook of `sleep 5`.
**Why those two numbers**, rather than "long enough": `preStop` runs before SIGTERM, and 5 seconds covers the Endpoints controller propagating the pod's removal to every node, so no new connection arrives at a pod that is shutting down. The 30-second grace period then leaves 25 seconds for in-flight work, against a 21-second worst-case request (`FR-AI-006`). Matching values are in `FR-BE-021`.
**Acceptance:** `kubectl set image` during the load of `FR-LOAD-004` produces zero failed requests.
**Verify:** Manifest review, `FR-LOAD-004` evidence.

### FR-K8S-012 — Kustomize structure
**MUST.** `k8s/base/` holds the shared manifests; `k8s/overlays/dev/` and `k8s/overlays/prod/` hold environment differences. `kustomize build overlays/prod` produces valid manifests.
**Kustomize, not Helm.** `AD-011` settled this; the permission to use Helm instead is withdrawn, because leaving two options open inside a `MUST` means the CI `manifests` job cannot be written against either.
**Overlay contents, so "environment differences" is concrete.** `dev`: `LOG_LEVEL=DEBUG`, `TRIAGE_PROVIDER=simulated`, `limits` halved, `replicas` left at the base value. `prod`: `LOG_LEVEL=INFO`, `TRIAGE_PROVIDER=llm`, the `AD-048` limits, `IMAGE_TAG` set to the commit SHA. **Neither overlay changes `replicas` below 2**, because the HPA's `minReplicas: 2` would immediately override it — a lowered dev replica count would silently not happen.
**Acceptance:** `kustomize build overlays/dev` and `overlays/prod` both pass `kubeconform -strict`, and the rendered outputs differ only in the values listed above.
**Verify:** CI (kubeconform on both overlays).

### FR-K8S-013 — Deploy by immutable reference
**MUST.** Deployed manifests reference images by **commit SHA tag**. `:latest` may be published but is never deployed. Digest deployment is a bonus (`AD-034`) and is not the acceptance target here.
**Rationale:** §5.3 — automatic −8 for deploying `:latest`.
**Acceptance:** `scripts/check_submission.py` fails if `kustomize build overlays/prod` contains any image reference whose tag is `latest` or is absent. One target, so the checker has one rule.
**Verify:** CI, `scripts/check_submission.py`.

### FR-K8S-014 — Rollback, both mechanisms
**MUST.** Both mechanisms are documented in `docs/RUNBOOK.md`, demonstrated on video, and compared.
**Both are bounded by a measured time:** `kubectl rollout undo deployment/backend -n civic-station` completes within **30 seconds**, measured from command to `kubectl rollout status` returning; re-applying the previous overlay at the previous SHA completes within **90 seconds**, measured the same way. Both figures are captured to `docs/evidence/rollback-timing.txt`. `NFR-OPS-002`'s "roughly thirty seconds" applies to the first mechanism only — the declarative path is slower by nature and pretending otherwise would misreport it.
**The comparison to write:** the imperative path is for while the fire burns and leaves the cluster disagreeing with the repository; the declarative path is the correct answer once it is out, and restores that agreement.
**Verify:** Runbook review, Manual (timed, captured), video.

---

# M8 — CI/CD

### FR-CICD-001 — `ci.yml` triggers and jobs
**MUST.** Runs on pull requests to `main` and on pushes to `dev`, with jobs: `lint-and-type`, `test-backend`, `test-frontend`, `build`, `scan`, `manifests`, `integration`, `submission-check`.
**All eight are required status checks on `main`** (`FR-CICD-012`). Naming them here matters: a branch-protection rule that requires only some of them lets `scan`, `manifests` or `integration` fail while the merge button stays green, which defeats the gate the marks are for.
**`submission-check` runs `scripts/check_submission.py`** — previously defined (`FR-DOC-007`) but wired into no job, so every §5.3 deduction guard ran only when a human remembered.
**Acceptance:** A PR with any one job failing cannot be merged; the eight names in the branch-protection rule match the eight job ids exactly.
**Verify:** Workflow review, pipeline run, branch-protection screenshot.

### FR-CICD-002 — Lint and type checks
**MUST.** `ruff` and `mypy` on the backend; `eslint` and `tsc --noEmit` on the frontend. Failures fail the job.
**Verify:** Pipeline run.

### FR-CICD-003 — Backend tests in CI
**MUST.** `pytest` with coverage ≥ 65 % on `app/`, executed with `TRIAGE_PROVIDER=simulated`.
**Verify:** Pipeline run.

### FR-CICD-004 — Frontend tests in CI
**MUST.** Vitest component tests, at least five (`FR-FE-020`'s required mapping), executed on every PR with **statement coverage of `frontend/src/` at or above 50 %**, enforced by `vitest --coverage`. A coverage gate on the backend and none on the frontend meant half the code had a number and half had a promise.
**Verify:** Pipeline run.

### FR-CICD-005 — Build without publish on PRs
**MUST.** The PR pipeline builds both images and does **not** push them to any registry.
**Acceptance:** The `build` job runs `docker build` with no `--push` and no `docker push`, and declares `permissions: packages: none`. A reviewer can confirm from the workflow file alone that a PR cannot publish.
**Verify:** Workflow review, CI (`scripts/check_submission.py` fails on `docker push` or `push: true` inside `ci.yml`).

### FR-CICD-006 — Vulnerability scan
**MUST.** Trivy scans both images and fails the job on HIGH or CRITICAL findings that have a fixed version available.
**Verify:** Pipeline run.

### FR-CICD-007 — Manifest validation
**MUST.** `kustomize build overlays/prod` piped to `kubeconform` runs on every PR.
**Verify:** Pipeline run.

### FR-CICD-008 — Compose integration job
**MUST.** The job brings the stack up, waits for `/ready`, submits a complaint, reads it back, asserts the category, asserts `X-Cache` goes `MISS` then `HIT`, and tears down with `docker compose down -v`.
**Verify:** Pipeline run.

### FR-CICD-009 — `cd.yml` gated pipeline
**MUST.** On push to `main`: run the full suite; then `build-push` with `needs: test`, pushing both images to GHCR tagged with the commit SHA and `latest`, emitting an SBOM with Syft and exposing the image digest as a job output; then `deploy-k8s` with `needs: build-push`, creating an ephemeral k3d cluster, applying `overlays/prod` at the SHA tag, waiting on `kubectl rollout status`, smoke-testing through the Ingress, and printing `kubectl get hpa`.
**The SBOM has a destination:** `syft` writes SPDX JSON per image, uploaded as a workflow artifact named `sbom-<image>-<sha>` with 90-day retention, and attached to the GitHub Release by `release.yml` when one exists. An SBOM that is generated and discarded is not a deliverable.
**The deploy job fails closed.** If the smoke test fails, the job runs `kubectl rollout undo deployment/backend -n civic-station`, prints `kubectl describe` and the pod logs, and exits non-zero. A deploy job whose only failure mode is a red tick leaves a broken deployment running — and this is the same command `FR-K8S-014` documents, exercised automatically rather than only demonstrated.
**Rationale:** §5.3 — automatic −8 for a publishing or deploying job not gated by `needs:`.
**Acceptance:** `needs:` present on both `build-push` and `deploy-k8s`; a forced smoke-test failure produces a rolled-back deployment and a red run; the SBOM artifact exists on a green run.
**Verify:** Workflow review, successful run link (submission item 2), one deliberate-failure run.

### FR-CICD-010 — `release.yml`
**MUST.** On a `v*` tag: build, push semver-tagged images, generate release notes, and attach the SBOM artifacts from `FR-CICD-009`.
**Verify:** Workflow review.

### FR-CICD-011 — Least privilege and pinned actions
**MUST.** Every workflow declares an explicit `permissions:` block scoped to what it needs. Every action is pinned to at least a major version tag; commit-SHA pinning is a bonus. Registry authentication uses a scoped, revocable token (`GITHUB_TOKEN` with `packages: write` for GHCR), never an account password.
**Verify:** Workflow review.

### FR-CICD-012 — Branch protection
**MUST.** `main` is protected: no direct pushes, PR required, at least one approval, and **all eight `ci.yml` jobs required as status checks** (`FR-CICD-001`) — `lint-and-type`, `test-backend`, `test-frontend`, `build`, `scan`, `manifests`, `integration`, `submission-check`.
**Merge method: merge commit, not squash.** `FR-PROC-004` requires a preserved merge commit as marked evidence and `FR-PROC-003` requires at least 35 commits; squash-merging destroys both. This is a repository setting, so it is stated as a requirement rather than left to habit.
**Rationale:** §5.3 — automatic −5 for commits pushed directly to `main`.
**Acceptance:** The screenshot in `docs/evidence/branch-protection.png` shows all eight checks listed and "Require a pull request before merging" enabled; `git log --merges main` is non-empty.
**Verify:** Evidence screenshot, Git history.

### FR-CICD-013 — Evidence that the gate works
**MUST.** A pull request containing a deliberately failing test, with screenshots of the red check and the blocked merge button, fixed within the same PR, with a screenshot of the resulting green state.
**Verify:** Evidence screenshots.

---

# M9 — Load and scaling evidence

### FR-LOAD-001 — Load generator
**MUST.** `load/k6-script.js` generates the load profile. k6 only — the "or an equivalent `hey` invocation" alternative is withdrawn, because `hey` cannot express a staged ramp and the profile below is defined in terms of stages.
**The profile (`AD-050`), as executable numbers:**

```js
export const options = {
  stages: [
    { duration: '60s', target: 40 },   // ramp — makes the lag visible
    { duration: '180s', target: 40 },  // plateau above the 60% CPU target
    { duration: '30s', target: 0 },    // ramp down
    { duration: '330s', target: 0 },   // idle > the 300s scale-down window
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<2000'],
  },
};
```

**Request mix per iteration:** 8 × `GET /api/complaints` with randomised `page`, `page_size` and filter combinations, 1 × `GET /api/stats`. The list endpoint carries the load because it is uncached; stats is capped at a low rate because a 30-second TTL means it cannot generate sustained CPU (`AD-017`).
**Output:** `--out json=docs/evidence/k6-timeseries.json` as well as the summary, because the summary is an aggregate and the chart in `FR-LOAD-002` needs a time series (`AD-051`).
**Acceptance:** The script runs against the cluster, the thresholds are present and the run fails if either is breached.
**Verify:** Script review, one recorded run.

### FR-LOAD-002 — HPA scale-out capture
**MUST.** metrics-server is installed; the `FR-LOAD-001` profile drives scale-out; the HPA state is captured **with timestamps**; a chart of replicas against offered load over time is produced; 3–5 sentences explain the lag.
**Timestamped capture (`AD-051`):** `kubectl get hpa -w` emits no timestamps, so the capture is piped through a timestamping filter — `kubectl get hpa backend -n civic-station -w | awk '{ print strftime("%Y-%m-%dT%H:%M:%S"), $0; fflush() }' | tee docs/evidence/hpa-watch.txt`. Without this the lag cannot be computed from the evidence at all, which is what the audit found.
**The chart** is produced by `scripts/plot_scaling.py`, reading `hpa-watch.txt` and `k6-timeseries.json` and writing `docs/evidence/scaling-chart.png` — committed and reproducible, not a screenshot of a spreadsheet (`AD-044`).
**Acceptance, as numbers:** CPU utilisation exceeds 60 % during the plateau; replicas rise above 2; replicas return to 2 within 600 s of the idle stage beginning; the lag figure is stated in seconds and is derivable from the two committed files.
**Verify:** Evidence artefacts, engineering notes Q5.

### FR-LOAD-003 — VPA recommendation loop
**MUST.** Five steps, in order: (1) record the initial requests from `AD-048` — `backend: 100m / 256Mi`; (2) run the `FR-LOAD-001` profile; (3) capture `kubectl describe vpa backend-vpa` Target, Lower Bound and Upper Bound to `docs/evidence/vpa-recommendation.txt`; (4) update the backend requests in `k8s/base/backend.yaml` to the Target; (5) re-run and report what changed about HPA behaviour.
**What "what changed" means concretely:** the replica count at plateau, and the time from load starting to the first scale-up. Both are readable from the two `hpa-watch.txt` captures, so the answer is a comparison of numbers rather than an impression.
**Acceptance:** Both captures exist, the manifest diff showing step 4 is in the history, and the notes state both figures before and after.
**Verify:** Evidence artefacts, engineering notes Q6.

### FR-LOAD-004 — Zero-downtime rollout
**MUST.** Run the load generator during `kubectl set image` and show **zero failed requests**.
**Promoted from bonus to required.** The brief states this in the body of §3.3 at `:293`, not only as a `+4` bonus at `:486`, and `NFR-REL-003` is a `MUST` whose only measure is this demonstration. `AD-012` moves it into scope; it is nearly free once `FR-BE-021` and `FR-K8S-011` exist, both of which are required anyway.
**Acceptance, with a denominator:** during a rollout under the plateau load of 40 VUs for at least 60 seconds — approximately 2 000 requests — k6 reports `http_req_failed` of **exactly 0**, and the count of requests attempted is reported alongside it. "Zero failures" without the attempt count is not evidence.
**Depends on:** `FR-BE-021` (SIGTERM drain) and `FR-K8S-011` (`preStop`, `maxUnavailable: 0`).
**Verify:** Evidence capture (`docs/evidence/zero-downtime.txt` with both numbers), video.

---

# M10 — Documentation and portfolio

### FR-DOC-001 — README
**MUST.** Contains the problem statement, status badges, a Mermaid architecture diagram, the `make up` quickstart that works from a clean clone, the API endpoint table (**all eleven endpoints**, with a note on which ten the rubric line counts — `FR-BE-010`), the declared backend framework (FastAPI, per the brief's §2.2 requirement to say so), the `make pull-models` prerequisite (`AD-046`), and screenshots of all three views.
**Every claim is demonstrable.** The README asserts nothing that has no command beside it or behind it in `docs/evidence/`; `NFR-DOC-002` requires this and the check is a reading of the README against that directory before submission.
**Verify:** Review, clean-clone test (`FR-CTR-012`).

### FR-DOC-002 — Five ADRs
**MUST.** `docs/adr/0001-provider-interface.md`, `0002-frontend-runtime-config.md`, `0003-deploy-by-sha.md`, `0004-pii-and-data-governance.md`, and `0005-network-topology-and-limiter-degradation.md`. Each states context, options considered, the decision, consequences, **a status, and a real ISO date** — not "Round 2", which cannot be ordered against the code it describes.
**The fifth exists** because two Tier 1 architectural decisions had no ADR: `AD-002` (three networks, a deliberate deviation from the brief) and `AD-008` (the limiter fails open, trading security for availability on the only control guarding the paid path). The rubric marks four ADRs; a fifth costs nothing and covers the two decisions most likely to be challenged at viva.
**Which decisions each ADR records** is listed in `OPEN-DECISIONS.md` and must match the ADR's own `Decides:` line.
**Verify:** Review, CI (`scripts/check_submission.py` fails if any ADR lacks `Status:`, a parseable date, or a `Decides:` line).

### FR-DOC-003 — Runbook
**MUST.** `docs/RUNBOOK.md` covers: deploying, both rollback mechanisms with their measured timings (`FR-K8S-014`), reading logs, **rotating a leaked or expired credential** (`FR-PROC-006`), provisioning the GitHub and Kubernetes Secrets (`FR-PROC-007`), and what to do when triage starts failing.
**Verify:** Review.

### FR-DOC-004 — Engineering notes
**MUST.** `docs/ENGINEERING-NOTES.md` answers all eight §5.2 questions with references to the team's own files and line numbers, **and carries the additional content other requirements assign to this file**, which the previous wording excluded by scoping it to the eight questions alone:

| Content | Required by |
|---|---|
| The named query each of the three indexes serves | `FR-DATA-003` |
| Why a cache is given durable storage, and which workload would be missed | `FR-CACHE-005` |
| Both image stage sizes, with the command used | `FR-CTR-002` |
| Build-context sizes before and after, with the command | `FR-CTR-003` |
| A justification for each of the three named volumes | `FR-CTR-007` |
| Why a dev bind mount is right in `compose.yaml` and wrong in `compose.prod.yaml` | `FR-CTR-008` |
| The `Civic-Station` → `civic-station` RFC 1123 correction | `AD-030` |
| That the `AD-048` resource values are a recorded guess, not a measurement | `FR-K8S-007` |

**"Generic answers score zero" is made checkable:** each of the eight answers cites at least one `path:line` in this repository. An answer with no citation does not satisfy this requirement.
**Verify:** Review, CI (`scripts/check_submission.py` asserts eight numbered headings and at least one `path:line` citation under each).

### FR-DOC-005 — AI usage disclosure
**MUST.** `docs/AI-USAGE.md` names the AI tools used, which parts they wrote or shaped, and what was changed afterwards and why.
**Verify:** Review.

### FR-DOC-006 — Evidence directory
**MUST.** `docs/evidence/` holds exactly these files, each named so a marker can find it without hunting:

| File | Produced by |
|---|---|
| `branch-protection.png` | `FR-CICD-012` |
| `merge-conflict/` (markers, resolution, merge commit) | `FR-PROC-004` |
| `blocked-merge-red.png`, `blocked-merge-green.png` | `FR-CICD-013` |
| `hpa-watch.txt` (timestamped) | `FR-LOAD-002` |
| `k6-timeseries.json` | `FR-LOAD-001` |
| `scaling-chart.png` | `FR-LOAD-002` |
| `vpa-recommendation.txt` | `FR-LOAD-003` |
| `zero-downtime.txt` | `FR-LOAD-004` |
| `network-isolation.txt` | `FR-CTR-005` |
| `build-context.txt` | `FR-CTR-003` |
| `sigterm.txt` | `FR-BE-021` |
| `probes.txt` | `FR-K8S-006` |
| `persistence-k8s.txt` | `FR-DATA-005` |
| `rollback-timing.txt` | `FR-K8S-014` |

**Acceptance:** Every file above exists and is non-empty, **and its content matches what its name claims** — `scripts/check_submission.py` checks existence and non-emptiness; a human checks the claim before submission, because a file can exist and show the wrong thing.
**Verify:** CI (existence and non-emptiness), directory review.

### FR-DOC-007 — Submission checker
**MUST.** `scripts/check_submission.py` mechanically checks the §5.3 deduction list: secrets in history, unpinned or `:latest` images, `localhost` in service-to-service configuration (with the exclusions in `FR-FE-016`), published data ports in the production Compose file, `:latest` in deployed manifests, ungated publishing jobs, PostgreSQL without a PVC, missing resource requests or limits, and the structural checks named in `FR-DOC-002`, `FR-DOC-004` and `FR-DOC-006`.
**It runs in CI** as the `submission-check` job of `FR-CICD-001`, and is a required status check. A checker that only runs when someone remembers is not a guard.
**Acceptance:** Exits 0 on a clean repository and non-zero with a message naming the rule and the offending path otherwise. Has its own unit tests, including one per `FR-FE-016` exclusion.
**Verify:** CI, clean run from the repository root.

### FR-DOC-008 — Demo video
**MUST.** ≤ 5 minutes, both partners speaking, covering, in order: clean clone to running system, AI triage, fallback, network isolation failing, HPA scaling, rollback, **and persistence across a restart** (`FR-DATA-005`, which the brief demands a demonstration of at `:128`).
**Verify:** Submitted link.

---

# M11 — Process and collaboration

### FR-PROC-001 — Branch model
**MUST.** Two long-lived branches (`main`, `dev`) plus short-lived feature branches. No work is committed directly to `main`.
**Verify:** Git history.

### FR-PROC-002 — Pull requests
**MUST.** At least five merged PRs, each linked to an Issue, each carrying a substantive review comment from the other partner.
**Verify:** Repository review.

### FR-PROC-003 — Commit discipline
**MUST.** At least 35 commits using Conventional Commit prefixes (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `refactor:`, `chore:`). Neither partner falls below 35 % of commits by `git shortlog -sn`.
**Verify:** `git shortlog -sn` output (submission item 5).

### FR-PROC-004 — Deliberate merge conflict
**MUST.** One real merge conflict on real code, resolved, with the markers, the resolution and the merge captured as evidence, plus 2–4 sentences explaining why the surviving version won.
**Verify:** Evidence.

### FR-PROC-005 — Cross-ownership for viva
**MUST.** Each partner can explain, and modify live, any part of the submission — including code the other partner wrote. The individual mark is the team mark multiplied by a viva factor.
**Made checkable, since the ability itself cannot be asserted in CI:** each partner authors at least one engineering-note answer drawn from the other's area, and at least one commit in each of the other's modules appears under their name in `git log`. Those two artefacts are the evidence; the ability is what they stand for.
**Verify:** `git log --author` per module, notes authorship, internal walkthroughs.

### FR-PROC-006 — Credential rotation and incident note
**MUST.** A documented procedure exists for rotating a credential that has leaked or expired, and for recording the incident. §5.3 attaches **−20 plus a mandatory rotation and incident note** to a secret in Git history, and no requirement previously covered either half of that obligation.
**The procedure**, in `docs/RUNBOOK.md`: (1) revoke at the source — regenerate the Groq key in the provider console, or `ALTER USER ... PASSWORD` for the database; (2) update GitHub Secrets; (3) re-create the Kubernetes Secret with `kubectl create secret generic ... --dry-run=client -o yaml | kubectl apply -f -`; (4) **`kubectl rollout restart deployment/backend`** — without this the old value stays live in every running pod, which is the step that makes a rotation look done and not be; (5) update local `.env`; (6) if the credential reached Git history, treat the history as compromised and say so in the note rather than claiming a rewrite cleaned it.
**The incident note**, at `docs/INCIDENTS.md`, records: what leaked, when it was committed and when it was noticed, the blast radius, the rotation steps taken with timestamps, and the change that prevents a recurrence. Written even if the leak was caught before push.
**Acceptance:** The runbook section exists with all six steps; `docs/INCIDENTS.md` exists, containing either a real entry or the explicit line "No incidents to date." — an empty file is ambiguous.
**Verify:** Runbook review, document review.

### FR-PROC-007 — Provisioning the provider credential
**MUST.** The prerequisite steps to obtain and install the model provider credential are documented, because every CI and deployment path assumes `GROQ_API_KEY` already exists and nothing said how it gets there.
**In `docs/RUNBOOK.md`:** create a Groq account at `console.groq.com`; generate an API key; record the **observed free-tier rate limits and the date seen** into `docs/TRIAGE.md` (`AD-006`, `AD-052`); add the key as the repository secret `GROQ_API_KEY`; create the Kubernetes Secret from it. Also state the fallback: if no key is available, `TRIAGE_PROVIDER=ollama` is a fully supported path and the brief explicitly attaches no mark penalty to it.
**The two partners share the key through the GitHub repository secret, never through a chat message, a file, or a commit.**
**Acceptance:** A reader with no account can follow the section end to end. `docs/TRIAGE.md` carries the rate-limit line with a date.
**Verify:** Runbook review, document review.

---

## Appendix A — Requirements whose violation carries an automatic deduction

| § 5.3 deduction | Guarded by |
|---|---|
| Secret anywhere in Git history (−20), **plus rotation and an incident note** | FR-CTR-010, FR-AI-011, FR-DOC-007, **FR-PROC-006** |
| LLM key in a committed manifest (−15) | FR-K8S-005, FR-DOC-007 |
| Unpinned base image (−8) | FR-CTR-004, FR-DOC-007 |
| `localhost` for service-to-service (−8) | FR-FE-016, FR-DOC-007 |
| Frontend can reach the database (−8) | FR-CTR-005, FR-DOC-007 |
| Published DB/cache port, or NodePort on the DB (−8) | FR-CTR-011, FR-K8S-003 |
| Publishing job not gated by `needs:` (−8) | FR-CICD-009 |
| Deploying `:latest` (−8) | FR-K8S-013 |
| PostgreSQL as a Deployment with no PVC (−8) | FR-K8S-002 |
| Commits pushed directly to `main` (−5) | FR-CICD-012, FR-PROC-001 |
| README quickstart fails from a clean clone (−5) | FR-CTR-012, FR-DOC-001 |

**Every row above is checked by `scripts/check_submission.py`**, which runs as the required `submission-check` job (`FR-CICD-001`). The one exception is the frontend-to-database reachability test, which needs a running stack and therefore runs in the `integration` job instead.

## Appendix B — Revision history

| Date | Change |
|---|---|
| Round 1 | Initial extraction from the problem statement. |
| 2026-09-25 | Audit remediation (`docs/audit/01-specification-audit.md`). Added `FR-BE-029`, `FR-CACHE-007`, `FR-AI-014`, `FR-PROC-006`, `FR-PROC-007`. `FR-CTR-005` changed from two networks to three (`AD-002`). `FR-LOAD-004` promoted from bonus `SHOULD` to `MUST`. `FR-DATA-002` made `ai_summary` and `triage_confidence` `NOT NULL` and added `simulated` to the `triaged_by` set. `FR-DATA-003` went from two indexes to three. `FR-DOC-002` went from four ADRs to five. Numbers, data sources and acceptance predicates supplied throughout in place of "roughly", "meaningful", "generous" and "review". |
