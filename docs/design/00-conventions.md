# 00 — Project Conventions

**Status:** Authoritative. Revised 2026-09-25 by the specification audit (`docs/audit/01-specification-audit.md`).
**Applies to:** every module
**Read before:** any other design document

This document fixes the things that must be identical everywhere: repository layout, the configuration surface, the error model, the log schema, and naming. An agent implementing any module reads this first, then the module's own design document.

Nothing here is a suggestion. Two modules that disagree about the shape of an error body produce a frontend that cannot render errors and an integration test that cannot assert on them.

---

## 1. Repository layout

The brief's §5.7 layout is normative. The tree below is that layout with the additions this design requires.

```
Civic-Station/
├── backend/
│   ├── app/
│   │   ├── main.py                  # app factory, lifespan, middleware wiring
│   │   ├── config.py                # typed settings, one object, read once
│   │   ├── domain/                  # enums, TriageResult, transition table, domain errors
│   │   ├── routes/                  # HTTP only
│   │   ├── services/                # business rules
│   │   ├── repositories/            # ALL SQL
│   │   ├── providers/
│   │   │   ├── cache/               # Redis port: stats cache, rate limiter, triage cache, outcomes
│   │   │   └── triage/              # base, llm, ollama, rules, simulated, factory, prompt, redact
│   │   ├── observability/           # logging setup, request-id middleware, metrics
│   │   └── db/                      # engine, session factory, ORM models
│   ├── alembic/versions/
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── seeds/complaints.py          # idempotent seed command
│   ├── Dockerfile  .dockerignore  pyproject.toml  alembic.ini
├── frontend/
│   ├── src/
│   │   ├── api/                     # typed client + generated types
│   │   ├── components/
│   │   ├── pages/                   # Submit, Dashboard, Stats
│   │   └── App.tsx  main.tsx
│   ├── tests/
│   ├── Dockerfile  .dockerignore  nginx.conf.template  entrypoint.sh  package.json
├── k8s/
│   ├── base/{namespace,backend,frontend,postgres,redis,ingress,configmap,secret}.yaml
│   ├── base/{hpa,vpa,pdb}.yaml  kustomization.yaml
│   └── overlays/{dev,prod}/kustomization.yaml
├── load/k6-script.js
├── scripts/
│   ├── check_submission.py
│   └── plot_scaling.py              # AD-044: replicas-vs-load chart
├── docs/                            # see docs/README.md
├── .github/workflows/{ci.yml,cd.yml,release.yml}
├── compose.yaml  compose.prod.yaml  .env.example  .gitignore
└── README.md  LICENSE
```

**Rule:** a file that does not fit this tree means either the tree is wrong (fix it here first) or the file is in the wrong layer.

---

## 2. Layer rules, stated as checks

These are the mechanical forms of `NFR-ARCH-001`. `scripts/check_submission.py` enforces them.

| Rule | Check |
|---|---|
| No SQL outside repositories | No `select(`, `session`, `execute(`, or ORM model import anywhere under `routes/`, `services/`, `providers/` |
| No business rules in routes | No import of the transition table or `TRIAGE_*` symbols under `routes/` |
| No vendor SDK outside providers | `openai`, `redis`, `httpx` imported only under `providers/` (and `httpx` in tests) |
| No concrete provider outside its package | `LLMTriage`/`OllamaTriage`/`RuleBasedTriage`/`SimulatedTriage` named only in `providers/triage/` and tests |
| No DDL in application code | No `create_all`, no `CREATE TABLE` outside `alembic/versions/` |
| No duplicated domain rules in the frontend | No status-transition map, no hand-written enum list under `frontend/src/` |

**Direction of dependency:** `routes → services → repositories`, `services → provider ports`, everything → `domain`. `domain` imports nothing from the application.

---

## 3. Configuration surface (the environment variable registry)

One typed settings object, constructed once at startup from the environment. No module reads `os.environ` directly. An unknown or invalid value fails fast at startup with a message naming the variable.

| Variable | Default | Used by | Notes |
|---|---|---|---|
| `DATABASE_URL` | — (required) | M2.5, M3 | `postgresql+asyncpg://…`. Never contains a literal password in a committed file. |
| `REDIS_URL` | — (required) | M4 | `redis://cache:6379/0` |
| `TRIAGE_PROVIDER` | `rules` | M5.1 | One of `llm`, `ollama`, `rules`, `simulated`. Unknown → startup failure naming the variable and listing the legal values. |
| `GROQ_API_KEY` | — | M5.2 | Required only when `TRIAGE_PROVIDER=llm`. Never logged. |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | M5.2 | |
| `TRIAGE_MODEL` | `llama-3.1-8b-instant` | M5.2 | Pinned by name (`AD-045`). Also recorded in `docs/TRIAGE.md`. |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | M5.3 | |
| `OLLAMA_MODEL` | `llama3.2:1b` | M5.3 | Pinned by name (`AD-045`). |
| `TRIAGE_TIMEOUT_SECONDS` | `10` | M5.6 | Hard cap per outbound call. **Refused above 15** by a settings validator (`BR-TRIAGE-008`), because the whole-operation worst case is two calls plus jitter and must stay under the 31 s ceiling the frontend and any proxy read timeout assume. |
| `TRIAGE_CACHE_TTL_SECONDS` | `86400` | M4.3 | 24 h |
| `PROMPT_VERSION` | `v1` | M5.7, M4.3 | Part of the cache key. Bump whenever the prompt changes. |
| `SIMULATED_SEED` | `1337` | M5.5 | |
| `SIMULATED_FAILURE_MODE` | `none` | M5.5 | `none` \| `raise` \| `malformed` \| `slow` |
| `STATS_CACHE_TTL_SECONDS` | `30` | M4.1 | |
| `RATE_LIMIT_REQUESTS` | `10` | M4.2 | Per window, per IP |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | M4.2 | |
| `CORS_ALLOW_ORIGINS` | `` (empty) | M2.1 | Comma-separated. Empty means same-origin only, the normal deployed case under ADR-0002. Dev sets `http://localhost:5173,http://localhost:8080`. |
| `LOG_LEVEL` | `INFO` | M2.6 | |
| `APP_VERSION` | `unknown` | M2.1 | Commit SHA, injected **at runtime** from the Deployment manifest or `compose.prod.yaml` — **never a Docker build argument** (`AD-014`), or the image becomes commit-specific and `NFR-PORT-001` is false. Served by `GET /api/version`. |
| `BACKEND_ORIGIN` | — (required) | M1.5 | **Frontend container only.** nginx proxy target, form `http://<host>:<port>` with no trailing slash — for example `http://backend:8000`. Missing or malformed → entrypoint fails loudly. |
| `BACKEND_PORT` | `8000` | M2.5 | The port uvicorn binds and every probe, healthcheck and proxy target uses. Previously pinned only in an ADR parenthetical. |
| `TRUSTED_PROXY_CIDRS` | `10.0.0.0/8,172.16.0.0/12,192.168.0.0/16` | M4.2 | Peers whose `X-Forwarded-For` is trusted for rate-limit keying (`AD-054`). |
| `READINESS_TIMEOUT_SECONDS` | `1` | M2.1 | Per-dependency timeout for `/ready`. Both checks run concurrently, so the endpoint's worst case is this value, not twice it. |
| `SEED_UUID_NAMESPACE` | `6f2a1c94-3e5b-4d80-9a17-c0b8e4f21d63` | M3.3 | Fixed UUIDv5 namespace, so seed ids are reproducible on any machine (`AD-022`). |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | — (required) | M6 | Consumed by the `postgres` service and composed into `DATABASE_URL`. From `.env` locally, a Secret on the cluster. |
| `IMAGE_TAG` | — (required in prod) | M6.4, M8 | Commit SHA. `compose.prod.yaml` uses `image: ${IMAGE_TAG}`; never `latest` (`FR-K8S-013`). |

`.env.example` lists every variable above with placeholder values and is committed. `.env` is git-ignored and must never appear in history.

---

## 4. The error model

**One error body shape for the whole API.** The frontend renders from this shape and nothing else.

```
{
  "error": {
    "code":    "<machine-readable code>",
    "message": "<human-readable sentence>",
    "fields":  [ { "field": "text", "rule": "min_length", "detail": "..." } ]   // only for validation errors
  },
  "request_id": "<the request id>"
}
```

| HTTP | `code` | Raised when |
|---|---|---|
| 400 | `validation_error` | Request body or query parameters fail validation. `fields` is populated and names every offending field. |
| 404 | `not_found` | Complaint id does not exist. |
| 409 | `invalid_transition` | Status transition not permitted. `message` **names the attempted transition** — this exact string is what the Dashboard renders verbatim. |
| 429 | `rate_limited` | Rate limit exceeded. Response carries a `Retry-After` header in seconds. |
| 503 | `dependency_unavailable` | `/ready` only. `message` names the failed dependency. |

**Rules:**
- FastAPI's default `{"detail": ...}` shape is replaced by an exception handler. A bare `detail` body anywhere is a defect against `BR-VAL-004`.
- A 409 message is authored by the backend and is the single source of that text (`BR-STATUS-005`). Suggested form: `Cannot transition complaint from 'resolved' to 'open'.`
- `request_id` is present on every error body.
- No error body ever contains a stack trace, a database error string, or anything derived from the API key.

---

## 5. Log schema

One JSON object per line, on stdout, never to a file (`BR-OPS-005`).

Required keys on every line: `timestamp` (ISO 8601 UTC), `level`, `event` (a short stable string, not a sentence), `request_id`.

Contextual keys where applicable: `method`, `path`, `status_code`, `duration_ms`, `complaint_id`, `provider`, `error_class`, `fallback`.

**Stable event names** — these are what logs are searched by, so they do not change casually:

| Event | Level | Emitted by |
|---|---|---|
| `request.started` / `request.completed` | INFO | M2.6 middleware |
| `triage.cache_hit` / `triage.cache_miss` | DEBUG | M5.6 |
| `triage.completed` | INFO | M5.6 — carries `provider`, `duration_ms`, `confidence` |
| `triage.retry` | WARNING | M5.6 — carries `error_class` |
| `triage.fallback` | **WARNING** | M5.6 — **exactly one per fallback**, carries `complaint_id`, `provider`, `error_class` (`BR-OPS`, `FR-BE-025`) |
| `triage.validation_failed` | WARNING | M5.6 |
| `ratelimit.exceeded` | INFO | M4.2 |
| `ratelimit.unavailable` | ERROR | M4.2 — fail-open path (`AD-008`) |
| `stats.cache_hit` / `stats.cache_miss` | DEBUG | M4.1 |
| `status.transition_rejected` | INFO | M2.2 |
| `shutdown.started` / `shutdown.completed` | INFO | M2.5 |

**Never logged at any level:** the API key, the database password, `reporter_contact`.

**Complaint `text` is logged only at `DEBUG`**, and `LOG_LEVEL` is `INFO` in every committed configuration, so citizen text does not reach a log shipper by default. Stated as a level rather than as "not at INFO", because the earlier phrasing left `DEBUG` in production sounding acceptable.

**The five log fields are fixed** (`FR-BE-023`): `ts` (RFC 3339, milliseconds, UTC), `level`, `msg`, `request_id` (UUID), `logger`. Handlers may add fields; none of the five may be renamed or dropped, because tests parse them.

---

## 6. Metric names

Prometheus, exposed at `/metrics`. Names are fixed here so dashboards and assertions agree.

| Metric | Type | Labels |
|---|---|---|
| `http_requests_total` | Counter | `method`, `path_template`, `status` |
| `http_request_duration_seconds` | Histogram | `method`, `path_template` |
| `triage_duration_seconds` | Histogram | `provider` |
| `triage_fallback_total` | Counter | `from_provider`, `error_class` |
| `triage_cache_hits_total` | Counter | — |
| `triage_cache_misses_total` | Counter | — |
| `stats_cache_hits_total` | Counter | — |
| `stats_cache_misses_total` | Counter | — |
| `rate_limit_rejected_total` | Counter | — |
| `rate_limiter_unavailable_total` | Counter | — |

**Use `path_template`, not the raw path.** `/api/complaints/{id}` is one label value; the raw path would create one time series per complaint id and blow up the metric cardinality.

**`error_class` obeys the same rule and is a closed set:** `Timeout`, `RateLimited`, `ServerError`, `ValidationFailed`, `Other`, mapped from the exception type. A provider-supplied exception name is unbounded and would blow up cardinality exactly as a raw path does — which the first version of this document forbade in one paragraph and then did in the table above it.

**Histogram buckets**, for both duration histograms: `0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25` seconds. Chosen to straddle the 10 s triage timeout, so a timed-out call and a fast one land in distinguishable buckets.

**Cache counters are separate rather than one counter with a `result` label.** `NFR-PERF-004` computes the hit rate as `hits / (hits + misses)`; with a labelled counter, a query that forgets the label selector silently returns the total instead of the hits, which is the kind of error that produces a plausible wrong number. `FR-BE-009` is the normative list.

---

## 7. Naming conventions

| Thing | Convention | Example |
|---|---|---|
| Python modules and functions | `snake_case` | `triage_service.py`, `apply_status_transition` |
| Python classes | `PascalCase` | `TriageResult`, `LLMTriage` |
| Domain errors | `PascalCase` ending in `Error` | `InvalidTransitionError`, `ComplaintNotFoundError` |
| TypeScript components | `PascalCase` | `SubmitForm.tsx` |
| TypeScript everything else | `camelCase` | `apiClient.ts` |
| Kubernetes objects | RFC 1123 lower-case with dashes | `civic-station`, `backend`, `postgres` |
| Docker Compose services | lower-case, singular | `frontend`, `backend`, `database`, `cache`, `ollama` |
| Environment variables | `SCREAMING_SNAKE_CASE` | `TRIAGE_PROVIDER` |
| Redis keys | `cs:<domain>:<key>` | `cs:stats:v1`, `cs:ratelimit:<ip>:<window>`, `cs:triage:<hash>`, `cs:outcomes` |
| Git branches | `<type>/<area>-<desc>` | `feat/triage-fallback`, `ci/trivy-scan` |
| Commits | Conventional Commits | `feat(triage): add rules fallback with attribution` |

**Service DNS names are the same in Compose and Kubernetes** where possible (`backend`, `database`, `cache`, `ollama`) so that configuration differs by value, not by shape. `localhost` never appears as a service-to-service address (`BR-SEC-004`).

---

## 8. Task conventions

Every task in a module design document has this shape:

- **ID** `T-<MOD>-nnn`
- **Owner** Dev 1 or Dev 2 (per `AD-013`)
- **Depends on** other task IDs, or `—`
- **Delivers** the requirement IDs it satisfies
- **Done when** an observable, checkable condition — not "code written"

**A task is not done until its check passes.** Where a task has non-trivial logic (a branch, a loop, a parser, a money or security path), the check is an automated test. Where it is configuration, the check is a command whose output is captured.

Task sizes are relative, not hours:
- **S** — one sitting, one file, obvious
- **M** — a few files, needs thought, has tests
- **L** — a subsystem; should have been split if it looks larger

---

## 9. Definition of done, applied to every task

1. The `Done when` condition is demonstrably true.
2. Business rules touched by the task are honoured — checked against `BUSINESS-RULES.md`, not from memory.
3. Lint and type check pass (`ruff`, `mypy`, `eslint`, `tsc --noEmit`).
4. A test exists if the task added non-trivial logic.
5. The commit message uses a conventional prefix and references the requirement ID.
6. Nothing secret was added to the working tree.
