# Dev 2 task status

Tracks every task whose `Owner` is Dev 2 (or shared) in the design-doc task tables. Update the row
when a task's `Done when` condition is demonstrably true, not when the code merely exists.

**Last updated:** 2026-09-28, on `feat/T-M9-001-load-scaling`.

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
| P5 prod Compose, env hygiene | T-M6-007/008/009 | **Done** — clean clone reaches a seeded stack; history secret scan clean |
| P6 CI lint + tests | T-M8-002/003/004 | **Done** (on `dev`) |
| P7 red/green evidence | T-M8-013 | Todo |
| P8 CI build/scan/manifests | T-M8-005/006/007 | Built — `build`/`scan` now have Dockerfiles to act on; `manifests` waits for `k8s/` |
| P9 Ollama + volume notes | T-M6-010/011 | **Done** |
| P10 CI integration | T-M8-008 | Built — first real run happens on this branch's PR |
| P11–P15 Kubernetes | T-M7-001…011, T-M9-002 | **Done** on local k3d |
| P16–P18 CD, release | T-M8-009…012 | Built — `cd.yml`, `release.yml`; deploy path rehearsed locally on k3d. Owed: a green run on `main` (needs the `GROQ_API_KEY` repository secret) and one forced-failure run |
| P19–P21 load, VPA, demos | T-M9-001…008, T-M7-012/013, T-M3-009, T-M4-008 (k8s part)/009/010 | **Done**, except the write-ups (T-M9-005 lag = Dev 1, T-M9-007 / notes Q6) |
| P22 check_submission §5.3 | T-M8-014 | **Done** — 9 checks, 0 findings; each detector has a planted-violation test that goes red with the detector disabled |
| P23 zero-downtime | T-M9-009 | **Done** — 13,456 requests, 0 failed |
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
| T-M6-007 | Built | `compose.prod.yaml` validates, 0 `build:`, no data ports, limits everywhere, checker passes (`check_compose_prod`). Owed only: a run with real GHCR images after the first CD push |
| T-M6-008 | **Done** | `check_secrets` scans the tree and `git log -p --all`: clean |
| T-M6-009 | **Done** | `docs/evidence/clean-clone-quickstart.txt` (warm Docker cache caveat stated there) |
| T-M6-010 | **Done** | `docs/evidence/ollama-offline.txt`: empty volume → named healthcheck failure; `make pull-models` 554 s, re-run no-op 3 s; `llm:ollama` triage with no route out (~20 s on CPU) |
| T-M6-011 | **Done** | `ENGINEERING-NOTES.md` "Images, volumes and bind mounts" |
| T-M6-012 | Todo | Notes Q1 and Q7 |

## M4 — cache (Dev 2 rows, `05-M4-cache.md`)

| ID | State | Evidence / what is left |
|---|---|---|
| T-M4-008 | **Done** | AOF + `redisdata` in both Compose files and `k8s/base/redis.yaml` (PVC) |
| T-M4-009 | **Done** | `ENGINEERING-NOTES.md`, `redisdata` paragraph |
| T-M4-010 | **Done** | `docs/evidence/ratelimit-multireplica.txt`: 10 × 201, 20 × 429 with `Retry-After`, 4 pods; needed `AD-068` |
| T-M3-009 | **Done** | `docs/evidence/compose-persistence.txt` (down/up keeps rows) and `k8s-postgres-persistence.txt` (pod delete) |

## M7 — Kubernetes (`08-M7-kubernetes.md`)

| ID | State | Evidence / what is left |
|---|---|---|
| T-M7-001 | **Done** | `scripts/k3d-up.sh`; k3s bundles metrics-server, `kubectl top nodes` returns data |
| T-M7-002 | **Done** | `k8s/base/`; all pods Running, postgres is a StatefulSet with `volumeClaimTemplates` |
| T-M7-003 | **Done** | ConfigMap via `configMapGenerator`; `secret.example.yaml` placeholders only, not applied (`AD-064`) |
| T-M7-004 | **Done** | `docs/evidence/k8s-probes.txt`: postgres down, pods leave endpoints, 0 restarts |
| T-M7-005 | **Done** | `AD-048` values on every container, incl. the init container; guesses recorded in `AD-048` |
| T-M7-006 | **Done** | Ingress `civic-station.localhost`: `/` and `/api` both 200 with the `Host` header |
| T-M7-007 | **Done** | `migrate` init container; fresh cluster came up migrated; choice justified in the notes |
| T-M7-008 | **Done** | `kubectl get hpa` shows `cpu: 6%/60%` |
| T-M7-009 | **Done** | `docs/evidence/vpa-recommendation.txt`: Target 182m / 250Mi after load |
| T-M7-010 | **Done** | `docs/evidence/k8s-rollout.txt`: 444/444 requests 200 during `rollout restart` |
| T-M7-011 | **Done** | Both overlays build and pass `kubeconform -strict`; 0 `:latest` |
| T-M7-012 | **Done** | `docs/evidence/k8s-postgres-persistence.txt` |
| T-M7-013 | **Done** | Prod limits: undo 22.3–24.5 s (bound 30 s), re-apply 22.5–25.2 s (`rollback-timing-prod-limits.txt`). The dev overlay's halved CPU limit gave 36–39 s (`rollback-timing.txt`) |
| T-M7-014 | Todo | Notes Q6 |

## M8 — CI/CD (`09-M8-cicd.md`)

| ID | State | Evidence / what is left |
|---|---|---|
| T-M8-001 | ? | Confirm protection on `main` in GitHub; add the screenshot to `docs/evidence/` |
| T-M8-002…004 | **Done** | `.github/workflows/ci.yml` on `dev` |
| T-M8-005 | Built | `build` job; now builds both Dockerfiles and enforces the 60 MB gate |
| T-M8-006 | Built | `scan` job; both images scan clean locally with Trivy 0.56.2 (`--ignore-unfixed`, HIGH/CRITICAL) |
| T-M8-007 | Built | `manifests` job now validates both overlays with kubeconform (VPA schema from the pinned CRDs catalog) and fails on `:latest`; first CI run on this branch's PR |
| T-M8-008 | Built | `integration` job; every step it runs was reproduced locally against `compose.yaml` |
| T-M8-009 | Built | `cd.yml` `test` (reusable `ci.yml`) → `build-push` (GHCR `:<sha>` + `:latest`, SPDX SBOM artifacts 90 days, digest outputs). Owed: first run on `main` |
| T-M8-010 | Built | `deploy-k8s`: k3d in runner, baseline = previous `main` commit, new SHA over it, Ingress smoke (exact `triaged_by`), `get hpa`, `rollout undo` on failure (`AD-065`). Rehearsed locally: `docs/evidence/cd-local-rehearsal.txt`. Owed: the green run link (submission item 2) and a `force_smoke_failure` run |
| T-M8-011 | Built | `release.yml` on `v*`: `needs: test`, semver + SHA images, SBOMs attached, generated notes. Owed: one test tag |
| T-M8-012 | **Done** (baseline) | `permissions:` per workflow and per job (`packages: write` only on publishing jobs, `contents: write` only on release). Actions pinned by major tag, which meets `FR-CICD-011`; SHA pinning is the bonus |
| T-M8-013 | Todo | Red-then-green merge-block evidence |
| T-M8-014 | **Done** | `scripts/check_submission.py` + `backend/tests/unit/test_check_submission_infra.py` (26 tests); `AD-066` scope |
| T-M8-015 | Todo | Notes Q2 |

## M9 — load and evidence (`10-M9-load-evidence.md`)

| ID | State | Evidence / what is left |
|---|---|---|
| T-M9-001 | **Done** | `load/k6-script.js`; CPU well above 60 % on the plateau (run 1: 120–220 % of request) |
| T-M9-002 | **Done** | k3s bundles metrics-server; `kubectl top pods` returns data |
| T-M9-003 | **Done** | `run1-hpa-watch.txt` / `run1-scaling.csv`: 2 → 10 → 2, timestamped, back to 2 ~5 min after load |
| T-M9-004 | **Done** | `scripts/plot_scaling.py` → `run1-/run2-replicas-vs-load.png`, regenerable from the committed CSVs (`AD-067`) |
| T-M9-005 | Todo (Dev 1) | Lag write-up; numbers ready: replicas rise 34 s after load, Ready capacity 44 s (run 1) |
| T-M9-006 | **Done** | `vpa-recommendation.txt`; requests 100m → 182m in `k8s/base/backend.yaml` (own commit); run 2 compared |
| T-M9-007 | Todo | Notes Q6 write-up |
| T-M9-008 | **Done** | See T-M4-010 |
| T-M9-009 | **Done** | `zero-downtime-rollout.txt`: 13,456 attempted, 0 failed, during `set image` with HPA scaling 4 → 7 |

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
| SIGTERM drain (T-M2-012) | **Done** — `docs/evidence/sigterm-drain.txt`: POST in flight answered 201 at 10.7 s, exit 0 |
| Ollama with no egress (T-M5-009) | **Done** — `docs/evidence/ollama-offline.txt` |
| Ollama numbers for `docs/TRIAGE.md` | Todo |
| One image, two environments (FR-FE-014) | **Done** — `docs/evidence/one-image-two-environments.txt`: same config digest in Compose and k3d; address read at start |
| Distributed limiter (T-M4-010, T-M9-008) | **Done** |
| Screenshots through nginx (optional) | Todo |
