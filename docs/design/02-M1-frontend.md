# 02 — M1 Frontend: design and implementation guide

**Owner:** Dev 1 (`AD-013`)
**Depends on:** `00-conventions.md`, `01-api-contract.md`, `ADR-0002`
**Delivers:** `RUB-B-01`…`RUB-B-05`. No mark total is stated here — the brief's section weights do not sum to its headline figure (`AD-047`), so a total quoted in a design document would be a number nobody can reconcile.
**Stack:** React 18 + Vite + TypeScript, served by `nginx:1.27-alpine`. `react-router`, plain CSS, no data-fetching library, no component library (`AD-036`, `AD-037`, `AD-038`)

---

## 1. What this module is for

Presentation and interaction. Nothing else.

The frontend owns **no business rules**. Triage category, priority, and valid status transitions are decided by the backend and rendered by the frontend. The brief's warning is the design constraint: *the moment your React code contains a list of valid status transitions, you have two sources of truth and one of them will rot.*

The second constraint is `ADR-0002`: the frontend never knows a backend address. It issues relative requests to `/api`, and nginx proxies them. This removes CORS from the browser's view entirely and makes the `localhost`-for-service-to-service deduction structurally impossible on this side.

---

## 2. Architecture

```
frontend/src/
├── api/
│   ├── types.ts        generated from the backend OpenAPI schema — NEVER hand-edited
│   └── client.ts       the ONLY module that issues HTTP
├── components/         ComplaintCard, FilterBar, Pagination, StatusControl,
│                       LoadingState, ErrorBanner, CacheBadge, ErrorBoundary
├── pages/              SubmitPage, DashboardPage, StatsPage
└── App.tsx             router, layout, error boundary
```

**`api/client.ts` is the only module that calls `fetch`.** Components receive data and callbacks. This is what makes `FR-FE-012` checkable and what makes component tests possible without a network.

**`api/types.ts` is generated** from `/openapi.json` (for example with `openapi-typescript`) and committed. Regenerating it after a backend contract change is a task, and `tsc --noEmit` failing afterwards is the *feature* — it is how a breaking contract change is caught in CI rather than in a demo.

### 2.1 The API client

- Base path is the literal string `/api`. There is no configurable base URL anywhere in the bundle (`ADR-0002`).
- Sends `X-Request-ID` on every request (`FR-FE-013`), generated per request, and surfaces it in error states so a reported failure can be found in the logs.
- Parses the single error body shape from `00-conventions.md` §4 into a typed `ApiError` carrying `code`, `message`, `fields` and `requestId`. **Every** non-2xx goes through this one parser — components never inspect a raw response.
- Reads `X-Cache` from the stats response and returns it alongside the body, because the Stats view must display it (`FR-FE-011`).

### 2.2 Submit page (M1.1)

Fields: complaint text (textarea), location, optional contact.

**Validation mirrors the server, never replaces it** (`BR-VAL-001`). Text 10–2000, location 3–200, checked on blur and on submit, with an inline message naming the field and the rule. The same input sent directly to the API still returns 400 — the client check is a courtesy, the server check is the guarantee, the database constraint is the promise.

**Honest loading state** (`FR-FE-003`). Triage is a synchronous call to a third party and can take seconds. While in flight: the submit control is disabled, a progress indicator is visible, and the copy says what is actually happening ("classifying your report…"). A form that looks idle invites a double submission, and a double submission costs an inference.

**Result rendering** (`FR-FE-004`). On 201, render `category`, `priority`, `ai_summary` and `triaged_by` from the response. `triaged_by` is shown in human form — "classified by: Groq", "classified by: keyword rules (fallback)" — because showing the provider is part of what makes this system's engineering visible. The mapping from `triaged_by` value to label is presentation, which is allowed; deciding the value is not.

**Error states** (`FR-FE-005`), three visibly different outcomes:
- 400 → field-level messages mapped back onto the offending inputs from `error.fields`.
- 429 → a distinct "you are submitting too quickly" state that uses `Retry-After` to say how long to wait.
- anything else → a non-silent error banner showing the request id.

### 2.3 Dashboard page (M1.2)

Server-side list, filters and pagination — all three as query parameters (`FR-FE-006`, `FR-FE-007`). Fetching all rows and filtering in the browser is a defect, not an optimisation.

- Filters for category, priority, status, individually and combined. Changing a filter resets to page 1.
- Pagination renders `total` from the server; page size is fixed at a value ≤ 100.
- Filter option values come from the generated enum types, not from a hand-written array (`BR-VOCAB-005`).

**Status transitions** (`FR-FE-008`, `FR-FE-009`) — the part most likely to be got wrong:

- The status control offers **every** status value, not a filtered list. The frontend does not know the transition table (`BR-STATUS-005`) and must not pre-empt the server by disabling "invalid" options.
- On 409, the server's `error.message` is displayed **verbatim**. It already names the attempted transition. A client-authored "Invalid transition" string would be a second source of truth and would score zero.
- On success, the row updates in place without a full reload.

This is genuinely counter-intuitive UI — deliberately letting a user attempt something that will fail. It is the correct architecture, and being able to explain *why* at viva is worth more than the smoother alternative.

### 2.4 Stats page (M1.3)

Renders counts by category, by priority and by status from `GET /api/stats`, including explicit zeroes (`AD-025` guarantees every key is present, so the view never needs a fallback for a missing key).

Displays the cache state from the `X-Cache` header (`FR-FE-011`) — a small badge reading HIT or MISS, ideally with the time of the last fetch. Two consecutive loads inside 30 seconds show MISS then HIT; submitting a complaint and reloading shows MISS again because the write invalidated the cache.

Showing your own cache behaviour in the UI is unusual and is exactly the kind of thing that makes a portfolio repository memorable. It is also 3 marks.

### 2.5 Application shell (M1.6)

- `react-router` with three routes and a shared layout.
- **Error boundary** wrapping the router (`FR-FE-017`) so a render-time exception yields a recoverable state, not a blank page.
- No secrets in source, in build-time environment, or in the bundle (`FR-FE-019`, `BR-SEC-002`). Anything in a browser bundle is public; "it's minified" is not a defence.

### 2.6 Serving and runtime configuration (M1.5)

Per `ADR-0002`:

- `nginx.conf.template` contains a `location /api { proxy_pass ${BACKEND_ORIGIN}; }` block and SPA fallback (`try_files $uri /index.html`) for client-side routing.
- `entrypoint.sh` runs `envsubst` over the template and then starts nginx. **If `BACKEND_ORIGIN` is unset, the entrypoint exits with an error** rather than starting nginx with an empty proxy target — a silent misconfiguration here looks like a backend outage.
- The `envsubst` line is the citable line for engineering-notes question 3 ("the exact line guaranteeing build-once-deploy-many").
- Proxy headers must include `X-Forwarded-For`, or the backend's rate limiter sees every request as coming from nginx and becomes global (see M4 §2.2).

---

## 3. Invariants this module must not violate

| Rule | Where it bites |
|---|---|
| `BR-STATUS-005` | No transition table; all statuses offered; 409 message rendered verbatim |
| `BR-VOCAB-005` | Enum lists come from generated types |
| `BR-VAL-001/002` | Client validation mirrors, never replaces |
| `BR-SEC-002` | Nothing secret in the bundle |
| `BR-SEC-004` | No `localhost`, no backend URL, anywhere |
| `FR-FE-018` | No business rule in React |

---

## 4. Tasks

| ID | Task | Size | Owner | Depends on | Delivers | Done when |
|---|---|---|---|---|---|---|
| T-M1-001 | Vite + React + TS scaffold, router, layout, three empty routes | S | Dev 1 | — | — | `npm run dev` serves three routes |
| **T-M1-002** | `nginx.conf.template` + `entrypoint.sh` with `envsubst`, SPA fallback, `X-Forwarded-For` | S | Dev 1 | T-M1-001 | FR-FE-014, ADR-0002 | Container fails loudly with `BACKEND_ORIGIN` unset; proxies correctly when set |
| T-M1-003 | Generate `api/types.ts` from `/openapi.json`; commit; add a regeneration script | S | Dev 1 | M2 T-M2-001 | FR-FE-012 | `tsc --noEmit` passes; types match the contract |
| **T-M1-004** | `api/client.ts`: all endpoints, `X-Request-ID`, single `ApiError` parser, `X-Cache` passthrough | M | Dev 1 | T-M1-003 | FR-FE-012/013 | No `fetch` outside this module |
| T-M1-005 | SubmitPage: form, mirrored validation, loading state, result rendering | M | Dev 1 | T-M1-004 | FR-FE-001…004 | Component tests for validation block, loading state, result render |
| T-M1-006 | Submit error states: 400 field mapping, 429 with `Retry-After`, generic | S | Dev 1 | T-M1-005 | FR-FE-005 | Three visibly distinct states, each asserted |
| T-M1-007 | DashboardPage: server-side list, pagination, `total` | M | Dev 1 | T-M1-004 | FR-FE-006 | Page change issues a new request, not a client slice |
| T-M1-008 | Dashboard filters from generated enums; reset to page 1 on change | S | Dev 1 | T-M1-007 | FR-FE-007, BR-VOCAB-005 | No hand-written enum array in `src/` |
| **T-M1-009** | StatusControl: offers all statuses, renders the server's 409 verbatim | M | Dev 1 | T-M1-007 | FR-FE-008/009, BR-STATUS-005 | Test: 409 response text appears in the DOM unchanged |
| T-M1-010 | StatsPage with aggregates and the `X-Cache` badge | S | Dev 1 | T-M1-004 | FR-FE-010/011 | MISS → HIT visible across two loads |
| T-M1-011 | Error boundary around the router | S | Dev 1 | T-M1-001 | FR-FE-017 | A throwing child yields a recoverable UI, not a blank page |
| T-M1-012 | Vitest suite: ≥ 5 meaningful component tests | M | Dev 1 | T-M1-005…010 | FR-FE-020 | Five tests, each tied to a named requirement, green in CI |
| T-M1-013 | eslint + `tsc --noEmit` clean; no secret patterns in the built bundle | S | Dev 1 | all above | NFR-MAINT-001, NFR-SEC-009 | CI `lint-and-type` job green; bundle grep clean |
| T-M1-014 | Three screenshots for the README | S | Dev 1 | T-M1-010 | FR-DOC-001 | `docs/evidence/` has submit, dashboard, stats |

---

## 5. Test plan (the five that must exist)

Mapped one-to-one onto requirements so "meaningful" is not a matter of opinion:

1. **Validation blocks submission** — a 9-character complaint produces an inline message naming `text`, and no request is issued (`FR-FE-002`).
2. **Loading state is honest** — while the promise is pending, the submit control is disabled and the indicator is present (`FR-FE-003`).
3. **Triage result renders** — given a 201 response fixture, category, priority, summary and a human-readable provider all appear (`FR-FE-004`).
4. **409 is surfaced verbatim** — given a 409 fixture whose message names the attempted transition, that exact string appears in the DOM (`FR-FE-009`, `BR-STATUS-005`).
5. **Cache state renders** — given responses with `X-Cache: MISS` then `HIT`, the badge changes (`FR-FE-011`).

All five mock at the `api/client` boundary, not at `fetch`, so they test the component contract rather than the transport.
