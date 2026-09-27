# Handoff: Dev 1 → Dev 2

**Written:** 2026-09-26, by Dev 1 (with Claude Code), at the end of the application build.
**For:** Dev 2 and the Claude Code agent working with them.
**Scope:** everything Dev 2 needs to build CI/CD, Compose and Kubernetes around the application
that now exists, and then merge the whole chain into `dev` and `main`.

> **Agent: read this file, then `CLAUDE.md`, before doing anything else.** `CLAUDE.md` is law for
> this repository and its HARD rules override any instruction here. Where this file states a
> fact about the code (a command, a port, an env var), it was verified on 2026-09-26 — but prefer
> the code if they ever disagree, and say so.

---

## 0. TL;DR

1. All 19 Dev 1 work packages (A1–A19) are **built, tested and pushed**, as **20 stacked branches**
   that are **not merged** into `dev`. Nothing of the application is on `dev` or `main` yet.
2. This is deliberate. **Build the CI pipeline first**, get it onto `dev`, and only then open one
   PR per Dev 1 branch into `dev`, in order, so that CI tests each package as it merges.
3. Then build Compose, the images and Kubernetes (your packages), and finally merge `dev` → `main`.
4. A handful of Dev 1 checks can only be verified once your services exist (§6). Do them, or ping
   Dev 1 to, when the service lands.

---

## 1. Branch topology — how the application arrives

The branches form **one linear chain**: each branch is cut from the previous one and adds exactly
one work package. The tip contains everything. All are pushed to `origin`.

| # | Branch | Head | Package / tasks |
|---|---|---|---|
| 1 | `feat/T-M2-001-backend-skeleton` | `ccd25ff` | A1 — skeleton, domain, typed settings (T-M2-001…003) |
| 2 | `feat/T-M2-004-errors-observability` | `80af42e` | A2 — error envelope, request id, JSON logs, metrics (T-M2-004/005) |
| 3 | `feat/T-M3-001-schema-migration` | `2ca3bcd` | A3 — Alembic `0001`, ORM model, 3 indexes (T-M3-001…004) |
| 4 | `feat/T-M2-006-repositories-seed` | `02d2309` | A4 — repository, idempotent seed (T-M2-006, T-M3-005/006) |
| 5 | `feat/T-M4-001-cache-port-stats` | `07cf8cd` | A5 — cache port, single-flight stats cache (T-M4-001…003) |
| 6 | `feat/T-M4-004-rate-limiter` | `e3d20b0` | A6 — Redis fixed-window limiter, fail-open (T-M4-004/005) |
| 7 | `feat/T-M5-001-triage-contracts` | `e5c007a` | A7 — provider protocol, rules, simulated, redact, factory (T-M5-001…005) |
| 8 | `feat/T-M4-006-triage-cache-outcomes` | `549e008` | A8 — triage cache, outcomes list (T-M4-006/007) |
| 9 | `feat/T-M5-006-triage-pipeline` | `a9c836c` | A9 — resilience pipeline, prompt guardrail (T-M5-006/007) |
| 10 | `feat/T-M2-008-services-routes` | `ac387be` | A10 — services, real routes, `/ready`, lifespan, CORS (T-M2-007…013) |
| 11 | `feat/T-M5-008-llm-triage-meta` | `278acd1` | A11 — Groq `LLMTriage`, `/api/meta/providers` (T-M5-008/010) |
| 12 | `feat/T-M5-009-ollama-triage` | `c354e2d` | A12 — `OllamaTriage` (T-M5-009) |
| 13 | `test/T-M2-015-suite-threshold` | `fc0adea` | A13 — coverage gate, route sweep, index notes (T-M2-015, T-M3-007/008) |
| 14 | `feat/T-M1-001-frontend-scaffold` | `aaf8ef4` | A14 — frontend scaffold, nginx template, types, client (T-M1-001…004) |
| 15 | `feat/T-M1-005-submit-page` | `b90642f` | A15 — Submit page (T-M1-005/006) |
| 16 | `feat/T-M1-007-dashboard` | `16e96d1` | A16 — Dashboard (T-M1-007…009) |
| 17 | `feat/T-M1-010-stats-boundary` | `da1f74d` | A17 — Stats page, error boundary (T-M1-010/011) |
| 18 | `chore/T-M1-012-frontend-quality` | `e97751e` | A18 — eslint, coverage, bundle scan, screenshots (T-M1-012…014) |
| 19 | `docs/T-M5-013-triage-layer-check` | `511d532` | A19 — `check_submission.py`, `TRIAGE.md` (T-M2-014, T-M5-013) |
| 20 | `fix/openapi-error-responses` | `e21bd84` | OpenAPI error responses + Groq model change to `qwen/qwen3.8-27b` (AD-045 rev) |
| 21 | `docs/handoff-dev2` | — | This file |

Verify with: `git log --oneline dev..docs/handoff-dev2` (21 commits, oldest at the bottom).

### 1.1 Merge rules that follow from the chain — do not break these

- **Merge in order, #1 first.** Each PR is `branch N → dev`. Once #N−1 is merged, PR #N's diff
  on GitHub shows only package N. Open a PR only after its predecessor is merged, or GitHub will
  show the whole stack.
- **Merge commits only, never squash, never rebase** (`FR-CICD-012`, `CLAUDE.md` rule 2). A
  squash or rebase merge rewrites the parent commit, and every later branch in the chain then
  conflicts against `dev`. With merge commits, each later branch merges cleanly.
- **Do not rebase or force-push any Dev 1 branch.** If one needs a fix, add a commit on that
  branch (and expect the later branches to pick it up via their own merge), or fix it forward on
  `dev` after the chain is in.
- **Every PR needs a partner review with a substantive comment** (`FR-PROC-002`). Dev 2 reviews
  Dev 1's PRs; Dev 1 reviews Dev 2's. Nobody approves their own PR. "LGTM" is not a review.
- **Nothing goes to `main` except a merge from `dev`** with green CI and one approval
  (`BR-DEL-003`). Never push to `main`.

---

## 2. The plan, in order

### Step 1 — build CI on its own branch, before any Dev 1 PR

Create your CI work (`P1`, `P6`, `P10` in `docs/schedule/01-work-breakdown-and-critical-path.md`;
`T-M8-001…004`, `T-M8-008`) **on a branch cut from the chain tip** (`docs/handoff-dev2`), so you
can run and debug the workflows against the real code. Then move the workflow files onto a branch
cut from `dev` (cherry-pick the CI commits), and merge that into `dev` first.

**Guard every job for code that does not exist yet.** When PR #1 opens, `dev` has no frontend, no
Alembic and no `scripts/`. A job that runs on a directory that is not there must end green, not red.
`hashFiles()` is **not** available in a job-level `if:`, only in steps, so either put the condition
on each step, or add a first "detect" step and gate the rest on its output:

```yaml
steps:
  - uses: actions/checkout@<pinned-sha>
  - id: has
    run: echo "frontend=$(test -f frontend/package.json && echo yes || echo no)" >> "$GITHUB_OUTPUT"
  - if: steps.has.outputs.frontend == 'yes'
    run: npm ci
    working-directory: frontend
```

Presence markers: `frontend/package.json` from PR #14, `backend/alembic.ini` (integration tests)
from PR #3, `scripts/check_submission.py` from PR #19. A job whose steps are all skipped reports
success, so it still satisfies a required status check.

### Step 2 — merge the chain into `dev`, one PR per branch, oldest first

For each branch in §1's table: open the PR into `dev`, wait for CI, get Dev 1's (or your) partner
review as appropriate, **merge commit**, next. Expect every job that exists at that point to pass —
each branch was green locally at its own commit for the checks that existed then (§5 lists them).

If a job fails on an intermediate branch, **read the failure before touching anything**: it is
more likely a CI configuration issue (missing service, wrong env var, a job that should have been
skipped) than an application bug, because every package passed its own suite. Record anything
that cost time in `docs/failure-log.md` as it happens (`CLAUDE.md` §5).

### Step 3 — your platform packages

Compose, images, Kubernetes, CD, load evidence (`P2`–`P5`, `P8`, `P9`, `P11`–`P25`). §3 and §4 give
the facts about the application you need; the design docs `07-M6`…`10-M9` give the requirements.

### Step 4 — `dev` → `main`

One PR, green CI, one approval, merge commit. Then the CD pipeline (`cd.yml`) deploys by SHA.

---

## 3. Facts about the backend you need for images, Compose and Kubernetes

### 3.1 Runtime

| Thing | Value |
|---|---|
| Python | **3.12** (`backend/.python-version`); deps via **uv** with the committed `backend/uv.lock` — use `uv sync --frozen` |
| Working directory | `backend/` (the package is `app`, the seed is `seeds`, migrations under `alembic/`) |
| Start command | `uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000` |
| Port | **8000**. `BACKEND_PORT` exists in settings but uvicorn reads `--port`, so pass the port on the command line |
| Liveness | `GET /health` → 200 `{"status":"ok"}`; touches no dependency (`BR-OPS-001`) |
| Readiness | `GET /ready` → 200, or **503** with `{"error":{...},"request_id":...,"checks":{"database":"ok|fail","cache":"ok|fail"}}`; both checks concurrent, each ≤ `READINESS_TIMEOUT_SECONDS` (1 s) |
| Metrics | `GET /metrics` (Prometheus text) |
| Version | `GET /api/version` → `{"version": APP_VERSION, "provider": ...}`; `APP_VERSION` is a **runtime** env var, never a build arg (`AD-014`) |
| Logs | one JSON object per line on **stdout**, fields `ts`, `level`, `msg`, `request_id`, `logger` (`AD-057`) |

Container specifics:

- **Exec-form `CMD`**, so uvicorn is PID 1 and receives SIGTERM (`FR-BE-021`). Shell form breaks
  the graceful drain and the zero-downtime rollout.
- Add **`--timeout-graceful-shutdown 25`** to the uvicorn command: `terminationGracePeriodSeconds`
  is 30 with a 5 s `preStop` sleep (`BR-OPS-004`), and the worst-case request is ~25 s.
- Add **`--no-proxy-headers`**. Client-IP resolution is done once, in `backend/app/client_ip.py`,
  from `X-Forwarded-For` and `TRUSTED_PROXY_CIDRS` (`AD-054`); uvicorn's own proxy-header handling
  must not rewrite the peer first.
- `python:3.12-slim` has no `curl`. A Docker `HEALTHCHECK` can use
  `python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"`.
- The app connects to nothing at construction; engine, Redis client and provider pools open on
  first use and are closed in the lifespan shutdown (logs `shutdown.started` / `shutdown.completed`).

### 3.2 Configuration (the full registry is `docs/design/00-conventions.md` §3)

Required at startup: `DATABASE_URL` (`postgresql+asyncpg://…`), `REDIS_URL` (`redis://cache:6379/0`).
An unknown or invalid value exits non-zero with a message naming the variable.

| Variable | Deployed value | Note |
|---|---|---|
| `TRIAGE_PROVIDER` | `llm` on the cluster, `simulated` in CI | `llm` requires `GROQ_API_KEY` |
| `GROQ_API_KEY` | from a Secret / GitHub Secret | **Never** in a manifest, Dockerfile, `.env.example`, or log (`CLAUDE.md` rule 1) |
| `TRIAGE_MODEL` | default `qwen/qwen3.8-27b` | Changed on 2026-09-26 — see §7 |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | `http://ollama:11434` / `llama3.2:1b` | Compose only (Ollama is not deployed to k8s) |
| `CORS_ALLOW_ORIGINS` | **empty** when deployed | Same-origin via nginx/Ingress; dev sets `http://localhost:5173,http://localhost:8080` |
| `TRUSTED_PROXY_CIDRS` | default private ranges | Validated at startup |
| `RATE_LIMIT_REQUESTS` / `_WINDOW_SECONDS` | 10 / 60 | Raise only for a measurement run |
| `LOG_LEVEL` | `INFO` everywhere committed | Complaint text is logged only at `DEBUG` |
| `APP_VERSION` | the commit SHA, set at runtime | |

**`.env.example` does not exist yet** — it is your `T-M6-008`. It must list every variable in the
registry with placeholder values only. The root `.gitignore` already ignores `.env` and `.env.*`
while allowing `.env.example`.

### 3.3 Database and seed — a deliberate step, never at startup (`BR-DATA-001`)

From `backend/`, with only `DATABASE_URL` set (Alembic does not need `REDIS_URL`):

```sh
uv run alembic upgrade head        # or: alembic upgrade head   inside the image
uv run python -m seeds.complaints  # 30 fixture rows; idempotent, safe to re-run
```

Compose: a one-shot `migrate` service before `backend` (T-M6-006). Kubernetes: an init container on
the backend Deployment (`08-M7-kubernetes.md`). The seed is exempt from the SQL-layer rule and runs
outside any request path.

### 3.4 Redis

Four jobs, five key shapes (`05-M4-cache.md`): `cs:stats:v1`, `cs:stats:lock`,
`cs:ratelimit:<ip>:<window>`, `cs:triage:<sha256>`, `cs:outcomes:<PROMPT_VERSION>`. Needs AOF on the
`redisdata` volume and `maxmemory 256mb` + `allkeys-lru` (T-M4-008). Redis down never crashes the
app: the limiter fails open (ERROR log + `rate_limiter_unavailable_total`), stats return `MISS`,
`/ready` returns 503 naming `cache`.

---

## 4. Facts about the frontend you need for the image and the Ingress

| Thing | Value |
|---|---|
| Build | `cd frontend && npm ci && npm run build` → `frontend/dist/` (`build` runs `tsc --noEmit` then `vite build`) |
| Node | pin `node:22-alpine` in the build stage (`FR-CTR-004`); local builds used Node 24, `package-lock.json` is compatible |
| Serve image | `nginx:1.27-alpine`, static files in `/usr/share/nginx/html` |
| Config template | copy `frontend/nginx.conf.template` to **`/etc/nginx/templates/nginx.conf.template`** |
| Entrypoint | copy `frontend/entrypoint.sh`, `chmod +x`, **exec-form** `ENTRYPOINT ["/entrypoint.sh"]` |
| Listen port | **8080** (so the container can run non-root) |
| Required env | `BACKEND_ORIGIN`, e.g. `http://backend:8000` — no trailing slash; the entrypoint exits 1 if it is unset or malformed |

- The entrypoint renders `/etc/nginx/conf.d/default.conf` with `envsubst '${BACKEND_ORIGIN}'`
  (restricted to that one variable, so nginx's own `$uri` etc. survive) and then `exec nginx`.
  For a non-root image, `/etc/nginx/conf.d`, `/var/cache/nginx` and the pid path must be writable.
- nginx proxies `/api` with `X-Forwarded-For $proxy_add_x_forwarded_for` and a 31 s read timeout.
- **The browser only ever calls relative `/api/...`** (`ADR-0002`). There is no backend URL in the
  bundle, so the same image digest must serve Compose and the cluster (`FR-FE-014`).
- **Ingress:** route `/api` **straight to the backend Service**, and `/` to the frontend. If a
  request ever passes Ingress → frontend nginx → backend, there are two trusted proxies and the
  "last `X-Forwarded-For` entry" rule (`AD-054`) resolves every client to the Ingress address, which
  turns the per-IP limiter into one global bucket. `T-M9-008` (4 replicas, 30 requests → exactly
  10 × 201 and 20 × 429) is the test that would expose this.
- `.gitattributes` forces LF for `*.sh` and `*.template`. Keep it: a CRLF `entrypoint.sh` fails
  inside the container with a confusing "not found".
- Verified on 2026-09-26 by mounting the files into `nginx:1.27-alpine` (no Dockerfile existed):
  unset `BACKEND_ORIGIN` → exit 1; set → `/api/*` proxied, `/dashboard` served the SPA shell.

---

## 5. Commands for the CI jobs (all verified locally on 2026-09-26)

**Backend** (`working-directory: backend`, Python 3.12 + uv):

```sh
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run mypy app tests seeds alembic
uv run pytest tests/unit tests/integration --cov        # fails under 65 % (pyproject.toml)
```

- The integration tests need **real PostgreSQL 16 and Redis 7 as GitHub service containers**
  (`AD-010`) — never SQLite. Env for the step:
  `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/civic_test`,
  `REDIS_URL=redis://localhost:6379/0`, `TRIAGE_PROVIDER=simulated`.
  (`localhost` is correct here: it is the runner reaching its own service containers, not
  service-to-service traffic. `CLAUDE.md` rule 16 is about Compose and Kubernetes.)
- **The database name must end in `_test`.** The integration suite downgrades the schema and
  truncates tables, and refuses to run against any other name (`backend/tests/integration/conftest.py`).
- `pytest` with no path runs `tests/unit` only (the fast loop, no services needed).
- Current numbers at the chain tip: **297 tests, 98.4 % branch coverage**.
- No test calls a hosted model. Never put `GROQ_API_KEY` in CI test jobs.

**Frontend** (`working-directory: frontend`):

```sh
npm ci
npm run lint            # eslint, incl. a rule banning fetch() outside src/api/client.ts
npm run typecheck       # tsc --noEmit
npm run test:coverage   # vitest; fails under 50 % (vite.config.ts) — use this, not `npm test`
npm run build
npm run scan:bundle     # python ../scripts/scan_bundle.py dist — secret patterns of FR-FE-019
```

Current numbers: **21 tests, 84 % statement coverage**.

**Contract drift** (`FR-BE-010`, `FR-FE-012`) — regenerate the frontend types from the backend and
fail if they changed:

```sh
cd frontend && npm run gen:types && git diff --exit-code src/api/
```

(`gen:types` runs `uv run --project ../backend python ../scripts/export_openapi.py …`, so the job
needs both Node and uv. No server is started.)

**Submission check** (`submission-check`, required, from the repository root, stdlib only):

```sh
python scripts/check_submission.py
```

---

## 6. Dev 1 checks that need your services — do them when the service exists

| Check | Needs | How | Done when |
|---|---|---|---|
| **SIGTERM drain** (T-M2-012, `FR-BE-021`) | Compose backend | `docker compose exec backend kill -TERM 1` during an in-flight `POST /api/complaints` (use `TRIAGE_PROVIDER=simulated` + `SIMULATED_FAILURE_MODE=slow` with a short `TRIAGE_TIMEOUT_SECONDS` to hold it open) | The POST returns 201 and the container exits 0 within 30 s |
| **Ollama with no egress** (T-M5-009) | Ollama service on `internal`, `make pull-models` (P9, T-M6-010) | Run the stack with `TRIAGE_PROVIDER=ollama`, submit a complaint | `triaged_by: "llm:ollama"` |
| **Ollama numbers for `docs/TRIAGE.md`** §6/§7 (T-M5-013) | Same | From `backend/`: `TRIAGE_PROVIDER=ollama OLLAMA_BASE_URL=http://<reachable>:11434 uv run python ../scripts/measure_triage.py provider --out ../docs/evidence/triage-ollama.json`, then `compare` against `docs/evidence/triage-groq-qwen-qwen3-8-27b.json` | Ollama row and agreement filled in; report timeouts separately |
| **One image, two environments** (`FR-FE-014`, `NFR-PORT-001`) | Frontend image, Compose, k3d | Same digest, different `BACKEND_ORIGIN` | Both work; capture in `docs/evidence/` |
| **Migrate + seed in Compose** (T-M3-006 ↔ T-M6-006) | `compose.yaml` | `make up` from empty | Seeded database, no DDL from app startup |
| **Distributed limiter** (T-M4-010, T-M9-008) | 4 backend replicas | 30 POSTs from one source in one window | Exactly 10 × 201, 20 × 429, each with `Retry-After` |
| **Screenshots from the container** (optional) | Compose stack | Re-capture `docs/evidence/{submit,dashboard,stats}.png` through nginx | Current ones were taken via the Vite dev server |

When you run anything with a real Groq key: key in the environment or the git-ignored `.env` only,
and confirm afterwards with `git grep -n "gsk_"` (must print nothing).

---

## 7. Decisions and changes made during the build that you should know about

Recorded in `docs/decisions/OPEN-DECISIONS.md` ("Round 6" and the revised rows). **Please read and
accept or challenge them** — they were recorded before the code, as `CLAUDE.md` §5 requires, but
you have not seen them yet.

| ID | What |
|---|---|
| `AD-057` | Log fields are `ts`, `level`, `msg`, `request_id`, `logger` (the `FR-BE-023` set). |
| `AD-058` | Error codes for 500 / 405 / 413 / 415 / 403-preflight all use the one envelope. |
| `AD-059` | The repository owns the transaction; status change = row lock → table check → update. |
| `AD-060` | Providers validate model output at their boundary; the pipeline re-validates. |
| `AD-061` | The pipeline has `run()` and `report()`; retry/validation logs are INFO so a fallback emits exactly one WARNING. |
| **`AD-045` (revised)** | **Groq model is now `qwen/qwen3.8-27b`.** The pinned `llama-3.1-8b-instant` returned `404 model_not_found`; Groq no longer serves Llama chat models. Measured choice, see `docs/TRIAGE.md` §7. |
| **API surface** | The **OpenAPI schema** now documents the real error responses (400/404/409/413/415/429 in the `ErrorResponse` envelope, 503 `ReadinessFailure` on `/ready`) and no longer shows FastAPI's default 422. The wire behaviour did not change, but `CLAUDE.md` rule 7 makes any API-surface change a both-agreed PR — please confirm on PR #20. |

**Observed Groq limits** (2026-09-26): 1,000 requests per window and **8,000 tokens/minute** — about
11 triage calls a minute for the whole system, which is below `AD-017`'s 10/min *per client*. Two
busy clients reach the quota; the app then falls back to rules with a 201. Worth a sentence in the
runbook and the engineering notes. Re-verify before submission.

**Open for a joint decision:** `AD-049` — the two filtered indexes lack an `id DESC` tail, so the
API's `ORDER BY created_at DESC, id DESC` needs a small incremental sort on filtered lists
(`docs/ENGINEERING-NOTES.md`, "Indexes"). Adding it is a new revision `0002`. Not done.

**Process gap to resolve together:** `CLAUDE.md` §6 requires a `grilling` skill run before every PR,
producing ≥ 3 file:line findings on the diff. The installed `grilling` skill grills a *person about
a plan*, not a diff. Dev 1's packages list three review findings each in the session instead;
decide whether to change the rule, or run a diff review (`/code-review`) per PR and log it in
`docs/AI-USAGE.md`.

---

## 8. `scripts/check_submission.py` — extend, do not replace (T-M8-014)

It exists with the **M2 layer checks** (T-M2-014): an AST walk for reverse imports, `sqlalchemy`
outside the SQL layer, vendor SDKs outside `providers/`, `os.environ` outside `app/config.py`,
concrete triage classes outside `providers/triage/`, DDL outside migrations; plus a scan of
`frontend/src/` for hand-written enum lists and transition maps. 26 tests in
`backend/tests/unit/test_check_submission.py` plant each violation and assert it is caught.

Add your §5.3 detectors (`09-M8-cicd.md` §10: secrets in the tree and in `git log -p`, Secret
placeholders, image tags and `:latest`, `localhost` in `compose*`/`k8s/`/`frontend/src/`,
`compose.prod.yaml` ports and `build:`, CI `needs:`, Postgres StatefulSet) as **new functions
appended to `CHECKS`**, each returning a list of `Finding`s. Reuse `SECRET_PATTERNS` from
`scripts/scan_bundle.py`. Keep it stdlib-only so it runs before any install. Add a planted-violation
test per detector, as the existing ones do (`CLAUDE.md` rule 14: a test that cannot fail is not a
test).

---

## 9. Gotchas already paid for (details in `docs/failure-log.md`)

- **Alembic enum types**: revision `0001` creates and drops them with `checkfirst=False` on
  purpose. A leftover type must fail the next upgrade loudly.
- **CRLF**: this repo is checked out with `core.autocrlf=true` on Windows; `.gitattributes` protects
  the scripts that run in Linux containers. Add any new container shell scripts to it.
- **Library versions that differ from what the docs assume**: `openai` 3.x (uses `httpx2`
  internally), `redis` (Python client) 8.x against Redis server 7, `react-router` 7 (not
  `react-router-dom` 6, which carries two advisories), `vitest` 5, `@vitejs/plugin-react` 4.7 (the
  last line supporting Vite 6). All pinned in the lock files; `npm audit` and the Python deps were
  clean on 2026-09-26.
- **Vitest hook bodies**: `beforeEach(() => mock.mockReset())` returns the mock, and Vitest calls a
  returned function as teardown. Always use a block body in hooks.
- **A pinned hosted model can disappear.** The CD smoke test (`T-M8-010`) should submit one complaint
  and fail if `triaged_by` is `rules:fallback` on the deployed `llm` provider — otherwise a retired
  model looks like a healthy deployment, because the fallback path returns 201.

---

## 10. Where things are

| Need | Look at |
|---|---|
| Rules | `CLAUDE.md`, `AGENTS.md` |
| Your task tables | `docs/design/07-M6-containers.md`, `08-M7-kubernetes.md`, `09-M8-cicd.md`, `10-M9-load-evidence.md`, `05-M4-cache.md` (T-M4-008…010) |
| Package list and critical path | `docs/schedule/01-work-breakdown-and-critical-path.md` |
| Every decision | `docs/decisions/OPEN-DECISIONS.md` (resolution log) |
| API contract | `docs/design/01-api-contract.md`, and `frontend/src/api/openapi.json` (generated) |
| What AI did, per task | `docs/AI-USAGE.md` — append your own entries, per `CLAUDE.md` §6/§8 |
| How to run things locally | `README.md` |
