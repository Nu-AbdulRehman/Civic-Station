# AI usage

## Documentation

The final documentation in this repository was written with AI assistance (Claude Code).
The AI drafted, structured and formatted the text. All guidance behind it came from a
human in the loop: what to build, how to build it, scope and non-goals, and every ADR and
resolution-log decision in `docs/decisions/OPEN-DECISIONS.md`. The AI recorded those
decisions; it did not make them. The problem statement in `docs/planning/` is the course
brief and was not AI-written.

## Task log

One entry per completed task, appended by the agent that did it (`CLAUDE.md` §8).

- 2026-09-26 · main · Created `docs/AI-USAGE.md` with the Documentation disclosure and
  added the task-logging rule to `CLAUDE.md` §8.
- 2026-09-26 · main · Added the task-log rule to `AGENTS.md` (new "Task log" section and
  item 7 of the phase definition of done).
- 2026-09-26 · feat/T-M2-001-backend-skeleton · A1 (T-M2-001/002/003, FR-BE-010/018/020,
  BR-VOCAB-*, BR-STATUS-002/004): contract-first FastAPI skeleton with all 11 endpoints stubbed,
  `domain/` (enums, transition table, errors, models), typed `config.py`, 32 unit tests,
  root `.gitignore`. Files: `.gitignore`, `backend/**`.
- 2026-09-26 · feat/T-M2-004-errors-observability · A2 (T-M2-004/005, BR-VAL-004, FR-BE-023/024/026,
  NFR-OBS-001/003): single error envelope incl. 400/404/405/413/415/500, request-id middleware,
  structlog JSON logs, fixed Prometheus metrics, path param renamed to `{id}`; AD-057/058 recorded.
  Files: `backend/app/{errors,main}.py`, `backend/app/observability/*`, `backend/tests/**`,
  `docs/decisions/OPEN-DECISIONS.md`.
- 2026-09-26 · feat/T-M3-001-schema-migration · A3 (T-M3-001…004, FR-DATA-001/002/003,
  BR-DATA-001/002, AD-020/021/026/049): async Alembic env, revision `0001` (enum types, table,
  every CHECK, three indexes, strict type drop), `Mapped` ORM model, engine factory,
  `DatabaseSettings`, 20 integration tests against real PostgreSQL. Files: `backend/alembic*`,
  `backend/app/{config.py,db/*}`, `backend/tests/integration/*`, `backend/pyproject.toml`.
- 2026-09-26 · feat/T-M2-006-repositories-seed · A4 (T-M2-006, T-M3-005/006, FR-BE-016/017,
  FR-DATA-004, BR-STATUS-006/007, AD-016/022/059): `ComplaintRepository` (create, get, filtered
  page + total, locked status change, GROUP BY counts), 30-row idempotent seed, migrate/seed
  commands in `README.md`, 13 integration tests. Files: `backend/app/repositories/complaints.py`,
  `backend/seeds/*`, `backend/tests/integration/*`, `README.md`, `OPEN-DECISIONS.md`.
- 2026-09-26 · feat/T-M4-001-cache-port-stats · A5 (T-M4-001/002/003, FR-BE-019,
  FR-CACHE-001/002, AD-055, BR-CACHE-002/007): Redis client factory with 1 s timeouts,
  `StatsCachePort`, `RedisStatsCache` (read-through, 30 s TTL, single-flight lock, fail-soft
  invalidate), 4 integration tests on real Redis. Files: `backend/app/providers/cache/*`,
  `backend/tests/integration/test_stats_cache.py`, `backend/pyproject.toml`.
- 2026-09-26 · feat/T-M4-004-rate-limiter · A6 (T-M4-004/005, FR-CACHE-003, BR-CACHE-004/005/
  006/007, AD-008/018/054): Redis fixed-window limiter (INCR + EXPIRE NX, fake-clock tested),
  fail-open path, single client-IP resolver, `TRUSTED_PROXY_CIDRS` validation, rate-limit
  dependency on `POST /api/complaints` only. Files: `backend/app/{client_ip,config,deps,main}.py`,
  `backend/app/providers/cache/*`, `backend/app/routes/complaints.py`, `backend/tests/**`.
- 2026-09-26 · feat/T-M5-001-triage-contracts · A7 (T-M5-001…005, FR-AI-001…004, BR-TRIAGE-009/
  015, ADR-0004, AD-023/026/060): `TriageProvider`/`TriageOutcome`, `RuleBasedTriage`,
  `SimulatedTriage` (four modes, pinned output), `redact()`, factory wired into `app.state`;
  version/meta report the active provider; seed reuses the rules summary. Files:
  `backend/app/providers/triage/*`, `backend/app/{deps,main}.py`, `backend/app/routes/meta.py`,
  `backend/seeds/complaints.py`, `backend/tests/unit/test_triage_providers.py`.
- 2026-09-26 · feat/T-M4-006-triage-cache-outcomes · A8 (T-M4-006/007, FR-CACHE-004, FR-AI-012,
  FR-BE-006, AD-009/019): `triage_cache_key` + `RedisTriageCache` (24 h TTL, hit/miss counters,
  skip when Redis is down), `RedisOutcomes` (versioned key, LPUSH+LTRIM to 20, six fields only),
  two new ports, 12 integration tests. Files: `backend/app/providers/cache/*`,
  `backend/tests/integration/test_triage_cache_outcomes.py`.
- 2026-09-26 · feat/T-M5-006-triage-pipeline · A9 (T-M5-006/007/011/012, FR-AI-005…010,
  BR-TRIAGE-003/005/006/007/008/010/011, FR-BE-025, AD-007/060/061): `TriagePipeline.run()`
  (redact, cache, hard timeout, one jittered retry, re-validation, rules fallback) and `report()`
  (single fallback WARNING, outcome record), `ProviderHTTPError`, delimited prompt with sentinel
  stripping, 28 unit tests incl. the mandatory fallback test. Files:
  `backend/app/providers/triage/{base,pipeline,prompt}.py`, `backend/app/main.py`,
  `backend/tests/unit/test_triage_pipeline.py`, `docs/decisions/OPEN-DECISIONS.md`.
- 2026-09-26 · feat/T-M2-008-services-routes · A10 (T-M2-007…013, FR-BE-001…015/021, BR-STATUS-*,
  BR-CACHE-001/003, BR-OPS-001/002, AD-024/025): `ComplaintService`, `StatsService`,
  `ReadinessService`, store/triage ports, real routes, `/ready` with concurrent checks, lifespan
  shutdown, outermost CORS (204/403 preflight), in-memory fakes, unit + integration contract
  tests incl. the mandatory fallback test over HTTP. Files: `backend/app/{main,deps,errors}.py`,
  `backend/app/{services,routes}/*`, `backend/app/observability/cors.py`,
  `backend/app/repositories/health.py`, `backend/tests/**`.
- 2026-09-26 · feat/T-M5-008-llm-triage-meta · A11 (T-M5-008/010, FR-AI-005/011/012, FR-BE-006,
  BR-TRIAGE-003/007/014, AD-006/045): `LLMTriage` (Groq via `openai`, JSON mode, `temperature=0`,
  `max_tokens=200`, SDK retries off, fence stripping, SDK errors mapped to `ProviderHTTPError`/
  `TimeoutError`), factory wiring, `ProvidersService` feeding `/api/meta/providers` from
  `cs:outcomes`, mocked-transport tests incl. key-sentinel log check, contract test 19. Files:
  `backend/app/providers/triage/{llm,factory}.py`, `backend/app/services/meta.py`,
  `backend/app/{main,deps}.py`, `backend/app/routes/meta.py`,
  `backend/app/providers/cache/outcomes.py`, `backend/tests/**`, `backend/pyproject.toml`.
- 2026-09-26 · feat/T-M5-009-ollama-triage · A12 (T-M5-009, FR-AI-002, AD-005/006/045/046):
  `OllamaTriage` over `httpx` (`/api/chat`, JSON format, `temperature 0`, `num_predict 200`,
  same prompt and validation), factory wiring, provider pools closed at shutdown, 11
  mocked-transport tests. Files: `backend/app/providers/triage/{ollama,llm,factory}.py`,
  `backend/app/main.py`, `backend/tests/unit/test_{ollama_triage,triage_providers}.py`,
  `backend/pyproject.toml`.
- 2026-09-26 · test/T-M2-015-suite-threshold · A13 (T-M2-015, T-M5-011/012, T-M3-007/008,
  FR-BE-011/027, NFR-TEST-003): coverage gate (`fail_under = 65`, measured 98.3 % branch),
  FR-BE-011(b) route-sweep test, three consecutive green runs (270 tests), index justification in
  `docs/ENGINEERING-NOTES.md`, `docs/failure-log.md` started. Files: `backend/pyproject.toml`,
  `backend/tests/unit/test_route_sweep.py`, `docs/ENGINEERING-NOTES.md`, `docs/failure-log.md`.
- 2026-09-26 · feat/T-M1-001-frontend-scaffold · A14 (T-M1-001…004, FR-FE-012/013/014/016,
  ADR-0002): Vite + React 18 + TS scaffold with three routes, `nginx.conf.template` and
  `entrypoint.sh` (validated `BACKEND_ORIGIN`, single-variable `envsubst`), schema export script,
  generated `types.ts` with runtime enum arrays, typed `api/client.ts`, `.gitattributes` for LF
  scripts. Files: `frontend/**`, `scripts/export_openapi.py`, `.gitattributes`, `.gitignore`,
  `README.md`.
- 2026-09-26 · feat/T-M1-005-submit-page · A15 (T-M1-005/006, FR-FE-001…005/013, BR-VAL-001/002):
  `SubmitPage` (schema-derived bounds, trimmed validation, honest loading, abort on unmount, three
  distinct error states), `TriageResult`, `ErrorBanner`, provider labels, network errors typed in
  the client, Vitest + Testing Library with 12 tests across five files. Files: `frontend/src/**`,
  `frontend/tests/*`, `frontend/{package.json,package-lock.json,vite.config.ts,tsconfig.json}`,
  `docs/failure-log.md`.
- 2026-09-26 · feat/T-M1-007-dashboard · A16 (T-M1-007/008/009, FR-FE-006…009, BR-STATUS-005,
  BR-VOCAB-005): `DashboardPage` (server-side list, fixed page size, abort stale queries),
  `FilterBar` from generated enum arrays with reset to page 1, `Pagination` on server `total`,
  `StatusControl` offering every status and showing the 409 message verbatim, 5 component tests.
  Files: `frontend/src/{pages/DashboardPage,components/*}.tsx`, `frontend/src/styles.css`,
  `frontend/tests/{dashboardMock.ts,DashboardList.test.tsx,StatusConflict.test.tsx}`.
- 2026-09-26 · feat/T-M1-010-stats-boundary · A17 (T-M1-010/011, FR-FE-010/011/017, AD-025):
  `StatsPage` (total and three count tables in generated-enum order, refresh), `CacheBadge` from
  `X-Cache` with fetch time, `ErrorBoundary` inside `<main>` with reset button and reset on
  navigation, 4 component tests. Files: `frontend/src/{App.tsx,pages/StatsPage.tsx}`,
  `frontend/src/components/{CacheBadge,ErrorBoundary}.tsx`, `frontend/src/styles.css`,
  `frontend/tests/{StatsCache,ErrorBoundary}.test.tsx`.
- 2026-09-26 · chore/T-M1-012-frontend-quality · A18 (T-M1-012/013/014, FR-FE-012/019/020,
  NFR-MAINT-001): eslint flat config (TS, react-hooks, `fetch` banned outside the client), two
  set-state-in-effect findings fixed, Vitest coverage gate at 50 % (measured 84 % statements),
  `scripts/scan_bundle.py` secret scan, three screenshots in `docs/evidence/` captured with
  headless Chrome against the seeded backend. Files: `frontend/{eslint.config.js,vite.config.ts,
  package.json,package-lock.json}`, `frontend/src/pages/{Dashboard,Stats}Page.tsx`,
  `scripts/scan_bundle.py`, `docs/evidence/*.png`, `README.md`.
- 2026-09-26 · docs/T-M5-013-triage-layer-check · A19 (T-M2-014, T-M5-013, NFR-ARCH-001/002/004,
  FR-BE-011/020/022, FR-AI-013, NFR-PERF-004, AD-052): `scripts/check_submission.py` (AST layer
  checks + frontend duplicate-rule scan, 26 tests, planted-violation proof), `scripts/measure_triage.py`,
  `docs/TRIAGE.md` with measured cache hit rate (0.20) and rules/simulated baselines; Groq rate
  limits, Groq fallback rate and Groq-vs-Ollama left pending with commands. Files: `scripts/*`,
  `backend/tests/unit/test_check_submission.py`, `docs/TRIAGE.md`, `docs/evidence/triage-*.json`,
  `README.md`.
- 2026-09-26 · fix/openapi-error-responses · OpenAPI schema now documents the errors the API sends
  (FR-BE-002, FR-FE-012): `ErrorResponse`/`FieldError`/`ReadinessFailure` models, per-route 400/404/
  409/413/415/429 responses with `Retry-After`, `Location` and `X-Cache` headers, FastAPI's default
  422 stripped; frontend types regenerated and the client's hand-written error shape replaced by the
  generated one. No wire behaviour changed. Files: `backend/app/{main,errors}.py`,
  `backend/app/domain/models.py`, `backend/app/routes/*`, `backend/tests/unit/*`, `frontend/src/api/*`.
- 2026-09-26 · fix/openapi-error-responses · Live Groq smoke run (T-M5-008) with the developer's key
  from the git-ignored `.env`: pinned `llama-3.1-8b-instant` returned 404; both live candidates
  measured (paced under the observed 8k TPM quota); developers chose `qwen/qwen3.8-27b`; `AD-045`/
  `AD-006` revised; model default, conventions, ADR-0001, M5/M10 guides, FR-AI-013, AGENTS.md and
  `docs/TRIAGE.md` §1/§4/§6/§7 updated; `--interval` pacing added to `measure_triage.py`. Key
  verified absent from logs and working tree. Files: `backend/app/config.py`, `docs/**`, `AGENTS.md`,
  `scripts/measure_triage.py`, `backend/tests/unit/test_llm_triage.py`.
- 2026-09-27 · feat/T-M6-001-containers-compose · P2–P5 + P9 (T-M6-001…008/010/011, T-M4-008
  Compose part, T-M4-009): backend and frontend Dockerfiles + `.dockerignore`, `compose.yaml`
  (5 services + migrate + ollama-pull, 3 networks, 3 volumes), `compose.prod.yaml`, `.env.example`,
  `Makefile`, README quickstart, isolation evidence, notes, AD-062/063, `docs/handover/DEV2-STATUS.md`.
- 2026-09-26 · docs/handoff-dev2 · Wrote `docs/handover/handoff.md` for Dev 2 and their agent: the
  stacked-branch chain and its merge rules (in order, merge commits only, CI first), the CI command
  set, image/Compose/k8s facts about the application, Dev 1 checks that need Dev 2's services,
  decisions to review, and gotchas. Files: `docs/handover/handoff.md`.

## Skill invocations

One entry per skill run (`CLAUDE.md` §6 rule 3).

### 2026-09-26 · feat/T-M2-001-backend-skeleton
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A1 (T-M2-001/002/003) from the
  `03-M2-backend.md` task table, `00-conventions.md` §3/§4 and `01-api-contract.md`.
- **I changed:** accepted as-is. Noted one document conflict: `06-M5-ai-triage.md` places
  `TriageResult` in `providers/triage/base.py`, while `00-conventions.md` §1 and T-M2-002 place it
  in `domain/`. Conventions outrank module guides, so it lives in `domain/` and `base.py` will
  re-export it in T-M5-001.

### 2026-09-26 · feat/T-M2-004-errors-observability
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A2 (T-M2-004/005).
- **I changed:** accepted as-is. Added the 413/415 body checks to A2 because `01-api-contract.md`
  §0 places them in middleware and they must emit the §4 envelope.

### 2026-09-26 · feat/T-M2-004-errors-observability
- **Tool:** Claude Code + `ponytail`
- **Shaped / Wrote:** Decision stubs `AD-057` (log field names) and `AD-058` (500 and
  framework-level error envelopes) in the `OPEN-DECISIONS.md` resolution log.
- **I changed:** accepted as-is. Also collapsed the request-id, logging and metrics steps of
  `03-M2-backend.md` §2.3 into one ASGI middleware; the fixed order is preserved inside it.

### 2026-09-26 · feat/T-M3-001-schema-migration
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A3 (T-M3-001…004).
- **I changed:** Put all three indexes in revision `0001`, following `04-M3-data.md` §2.3 and
  `FR-DATA-003`/`AD-049`; the same document's task table still says "Revision 0002: the two
  indexes" (T-M3-004), which §2.3 itself calls the stale wording. `0002` stays reserved.

### 2026-09-26 · feat/T-M2-006-repositories-seed
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A4 (T-M2-006, T-M3-005/006).
- **I changed:** T-M3-006 reduced to documenting the migrate and seed commands in `README.md`:
  there is no `compose.yaml` yet, and wiring it is T-M6-006 (Dev 2, `AD-013`).

### 2026-09-26 · feat/T-M2-006-repositories-seed
- **Tool:** Claude Code + `ponytail`
- **Shaped / Wrote:** Decision stub `AD-059` (the repository owns the transaction; status change
  is lock, check, update in one method).
- **I changed:** accepted as-is.

### 2026-09-26 · feat/T-M4-001-cache-port-stats
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A5 (T-M4-001/002/003).
- **I changed:** Contract tests 11 and 12 need `StatsService` and `ComplaintService` (T-M2-008/009,
  package A10), so A5 delivers the port, the read-through with single-flight, and `invalidate()`,
  proven by integration tests against real Redis; the route and service wiring lands in A10.

### 2026-09-26 · feat/T-M4-004-rate-limiter
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A6 (T-M4-004/005).
- **I changed:** Key shape `cs:ratelimit:<ip>:<window>` from `00-conventions.md` §7 and
  `05-M4-cache.md`, not `cs:rl:<ip>:<epoch_minute>` from `FR-CACHE-003`: conventions outrank the
  requirement text in the reading order, and a configurable window cannot be keyed by minute.

### 2026-09-26 · feat/T-M5-001-triage-contracts
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A7 (T-M5-001…005).
- **I changed:** `llm` and `ollama` resolve in the factory but exit at startup with a message until
  T-M5-008/009 exist, rather than silently falling back to another provider (`FR-BE-018`).

### 2026-09-26 · feat/T-M5-001-triage-contracts
- **Tool:** Claude Code + `ponytail`
- **Shaped / Wrote:** Decision stub `AD-060` (providers validate at their boundary; the pipeline
  maps `ValidationError` to `ValidationFailed` and re-validates).
- **I changed:** accepted as-is.

### 2026-09-26 · feat/T-M4-006-triage-cache-outcomes
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A8 (T-M4-006/007).
- **I changed:** Outcome entries store exactly the six fields of `FR-BE-006`/`FR-AI-012` and
  `CLAUDE.md` HARD rule 13; `01-api-contract.md` §7 also lists a nullable `recent[].confidence`,
  so the response model keeps that field (always null) rather than changing the frozen API
  surface. The contract's §7 example is the document to fix. Cache key uses the `|` separator
  from `FR-CACHE-004`.

### 2026-09-26 · feat/T-M5-006-triage-pipeline
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A9 (T-M5-006/007).
- **I changed:** The mandatory test is proven at the pipeline boundary here; its HTTP form
  (`POST` -> 201 with `rules:fallback`) needs `ComplaintService` and lands in A10 (T-M2-008).

### 2026-09-26 · feat/T-M5-006-triage-pipeline
- **Tool:** Claude Code + `ponytail`
- **Shaped / Wrote:** Decision stub `AD-061` (`run()`/`report()` split; retry and validation
  logs at INFO so a fallback yields exactly one WARNING).
- **I changed:** accepted as-is.

### 2026-09-26 · feat/T-M2-008-services-routes
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A10 (T-M2-007…013).
- **I changed:** Engine, session factory and Redis client are built in `create_app` (all three
  connect lazily, so nothing is opened before the first request) and closed by the lifespan
  shutdown, instead of being created in lifespan startup: tests can then inject fakes on
  `app.state` without running the lifespan. `/api/meta/providers` `recent` stays for A11
  (T-M5-010, per the work breakdown).

### 2026-09-26 · feat/T-M5-008-llm-triage-meta
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A11 (T-M5-008/010).
- **I changed:** The SDK's own retries are disabled (`max_retries=0`): the pipeline owns the
  single retry (`BR-TRIAGE-007`), and leaving the SDK's default of 2 would have turned "one
  retry" into up to six calls. T-M5-008's "live smoke run" needs a real `GROQ_API_KEY` and is
  left to the developer; every automated test runs against a mocked transport (`NFR-TEST-001`).

### 2026-09-26 · feat/T-M5-009-ollama-triage
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A12 (T-M5-009).
- **I changed:** Done-when "classifies with no egress" needs the Compose `ollama` service and the
  `make pull-models` volume (P9/T-M6-010, Dev 2); A12 delivers the provider against Ollama's
  `/api/chat` contract, proven on a mocked transport. `httpx` moves from a dev-only to a runtime
  dependency, as `AD-005` prescribes it for this provider.

### 2026-09-26 · test/T-M2-015-suite-threshold
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A13 (T-M2-015, T-M5-011/012, T-M3-007/008).
- **I changed:** T-M3-007's "CI job step" lives in `ci.yml` (Dev 2, P10); A13 confirms the
  integration tests already carry up/down/up and seed-twice and hands over the command.
  `docs/failure-log.md` is created now rather than on day 1, with the failures this session hit,
  each dated and described as it happened; stated so the log is not mistaken for a contemporaneous one.

### 2026-09-26 · feat/T-M1-001-frontend-scaffold
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A14 (T-M1-001…004).
- **I changed:** `react-router` 7.18.4 instead of `react-router-dom` 6: v6 carries two open
  advisories (open redirect, SSR constructor injection) that the Trivy job would flag, and
  `AD-037` names `react-router`. `@vitejs/plugin-react` pinned to 4.7.0, the last line whose peer
  range includes Vite 6. The OpenAPI schema is exported by `scripts/export_openapi.py` from the app
  factory, so regenerating types needs no running backend and no `localhost` URL in `frontend/`.

### 2026-09-26 · feat/T-M1-005-submit-page
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A15 (T-M1-005/006).
- **I changed:** Client-side length bounds are read from the committed `openapi.json`
  (`ComplaintCreate.minLength/maxLength`) instead of literal numbers, so the mirror of `BR-VAL-001/002`
  cannot drift from the server. `vitest` 5.0.2 instead of 3.x: 3.x pulls `@vitest/mocker` with a
  moderate advisory, 5.x supports Vite 6 and audits clean.

### 2026-09-26 · feat/T-M1-007-dashboard
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A16 (T-M1-007/008/009).
- **I changed:** accepted as-is.

### 2026-09-26 · feat/T-M1-010-stats-boundary
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A17 (T-M1-010/011).
- **I changed:** The error boundary wraps the routed content inside `<main>` rather than the whole
  router, so the navigation stays usable after a crash, which is what `FR-FE-017`'s acceptance
  asserts; it resets on navigation as well as on its own button.

### 2026-09-26 · chore/T-M1-012-frontend-quality
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A18 (T-M1-012/013/014).
- **I changed:** Added an eslint rule that bans `fetch` everywhere except `src/api/client.ts`, so
  `FR-FE-012`'s "no fetch outside the client" is enforced mechanically rather than by grep in
  review. The bundle secret scan is a small Python script under `scripts/` so
  `check_submission.py` (T-M2-014, P22) can reuse the same pattern set.

### 2026-09-26 · docs/T-M5-013-triage-layer-check
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A19 (T-M5-013, T-M2-014).
- **I changed:** `check_submission.py` is created with the M2 layer checks only (T-M2-014); the
  §5.3 infrastructure detectors (secrets in history, Compose, k8s, CI `needs:`) are T-M8-014 (Dev 2)
  and slot in as further functions in the same registry. `app/db/` is allowed to import
  `sqlalchemy` alongside `repositories/`, because `00-conventions.md` §1 puts the engine and ORM
  models there; `NFR-ARCH-001`'s list omits it. `docs/TRIAGE.md` reports only numbers actually
  measured here; the Groq and Ollama figures need a live key and pulled weights, so those sections
  name the pending measurement and its exact command instead of inventing values.

### 2026-09-27 · feat/T-M6-001-containers-compose
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for P2–P5 + P9 from `07-M6-containers.md` §6 (10 items,
  each tagged T-M6-nnn).
- **I changed:** accepted as-is.

### 2026-09-27 · feat/T-M6-001-containers-compose
- **Tool:** Claude Code + `ponytail`
- **Shaped / Wrote:** Decision record for two images under one `IMAGE_TAG` in `compose.prod.yaml`,
  recorded as `AD-062`.
- **I changed:** accepted as-is.

### 2026-09-27 · feat/T-M6-001-containers-compose
- **Tool:** Claude Code (design fork recorded without a separate skill run)
- **Shaped / Wrote:** `AD-063`, frontend base moved from `nginx:1.27.5-alpine` to
  `nginx:1.30.5-alpine3.24-slim` after Trivy and the 60 MB gate both failed on the design doc's pin.
- **I changed:** the fork was found by measurement mid-build; `ponytail` was not re-invoked for it.
  Disclosed here rather than reconstructed.

### 2026-09-27 · feat/T-M6-001-containers-compose
- **Tool:** Claude Code, diff self-review (the installed `grilling` skill questions a person about a
  plan, not a diff — the open process gap in the Dev 1 handoff §7)
- **Shaped / Wrote:** Findings on the branch diff: (1) `compose.yaml` `ollama-pull` wait loop had
  no bound, so a failed `ollama serve` hung `make pull-models` forever — fixed, 30 s cap;
  (2) `compose.yaml:44` dev backend runs `--reload`, so PID 1 is the reloader and the SIGTERM drain
  check (T-M2-012) is not meaningful against the dev file — WONTFIX, run it against
  `compose.prod.yaml`'s command; (3) `.env.example:9` puts a credential-shaped URL
  (`civic:PLACEHOLDER_change_me@`) in the tree, which T-M8-014's secret detector must allow by
  the `PLACEHOLDER_` prefix rather than flag — carried to T-M8-014; (4) an existing `.env` without
  `POSTGRES_*` makes `make up` stop with `POSTGRES_USER: set in .env` — intended, loud failure.
- **I changed:** fixed (1); (2) and (3) documented, (4) accepted.
