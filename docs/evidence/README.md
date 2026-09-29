# Evidence index

Each file here is a capture from a real run, named after what it proves. This index maps the
brief's rubric lines (§4) and submission items (§5.8) to the file that backs them. Commands that
regenerate a capture are in the file itself or in the script named.

## Collaboration and CI/CD (rubric A, I)

| Claim | File |
|---|---|
| `main` protected: PR, approval, eight required checks | `main-branch-protection-1.png`, `main-branch-protection-2.png` |
| A red pipeline blocks the merge, then green allows it | `blocked-merge-red.png`, `blocked-merge-green.png` |
| Deliberate merge conflict: markers, resolution, why | `merge-conflict.md` |
| CD deploy fails closed and rolls back (`force_smoke_failure`) | `cd-forced-rollback.png` |
| The deploy job's steps, rehearsed on a local cluster | `cd-local-rehearsal.txt` |

## Frontend (rubric B)

| Claim | File |
|---|---|
| Submit, Dashboard and Stats views, both themes | `ui-{submit,dashboard,stats}-{light,dark}.png` |
| The server's 409 message shown verbatim | `dashboard.png` |
| Stats `X-Cache` HIT shown in the UI | `stats.png`, `ui-stats-*.png` |
| One image runs in any environment (runtime config) | `one-image-two-environments.txt` |

## Backend, data, cache (rubric C, D, E)

| Claim | File |
|---|---|
| SIGTERM: an in-flight request drains before exit | `sigterm-drain.txt` |
| Data survives `docker compose down` / `up` | `compose-persistence.txt` |
| Data survives deleting `postgres-0` | `k8s-postgres-persistence.txt` |
| Distributed rate limiter: 4 replicas, exactly 10 × 201 and 20 × 429 | `ratelimit-multireplica.txt` |

## AI layer (rubric F)

| Claim | File |
|---|---|
| Provider measurements behind `docs/TRIAGE.md` | `triage-{rules,simulated,groq-*}.json` |
| Ollama works with no internet access; named failure on an empty volume | `ollama-offline.txt` |

## Docker and Compose (rubric G)

| Claim | File |
|---|---|
| The frontend cannot reach the database (`ping` fails) | `network-isolation.txt` |
| One-command quickstart from a clean clone | `clean-clone-quickstart.txt` |

## Kubernetes and scaling (rubric H, bonus)

| Claim | File |
|---|---|
| Probes: database down, pods leave the Service, no restarts | `k8s-probes.txt` |
| Rolling update with no failed requests | `k8s-rollout.txt` |
| `kubectl get hpa -w`, timestamped (§5.8 item 6) | `run1-hpa-watch.txt` (run 2: `run2-hpa-watch.txt`) |
| Replicas against load, the chart (§5.8 item 6) | `run1-replicas-vs-load.png` (run 2: `run2-replicas-vs-load.png`) |
| Chart inputs, regenerable with `scripts/plot_scaling.py --from-csv` | `run*-k6-timeseries.csv`, `run*-scaling.csv`, `run*-k6-summary.json` |
| VPA recommendations, requests updated, re-run compared | `vpa-recommendation.txt` (the request change is its own commit in `k8s/base/backend.yaml`) |
| Zero-downtime rollout under live load (bonus) | `zero-downtime-rollout.txt` |
| Rollback timing, both mechanisms | `rollback-timing-prod-limits.txt` (dev-overlay limits: `rollback-timing.txt`) |

`run1` used the original CPU request (100m), `run2` the VPA-guided one (182m); the design's
manifest names `hpa-watch.txt` and `replicas-vs-load.png`, and `run1-*` are those files.
