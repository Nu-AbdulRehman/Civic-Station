# 07 — M6 Containerisation: design and implementation guide

**Owner:** Dev 2 (`AD-013`)
**Depends on:** M2 `T-M2-001` (the contract-first skeleton), M1 `T-M1-002` (nginx template)
**Delivers:** `RUB-G-01`…`RUB-G-06`, and four of the eleven automatic deductions. Mark totals are not quoted in design documents (`AD-047`).
**Stack:** Docker multi-stage builds, Compose v2, three networks, three named volumes

---

## 1. What this module is for

Two images and two Compose files, built so that the images are environment-independent and the topology makes a class of attack impossible rather than merely discouraged.

The marked ideas here are **network segmentation** and **explicit persistence**. The satisfying deliverable is a *failing* command: `docker compose exec frontend ping database` must fail, and that failure is evidence of correct design.

---

## 2. Images

### 2.1 Backend image (M6.1)

- **Multi-stage.** Builder stage installs dependencies with `uv` from `pyproject.toml` + lock file; runtime stage copies only the installed environment and the application source.
- **Pinned base**, `python:3.12-slim` with an explicit tag (`FR-CTR-004` — an unpinned base is −8).
- **Layer order** is dependency manifests first, source second (`NFR-PERF-006`). A one-line source change must not reinstall dependencies; the rebuild time before and after is a number reported in the engineering notes.
- **Non-root `USER`** (`NFR-SEC-002`). Create the user in the runtime stage and `chown` only what needs it.
- **Exec-form `CMD`.** This is not style: shell-form `CMD` makes the shell PID 1, the shell does not forward SIGTERM, and the graceful shutdown in `FR-BE-021` silently stops working. A backend bug whose cause is a Dockerfile line.
- **`HEALTHCHECK`** declared, hitting `/health` (never `/ready` — a healthcheck that depends on the database makes Compose's `service_healthy` gate on the wrong thing).
- **Build argument `APP_VERSION`** carrying the commit SHA, surfaced as an environment variable for `GET /api/version` (`AD-014`).

### 2.2 Frontend image (M6.2)

- `node:22-alpine` build stage runs `npm ci` and `npm run build`; `nginx:1.27-alpine` runtime stage copies only `dist/`, the nginx template and the entrypoint.
- **The final image contains no Node, no `node_modules`, no source** (`NFR-PORT-002`). Verify by inspecting the image, not by assuming.
- **Non-root, and here is what that actually requires** — `nginx:alpine` does not run unprivileged without these four changes, and omitting any one of them produces a container that exits on start:
  1. `USER 101` (the `nginx` user that ships in the image).
  2. **Listen on `8080`**, not 80 — a non-root process cannot bind a privileged port.
  3. Redirect every writable path into `/tmp`: `client_body_temp_path`, `proxy_temp_path`, `fastcgi_temp_path`, `uwsgi_temp_path`, `scgi_temp_path`, and `pid /tmp/nginx.pid`.
  4. `chown` the `dist/` output and the generated config to 101 in the build stage.
- Entrypoint runs `envsubst` then `exec nginx -g 'daemon off;'` — `exec` so nginx becomes PID 1 and receives signals.
- **Size budget: 60 MB, as a hard CI gate** (`NFR-PERF-007`). Measured as the `Size` field from `docker image inspect` divided by 1 000 000 — uncompressed, on-disk. CI fails above it. The number was previously "~60 MB" here, "approximately" and a `SHOULD` in `NFR-PERF-007`, and "roughly" and a `MUST` in `FR-CTR-002`; one threshold with one measurement and one strength replaces all three. Both stage sizes are still reported in the notes, with the command used.

### 2.3 `.dockerignore` (M6.1/6.2)

One per build context, excluding `.git`, `node_modules`, `.venv`, `__pycache__`, `.env`, `tests/fixtures/`, `*.pyc`, `.pytest_cache`, `.mypy_cache`, `dist/`, `coverage/`, and `docs/`. **`tests/fixtures/` as a path**, not "test fixtures" as a concept — a rule naming a concept cannot be checked.

**The measurement has a threshold, so it can fail:** context size before and after, from the `docker build --progress=plain` transfer line, and **the frontend context must shrink by at least 90 %** (`FR-CTR-003`). Reporting two numbers with no criterion meant nothing could be wrong.

**Report build-context size before and after, with numbers** (`FR-CTR-003`). Measure with `docker build` output or by `tar`-ing the context. This is 2 marks for two files and a measurement.

---

## 3. Topology

### 3.1 Three networks (`AD-002`, `FR-CTR-005`)

| Network | Members | Property |
|---|---|---|
| `edge` | frontend, backend | Bridge. Browser-facing traffic. |
| `internal` | backend, database, cache, ollama | **`internal: true`** — no route to the outside world |
| `egress` | backend | Bridge. The backend's outbound path to Groq. |

**The backend is the only service on more than one network.** The frontend is on `edge` only; the database, cache and Ollama are on `internal` only.

**Why three rather than two.** `internal: true` blocks outbound traffic, so a backend that must call Groq needs a network that permits egress. Putting that egress on `edge` would work — `edge` is a normal bridge — but it makes the outbound capability an accidental side effect of the browser-facing network. A named `egress` network states the intent, costs about six lines, and turns engineering-notes question 7 from an excuse into a design decision.

**Ollama sits on `internal` with no egress.** This works because the model weights are pulled once into the `ollama_models` volume as a documented setup step, not on every `up`.

**The deliverable is the failure.** `docker compose exec frontend ping database` must fail; capture it. The frontend is the internet-facing component and therefore the most likely to be compromised; it has no route to your data.

### 3.2 Three volumes (`FR-CTR-007`)

| Volume | Purpose | Justification (goes in the notes) |
|---|---|---|
| `pgdata` | PostgreSQL data directory | The durable one. Everything else can be rebuilt. |
| `redisdata` | AOF persistence | See M4 §2.6 — three of Redis's four jobs here are not caches. |
| `ollama_models` | Model weights | So `up` does not re-pull hundreds of megabytes, and so Ollama can live on a network with no egress. |

### 3.3 Dev bind mount (`FR-CTR-008`)

`compose.yaml` bind-mounts `backend/app` for hot reload. `compose.prod.yaml` does not.

The sentence for the notes: a bind mount replaces the image's contents with the host's, which is exactly what you want while iterating and exactly what destroys build-once-deploy-many in production — the image you tested is no longer the code that runs.

---

## 4. The two Compose files

### 4.1 `compose.yaml` (development)

Services: `frontend`, `backend`, `database`, `cache`, `ollama`.

Requirements (`FR-CTR-009`, `FR-CTR-010`):
- `build:` contexts for frontend and backend; pinned images for the rest.
- **Healthchecks on every service**, and `depends_on: { condition: service_healthy }` on dependants. The backend waits for a healthy database and cache; the frontend waits for a healthy backend.
- All credentials via `${...}` from `.env`. `.env.example` committed with placeholders; `.env` git-ignored and never in history (−20 if it is).
- `restart: unless-stopped`.
- Migrations and seed run as an explicit step, not from application startup (`BR-DATA-001`).
- Ollama behind a Compose profile so a default `up` does not require pulling a model — but documented so the offline path is one flag away.

### 4.2 `compose.prod.yaml` (`FR-CTR-011`)

- `image: ${IMAGE_TAG}` references only. **No `build:` key anywhere.**
- **No published port on `database` or `cache`** (−8 if there is).
- `deploy.resources` limits on every service (`NFR-OPS-005`).
- No bind mounts.

### 4.3 One-command quickstart (`FR-CTR-012`)

From a clean clone, one documented command brings up a running, **seeded** system. A README quickstart that does not work from a clean clone is −5, and the CI integration job runs the documented path precisely so that this cannot silently rot.

Test it the only way that works: clone into a fresh directory on a machine that has never run the project, and follow the README literally.

---

## 5. Invariants this module must not violate

| Rule | Deduction if violated |
|---|---|
| `BR-SEC-001` — frontend cannot reach the database **in Compose** | −8 |
| `BR-SEC-003` — no secret in the tree or in history | −20 |
| `BR-SEC-004` — no `localhost` service-to-service | −8 |
| `BR-SEC-005` — no published data ports in prod | −8 |
| `FR-CTR-004` — every image pinned | −8 |
| `FR-CTR-012` — quickstart works from a clean clone | −5 |

**`BR-SEC-001` is a Compose property and does not carry to Kubernetes.** There is no `NetworkPolicy` in `k8s/`, so every pod in the namespace can reach `postgres` directly; `ClusterIP`-only Services stop external exposure, not lateral movement. The deduction is assessed against the Compose topology, which is where the captured `ping` failure comes from. The gap, and the default-deny policy that would close it, are in `NFR-SEC-001`, `ADR-0005` and `docs/NON-GOALS.md` §2.

---

## 6. Tasks

| ID | Task | Size | Owner | Depends on | Delivers | Done when |
|---|---|---|---|---|---|---|
| **T-M6-001** | Backend Dockerfile: multi-stage, pinned `python:3.12-slim`, `USER 1000`, exec CMD, HEALTHCHECK on `/health`, cache-correct COPY order. **No `APP_VERSION` build arg** — it is a runtime environment variable (`AD-014`), or the image becomes commit-specific | M | Dev 2 | M2 T-M2-001 | FR-CTR-001 | `docker image inspect` shows a non-zero `User` and a healthcheck; a source-only rebuild prints `CACHED` on the dependency step; `grep -c ARG.*APP_VERSION Dockerfile` is 0 |
| T-M6-002 | `.dockerignore` for both contexts; context sizes measured before and after | S | Dev 2 | T-M6-001 | FR-CTR-003 | Two numbers recorded in the notes |
| **T-M6-003** | Frontend Dockerfile: node build stage, nginx serve stage, non-root, entrypoint, size reported | M | Dev 2 | M1 T-M1-002 | FR-CTR-002, NFR-PORT-002 | Final image has no Node; both stage sizes recorded |
| **T-M6-004** | `compose.yaml`: five services, three networks, three volumes, healthchecks, `service_healthy`, `.env` substitution, dev bind mount | **L** | Dev 2 | T-M6-001/003 | FR-CTR-005/007/008/009/010, AD-002 | `docker compose up` yields a working stack |
| **T-M6-005** | Network isolation proof captured | S | Dev 2 | T-M6-004 | BR-SEC-001, RUB-G-03 | `exec frontend ping database` fails; output in `docs/evidence/` |
| T-M6-006 | Migration + seed step wired into the Compose flow | S | Dev 2 | T-M6-004, M3 T-M3-005 | FR-CTR-012, BR-DATA-001 | `up` from empty yields a seeded database |
| T-M6-007 | `compose.prod.yaml`: `image: ${IMAGE_TAG}` only, no `build:`, no data ports, `restart: unless-stopped`, `APP_VERSION` from the environment, and `deploy.resources` per `AD-048`. **Limits also added to `compose.yaml`** — the brief lists resource limits under required Compose engineering, so the dev file needs them too | M | Dev 2 | T-M6-004 | FR-CTR-011 | Checker script passes; `grep -c 'build:'` in the prod file is 0; every service in both files has `deploy.resources.limits` |
| T-M6-008 | `.env.example` committed; `.env` git-ignored; history scanned clean | S | Dev 2 | T-M6-004 | BR-SEC-003 | Secret scan over full history returns nothing |
| T-M6-009 | Clean-clone quickstart verification | S | Dev 2 | T-M6-006 | FR-CTR-012, NFR-PORT-004 | Fresh clone in a fresh directory reaches a seeded system by following the README literally |
| T-M6-010 | Ollama service on `internal`; `ollama_models` volume; **`make pull-models`** target running `ollama pull` in a throwaway container on `egress` (`AD-046`); healthcheck fails naming the empty volume | M | Dev 2 | T-M6-004 | FR-CTR-007, M5 T-M5-009 | `make pull-models` populates the volume and is a no-op on a second run; `TRIAGE_PROVIDER=ollama` then classifies with no egress; with the volume empty the service reports a named failure rather than hanging |
| T-M6-011 | Volume and bind-mount justifications written into `ENGINEERING-NOTES.md` | S | Dev 2 | T-M6-007 | RUB-G-04, RUB-E-04 | Three volumes justified; dev-vs-prod bind mount explained |
| T-M6-012 | Engineering-notes Q1 (laptop vs CI runner) and Q7 (egress) drafted | S | Dev 2 | T-M6-004 | RUB-J-05 | Three differences, each with a file:line that freezes it |

---

## 7. Verification checklist for this module

Run before calling M6 done:

```
docker compose exec frontend ping -c1 database      # MUST fail
docker compose exec backend  ping -c1 database      # MUST succeed
docker run --rm <backend-image> id                  # non-root uid
docker image ls                                     # frontend ≤ ~60 MB
grep -rn "localhost" compose*.yaml k8s/ frontend/src/   # no hits for service-to-service
grep -c "build:" compose.prod.yaml                  # 0
docker compose -f compose.prod.yaml config | grep -A2 "database:" | grep ports   # no hits
```
