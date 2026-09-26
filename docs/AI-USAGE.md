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
