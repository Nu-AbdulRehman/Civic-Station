# Dev 2 task status

Tracks every task whose `Owner` is Dev 2 (or shared) in the design-doc task tables. Update the row
when a task's `Done when` condition is demonstrably true, not when the code merely exists.

**Last updated:** 2026-09-27, on `feat/T-M6-001-containers-compose`.

Legend: **Done** = `Done when` verified · **Built** = in the tree, verification step still owed ·
**Partial** = some of the task exists · **Todo** = not started · **?** = cannot be checked from
the repository (GitHub settings); confirm by hand.

## Summary

| Package | Tasks | State |
|---|---|---|
| P1 governance | T-M11-001, T-M8-001 | ? (branch protection lives in GitHub settings; screenshot not in `docs/evidence/`) |
| P2 backend image | T-M6-001/002 | **Done** |
| P3 frontend image | T-M6-003 | **Done** |
| P4 Compose | T-M6-004/005/006 | **Done** |
| P5 prod Compose, env hygiene | T-M6-007/008/009 | Built — clean-clone run and full-history secret scan owed |
| P6 CI lint + tests | T-M8-002/003/004 | **Done** (on `dev`) |
| P7 red/green evidence | T-M8-013 | Todo |
| P8 CI build/scan/manifests | T-M8-005/006/007 | Built — `build`/`scan` now have Dockerfiles to act on; `manifests` waits for `k8s/` |
| P9 Ollama + volume notes | T-M6-010/011 | T-M6-011 **Done**; T-M6-010 Built, not run (needs the model pull) |
| P10 CI integration | T-M8-008 | Built — first real run happens on this branch's PR |
| P11–P15 Kubernetes | T-M7-001…011, T-M9-002 | Todo |
| P16–P18 CD, release | T-M8-009…012 | Todo (T-M8-012 partial: `ci.yml` has `permissions: contents: read`, actions pinned by tag, not SHA) |
| P19–P21 load, VPA, demos | T-M9-001…008, T-M7-012/013, T-M3-009, T-M4-008 (k8s part)/009/010 | T-M4-009 **Done**; rest Todo |
| P22 check_submission §5.3 | T-M8-014 | Todo (only the M2 layer checks exist) |
| P23 zero-downtime | T-M9-009 | Todo |
| P24 runbook + notes | T-M10-005, T-M6-012, T-M8-015, T-M7-014 | Todo |
| P25 evidence audit | T-M10-009 | Todo |

## M6 — containers (`07-M6-containers.md`)

| ID | State | Evidence / what is left |
|---|---|---|
| T-M6-001 | **Done** | `backend/Dockerfile`. Image user `1000`, healthcheck on `/health`, source-only rebuild prints `CACHED` on `uv sync`, no `ARG APP_VERSION` |
| T-M6-002 | **Done** | Both `.dockerignore` files; frontend context 139.51 MB → 284.89 kB, backend 195 MB → 397.70 kB (`ENGINEERING-NOTES.md`) |
| T-M6-003 | **Done** | `frontend/Dockerfile`; user `101`, port 8080, no Node in final image, ~15.3 MB unpacked, build stage ~386 MB. Base changed to `nginx:1.30.5-alpine3.24-slim` (`AD-063`) |
| T-M6-004 | **Done** | `compose.yaml`; `docker compose up -d --build --wait` reaches all-healthy; POST/GET/stats MISS→HIT work through nginx |
| T-M6-005 | **Done** | `docs/evidence/network-isolation.txt` (`ping: bad address 'database'`) |
| T-M6-006 | **Done** | One-shot `migrate` service; empty volumes → 30 seeded rows, backend waits on `service_completed_successfully` |
| T-M6-007 | Built | `compose.prod.yaml` validates (`docker compose config`), 0 `build:`, no data ports, limits on every service in both files. Owed: a run with real SHA-tagged images once `cd.yml` pushes them; "checker script passes" needs T-M8-014's detectors |
| T-M6-008 | Built | `.env.example` committed with placeholders; `.env` ignored. Owed: full-history secret scan (`git log -p` over `gsk_`, passwords) — belongs in T-M8-014 |
| T-M6-009 | Todo | Clone into a fresh directory after merge, follow README literally |
| T-M6-010 | Built | `ollama` (profile `ollama`, `internal` only), `ollama-pull` (profile `pull`, `egress`), `make pull-models`. Not yet run: pull, second-run no-op, empty-volume healthcheck message, `TRIAGE_PROVIDER=ollama` classification |
| T-M6-011 | **Done** | `ENGINEERING-NOTES.md` "Images, volumes and bind mounts" |
| T-M6-012 | Todo | Notes Q1 and Q7 |

## M4 — cache (Dev 2 rows, `05-M4-cache.md`)

| ID | State | Evidence / what is left |
|---|---|---|
| T-M4-008 | Partial | AOF + `redisdata` in both Compose files (`CONFIG GET appendonly` → `yes`); k8s manifest part waits for M7 |
| T-M4-009 | **Done** | `ENGINEERING-NOTES.md`, `redisdata` paragraph |
| T-M4-010 | Todo | Needs 4 backend replicas on the cluster |

## M7 — Kubernetes (`08-M7-kubernetes.md`)

T-M7-001 … T-M7-014: all **Todo**. No `k8s/` directory exists yet.

## M8 — CI/CD (`09-M8-cicd.md`)

| ID | State | Evidence / what is left |
|---|---|---|
| T-M8-001 | ? | Confirm protection on `main` in GitHub; add the screenshot to `docs/evidence/` |
| T-M8-002…004 | **Done** | `.github/workflows/ci.yml` on `dev` |
| T-M8-005 | Built | `build` job; now builds both Dockerfiles and enforces the 60 MB gate |
| T-M8-006 | Built | `scan` job; both images scan clean locally with Trivy 0.56.2 (`--ignore-unfixed`, HIGH/CRITICAL) |
| T-M8-007 | Built | `manifests` job skips until `k8s/overlays/prod/kustomization.yaml` exists |
| T-M8-008 | Built | `integration` job; every step it runs was reproduced locally against `compose.yaml` |
| T-M8-009…011 | Todo | `cd.yml`, `release.yml` |
| T-M8-012 | Partial | Actions pinned by tag (`@v4`), not by commit SHA |
| T-M8-013 | Todo | Red-then-green merge-block evidence |
| T-M8-014 | Todo | §5.3 detectors in `scripts/check_submission.py` |
| T-M8-015 | Todo | Notes Q2 |

## M9 — load and evidence (`10-M9-load-evidence.md`)

T-M9-001 … T-M9-009: all **Todo** (need the cluster).

## M10 / M11 — docs and process (Dev 2 or shared)

| ID | State |
|---|---|
| T-M10-003 README quickstart from a fresh clone (`make up`) | Built — quickstart section written; fresh-clone run owed |
| T-M10-005 `RUNBOOK.md` | Todo |
| T-M10-009 evidence audit | Todo |
| T-M11-001 repo setup, protection, labels | ? |
| Shared (T-M10-001/006/007/008/010…013, T-M11-002…009) | Ongoing / Todo |

## Dev 1 checks that need Dev 2's services (handoff §6)

| Check | State |
|---|---|
| Migrate + seed in Compose | **Done** (30 rows after `up` from empty) |
| SIGTERM drain (T-M2-012) | Todo — note the dev backend runs `--reload`; test against the prod-style command |
| Ollama with no egress (T-M5-009) | Todo — needs `make pull-models` |
| Ollama numbers for `docs/TRIAGE.md` | Todo |
| One image, two environments (FR-FE-014) | Todo — needs k3d |
| Distributed limiter (T-M4-010, T-M9-008) | Todo — needs k3d |
| Screenshots through nginx (optional) | Todo |
