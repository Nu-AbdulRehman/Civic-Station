# Engineering notes

The eight §5.2 answers come first; the topic sections after them hold the longer measurements
they cite. Every claim names a file and line in this repository, or a file under
`docs/evidence/` that a reader can open. Line numbers are as of the commit that adds this section.

---

## The eight questions (§5.2)

### Q1. Three things that differ between a laptop and a CI runner, and the line that freezes each

1. **The Python interpreter.** This laptop is Windows with Python 3.14 on the `PATH`; the runner
   is `ubuntu-24.04` (`.github/workflows/ci.yml:22`). The difference bit us for real: `uv` picked
   3.14 for `scripts/plot_scaling.py`, found no matplotlib wheel for it, and hung on a source build
   (`docs/failure-log.md`, 2026-09-28). The image does not care what the host has:
   `backend/Dockerfile:8` and `:16` pin `FROM python:3.12.14-slim-bookworm`, and `backend/uv.lock:3`
   pins `requires-python = "==3.12.*"`.
2. **Dependency versions.** A laptop accumulates whatever was last installed. The image installs
   exactly the lock file, or fails: `backend/Dockerfile:14` runs `uv sync --frozen`, and
   `frontend/Dockerfile:9` runs `npm ci`, which refuses a `package-lock.json` that disagrees with
   `package.json`.
3. **Configuration and credentials.** The laptop has a `.env` with a real `GROQ_API_KEY`; CI has
   no key and must give the same answer every run. `.github/workflows/ci.yml:111` sets
   `TRIAGE_PROVIDER: simulated` for the integration tests, and the service containers are pinned at
   `.github/workflows/ci.yml:70` (`postgres:16.4-alpine`) and `:79` (`redis:7.4-alpine`), so a test
   never depends on what happens to be running on the host.

A fourth, found late: **CPU count.** Docker on this laptop sees 12 CPUs, a hosted runner 4.
Resource limits in `compose.yaml` (every service's `deploy.resources`) make the stack behave the
same on both. They are also how a too-tight Ollama limit made every triage time out until it was
raised (`compose.yaml`, `ollama` service; `docs/failure-log.md`, 2026-09-29).

### Q2. Where the pipeline sits on the CI/CD maturity ladder, and the next rung

**Continuous deployment to a disposable environment, with automated verification and rollback.**
Every pull request runs eight required checks (`.github/workflows/ci.yml`: lint and types, both
test suites, image build, Trivy scan, kubeconform, a Compose integration run, and
`check_submission.py`). Every merge to `main` re-runs them, publishes both images to GHCR by commit
SHA, deploys that SHA to a Kubernetes cluster created inside the runner, smoke-tests it through the
Ingress, and rolls back automatically if the smoke test fails (`.github/workflows/cd.yml`,
`AD-065`; `docs/evidence/cd-forced-rollback.png`). Nothing is deployed by hand.

It is not the top rung, for two reasons that can be stated exactly. The cluster is thrown away at
the end of the job, so no long-lived environment ever runs the SHA; and images are scanned but not
signed (ADR-0003, `docs/NON-GOALS.md` §5).

**The next rung is GitOps continuous deployment to a persistent cluster:** Argo CD or Flux
watching `k8s/overlays/prod`, with the pipeline only committing the new SHA. What it buys: the
cluster converges on the repository by itself, drift is detected and reverted, and a rollback is a
`git revert` whose history is the audit log. Deploying by digest with Cosign verification would
close the signing gap at the same time.

### Q3. The line that guarantees build-once-deploy-many, and what breaks without it

`frontend/entrypoint.sh:21`:

```sh
envsubst '${BACKEND_ORIGIN}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/conf.d/default.conf
```

The backend's address enters the frontend when the container **starts**, not when the image is
built. The same image digest runs in Compose and on the cluster; only the environment differs
(`docs/evidence/one-image-two-environments.txt` shows one config digest in both places, and the
rendered `proxy_pass` changing with `BACKEND_ORIGIN`). The backend's counterpart is `APP_VERSION`,
read from the environment at runtime and deliberately not a build argument
(`backend/Dockerfile:3`, `AD-014`).

Without it, Vite would bake an API URL into the JavaScript at build time. Every environment would
need its own build, the image tested in CI would not be the image deployed, and rolling back to the
previous image would stop being a meaningful operation, because that image might point at the
wrong backend.

### Q4. What "correct" means for a probabilistic component, and how CI stays deterministic

Whether the model's answer is right cannot be checked by a test; everything around it can. For
this system, correct means:

- **Well-formed or rejected.** Every provider's output is parsed into `TriageResult`
  (`backend/app/domain/models.py:30`): a category and a priority from the closed enums, and a
  summary of bounded length. The pipeline validates again whatever a provider returns
  (`backend/app/providers/triage/pipeline.py:147`, `AD-060`). Malformed output is never repaired;
  it goes to the rules fallback.
- **Always answered.** A valid complaint gets a `201` whatever the provider does. Timeout, 429,
  5xx, bad JSON and injection attempts all end in the rules classifier with
  `triaged_by = "rules:fallback"` (`backend/app/providers/triage/pipeline.py:78`). Here correctness
  is a property of the system, not of the model.
- **Measured, not assumed.** Agreement between providers and the fallback rate are measured
  offline and reported with dates (`docs/TRIAGE.md` §5–§7).

CI is deterministic because it never calls a model. `.github/workflows/ci.yml:111` selects
`SimulatedTriage`, whose output is a pure function of its input: it seeds a random generator from a
SHA-256 of the text (`backend/app/providers/triage/simulated.py:34`), because Python's `hash()` is
salted per process. Its failure modes (`raise`, `malformed`, `slow`) let the tests drive every
fallback path on demand, with no network and no real clock.

### Q5. HPA lag: how many seconds, where the time went, and what would reduce it

**34 seconds from offered load rising to the HPA asking for more replicas, and 44 seconds until
the new pods were Ready to serve** (run 1, CPU request 100m). Both numbers come from two committed
files: `docs/evidence/run1-k6-timeseries.csv` (k6 starts at t = 1 s and reaches 40 virtual users at
t = 61 s) and `docs/evidence/run1-scaling.csv` (5-second samples of the HPA and the Deployment).
`uv run scripts/plot_scaling.py --from-csv docs/evidence/run1-k6-timeseries.csv
docs/evidence/run1-scaling.csv <prefix>` recomputes them. After the VPA-guided request change
(run 2, 182m), the same load gave 50 s and 78 s.

| Stage | Seconds | Evidence |
|---|---|---|
| Load arrives and CPU rises, but no metric shows it yet | ~34 | The first sample with CPU above the 60 % target (176 %) is at t = 35 s, and desired replicas rose in that same sample |
| Scheduling, container start, the migrate init container, the startup probe | ~10 | Current and Ready replicas rise at t = 45 s |
| Reaching full capacity (10 Ready pods) | +111 | t = 156 s |

The first stage is the metrics pipeline. metrics-server samples usage on an interval, the HPA
controller evaluates on its own period (15 s by default), and usage is averaged, so a step change
takes two or three cycles to become a decision. The chart (`docs/evidence/run1-replicas-vs-load.png`)
shows the second stage as the gap between the red (desired) and green (Ready) lines: a pod counts as
a replica before it can serve.

What would reduce it: a shorter metrics-server resolution and HPA sync period, at the cost of more
API-server load; a faster pod start, for example running migrations once as a pre-rollout Job
instead of in every pod's init container (`k8s/base/backend.yaml`, the `migrate` init container;
`08-M7` §2.1); and, for load that can be predicted, a higher `minReplicas`, so the capacity is
already there. Only the last one removes the lag rather than shortening it.

### Q6. Why the VPA is in `Off` mode

`k8s/base/vpa.yaml:9` sets `updateMode: "Off"`: the VPA recommends and a person decides.

The HPA scales on CPU utilisation, which is usage divided by the CPU request
(`k8s/base/hpa.yaml:14`, target 60 %). In `Auto` mode the VPA changes that same request, by evicting
and recreating pods, so the two controllers act on one signal. Under load the VPA raises the
request; the HPA's computed utilisation falls; the HPA scales in; per-pod usage rises; the VPA
raises the request again. Every eviction also removes capacity during the very load that caused it.

This repository shows the coupling directly. After run 1 the VPA recommended 182m against the 100m
guess (`docs/evidence/vpa-recommendation.txt`), and the request was changed by hand
(`k8s/base/backend.yaml:85`, in a commit of its own). Run 2 offered the same load. Utilisation under
load fell from 120–220 % of the request to 70–130 %, and the HPA scaled later and in smaller steps:
first rise at 50 s instead of 34 s, desired replicas 2 → 4 → 5 → 6 → 7 → 10 instead of
2 → 6 → 8 → 10. One request change, made deliberately, visibly changed the HPA's behaviour. In
`Auto` mode that change would happen continuously and unobserved, in the middle of the load.

### Q7. `internal: true` blocks outbound traffic: where does that leave the LLM call?

`compose.yaml:160` makes the `internal` network egress-free, and PostgreSQL, Redis and Ollama sit
only on it (`compose.yaml:81`, `:98`, `:116`). The backend must still reach Groq, so it is the only
service on three networks (`compose.yaml:48`): `edge` to the frontend, `internal` to the data
services, and a separate `egress` bridge (`compose.yaml:161`) for outbound calls (`AD-002`,
ADR-0005).

Putting egress on `edge` would also have worked, since `edge` is an ordinary bridge. But then the
backend's ability to call the internet would be a side effect of the network the browser traffic
uses. A network named `egress` states the intent, for six lines of YAML.

Ollama has no egress at all, so it cannot download its own model. The weights arrive once, through
a throwaway container on `egress` that writes into the `ollama_models` volume
(`compose.yaml:152`, `make pull-models`, `AD-046`). `docs/evidence/ollama-offline.txt` shows an
outbound attempt from the Ollama container failing with `Network is unreachable` while triage
through it succeeds. On Kubernetes there is no `NetworkPolicy`, so this segmentation does not carry
over (`docs/NON-GOALS.md` §2).

### Q8. The failure

**Symptom.** With `TRIAGE_PROVIDER=ollama`, the Ollama container healthy, and `/api/version`
reporting `llm:ollama`, every complaint still came back `triaged_by: rules:fallback`. The backend
logged `triage.retry` and then `triage.fallback`, both with `error_class: Timeout`. It spanned two
working sessions.

**What we wrongly believed first.** That the model was still loading. On the first day one
complaint in three succeeded, at about 20 s, which looked like a cold model warming up, and that
explanation was written into `docs/evidence/ollama-offline.txt`.

**What told us the truth.** Two commands. `docker exec civic-station-ollama-1 ollama ps` showed the
model fully loaded (`100% CPU`), so it was not loading. Then a timed request from the backend
container straight to `http://ollama:11434/api/chat`, reading Ollama's own counters:

```
call 1: 9.7s  prompt_eval 272 tok in 2.0s, gen 38 tok in 7.4s, load 0.0s
```

Thirty-eight tokens in 7.4 seconds is about five tokens a second, against a 10-second
`TRIAGE_TIMEOUT_SECONDS`, and `load 0.0s` ruled out loading on the spot. `docker stats` showed
Ollama pinned at 118 % CPU: `compose.yaml` capped the service at `cpus: "2.0"` on a 12-CPU machine.
`docker update --cpus 4` brought a call down to 3.5 s. The limit is now 4 (`compose.yaml`, `ollama`
service), and four complaints in a row were triaged by `llm:ollama` in about 4 s. The lesson: read
the provider's own timing before theorising about it. Full entry: `docs/failure-log.md`,
2026-09-29. A second failure found by measurement, the rate limiter split per node by kube-proxy
SNAT, is in the same log (2026-09-28, `AD-068`).

---

## Indexes and the queries they serve (`FR-DATA-003`, `BR-DATA-006`, `AD-049`, T-M3-008)

Every list request is built in one place,
`backend/app/repositories/complaints.py:68-83`: optional equality filters on `category`,
`priority` and `status` (`:68-76`), always ordered `created_at DESC, id DESC` (`:81`, `AD-016`),
then `LIMIT/OFFSET` (`:82-83`). The three indexes are created in revision `0001`
(`backend/alembic/versions/0001_create_complaints.py:85-102`) and mirrored in the ORM model
(`backend/app/db/models.py:60-67`) so that `alembic check` reports no drift.

| Index | Columns | Query it serves |
|---|---|---|
| `ix_complaints_created_at_id` (`0001_create_complaints.py:86`) | `created_at DESC, id DESC` | The unfiltered Dashboard listing: `ORDER BY created_at DESC, id DESC LIMIT :n OFFSET :m`. Both columns, because the `id` tie-break is what keeps pagination stable when rows share a timestamp; the seed deliberately creates such a pair (`backend/seeds/complaints.py`, third and fourth rows). |
| `ix_complaints_status_priority_created` (`:92`) | `status, priority, created_at DESC` | The operations filter: `WHERE status = :s AND priority = :p ORDER BY created_at DESC`. Carries `created_at`, so a filtered page is one index scan rather than a scan plus a sort. |
| `ix_complaints_category_created` (`:98`) | `category, created_at DESC` | The category filter: `WHERE category = :c ORDER BY created_at DESC`. |

**Evidence, not assertion.** `backend/tests/integration/test_schema.py:134` runs `EXPLAIN` on
each named query and asserts that its index appears in the plan and that no `Sort` node does;
`:146` asserts all three exist by name, which guards against a migration being reverted.

**A known limit, left visible.** The API always adds the `id` tie-break, including on filtered
lists. For the two filtered indexes, which do not carry `id`, PostgreSQL then adds an
*Incremental Sort* over rows that share a `created_at` (observed with `EXPLAIN` on 2026-09-26:
`Presorted Key: created_at`). Only equal-timestamp runs are sorted, so the cost is small, but
`AD-049`'s "no sort" holds only for the queries as `04-M3-data.md` §2.2 names them, not for
the exact SQL the repository issues. The fix is `id DESC` as a trailing column on both
filtered indexes; it changes `AD-049` and is therefore a decision for both developers rather
than a silent edit.

---

## Images, volumes and bind mounts (`FR-CTR-001…003`, `FR-CTR-007/008`, T-M6-002/003/011, T-M4-009)

### Image and build-context measurements (2026-09-27, Docker 29.7.2)

| Measurement | Before | After | Command |
|---|---|---|---|
| Frontend build context | 139.51 MB | 284.89 kB (−99.8 %, gate is −90 %) | `docker build --progress=plain frontend`, "transferring context" line, with and without `frontend/.dockerignore` |
| Backend build context | 195 MB on disk (mostly `.venv`) | 397.70 kB | same, `backend/.dockerignore`; "before" from `du -sh backend` |
| Frontend build stage (Node) | — | ~386 MB unpacked | `docker build --target build`, sum of `docker history` layers |
| Frontend final image (nginx) | — | ~15.3 MB unpacked (gate 60 MB) | sum of `docker history civic-station-frontend:dev` layers |
| Backend final image | — | ~272 MB unpacked, 77 MB compressed | `docker history` / `docker image inspect -f '{{.Size}}'` (containerd store reports compressed) |

A source-only change to `backend/app/` rebuilds with the `uv sync` step reported `CACHED`
(`backend/Dockerfile:13-14` copies the manifests before the source), so dependencies are not
reinstalled. The final frontend image contains no `node` binary and no `node_modules`
(`which node` in the image prints nothing).

### Why each volume exists

- **`pgdata`** (`compose.yaml`, `database` service) is the only state that cannot be rebuilt.
  Every complaint and every status change lives there; losing it is losing the product.
- **`redisdata`** holds Redis's append-only file (`--appendonly yes` in the `cache` command). It
  is tempting to call Redis "just a cache" and let it be ephemeral, but only one of its four jobs
  here is a cache in the throwaway sense (the stats snapshot). The rate-limit counters are
  enforcement state: a Redis restart that loses them hands every client a fresh window, which
  is a free burst to anyone who can trigger or wait out a restart. The triage cache saves paid
  model calls for 24 h, and `cs:outcomes` is the evidence behind the provider-reliability
  numbers. AOF on a volume costs one line and one volume; losing those three on every restart
  costs money and correctness.
- **`ollama_models`** holds model weights (hundreds of MB). Without it, every `up` would pull
  them again; more importantly, Ollama sits on the `internal` network with no route out, so it
  *cannot* pull. The weights arrive once through `make pull-models`, a throwaway container on
  `egress` writing into this volume (`AD-046`).

### Bind mount in development, none in production

`compose.yaml` bind-mounts `./backend/app` over `/app/app` and runs uvicorn with `--reload`, so
an edit on the host is live in the container within a second. `compose.prod.yaml` has no bind
mount and no `build:` key. A bind mount replaces the image's contents with whatever is on the
host, which is exactly what you want while iterating and exactly what destroys
build-once-deploy-many in production: the image that was tested is no longer the code that
runs. Production runs the SHA-tagged image and nothing else (`AD-062`).

---

## Kubernetes manifests (`FR-K8S-001…014`, T-M7-001…013)

Layout is `k8s/base/` plus `k8s/overlays/{dev,prod}` (`AD-011`). The namespace is `civic-station`,
the RFC 1123 form of the product name: the brief's `Civic-Station` is rejected by Kubernetes
(`AD-030`). `scripts/k3d-up.sh` builds a local cluster (1 server, 2 agents) with k3s's bundled
Traefik and metrics-server, installs the VPA recommender, creates the Secret once, imports the
`:dev` images and applies the dev overlay.

**Why PostgreSQL is a StatefulSet.** `k8s/base/postgres.yaml` uses `volumeClaimTemplates`, so the
pod is `postgres-0` with its own claim `pgdata-postgres-0`. When that pod is deleted or
rescheduled, its replacement has the same name and reattaches the same claim. A Deployment's pods
are interchangeable, with random names; with a shared claim, two pods during a rollout can
point at one data directory, and with no claim a rescheduled pod starts empty.
`docs/evidence/k8s-postgres-persistence.txt` shows a pod deleted, a new pod UID, and the same
rows afterwards.

**Why migrations run as an init container.** An init container cannot be forgotten: no backend
pod starts until `alembic upgrade head` exits 0. A pre-rollout Job would need its own ordering
mechanism. The cost is one migration attempt per pod, which is safe because Alembic serialises on
its version table and a second run is a no-op. The consequence is that old pods keep serving
against the new schema during a rollout, so every revision must be expand-then-contract
(`08-M7` §2.1). The seed does not run on the cluster: fixture complaints are demo data, not
production data. For a demo, run `kubectl exec -n civic-station deploy/backend -- python -m
seeds.complaints`.

**Probes mean different things.** Backend liveness and startup use `/health`, which touches no
dependency; readiness uses `/ready`, which checks the database and the cache.
`docs/evidence/k8s-probes.txt` shows the whole argument in one run: with PostgreSQL scaled to
zero, both backend pods go `0/1`, the Service has no endpoints, and `/ready` returns 503 naming
the database, while the restart count stays at 0. With liveness on `/ready`, the same outage
would have restarted every backend pod in a loop.

**Service links are off.** Both Deployments set `enableServiceLinks: false`. Without it, the
Service named `backend` injects `BACKEND_PORT=tcp://…` into every pod, which the settings
object rejects (`docs/failure-log.md`, 2026-09-28).

**Secrets.** `k8s/base/secret.example.yaml` documents the Secret with placeholders and is
deliberately not a Kustomize resource, so `kubectl apply -k` can never overwrite the real one
(`AD-064`). `DATABASE_URL` is assembled in the pod from `$(POSTGRES_PASSWORD)`, so the password
must be URL-safe; the setup script generates hex.

**Rolling update and rollback.** `maxSurge: 1`, `maxUnavailable: 0`, a 5 s `preStop` sleep and a
30 s grace period. During `kubectl rollout restart`, 444 of 444 requests through the Ingress
returned 200 (`docs/evidence/k8s-rollout.txt`). Rollback timings are in
`docs/evidence/rollback-timing-prod-limits.txt`: with the backend at its production CPU limit
(500m), `kubectl rollout undo` took 22.3–24.5 s against ADR-0003's 30 s bound, and the
declarative re-apply 22.5–25.2 s against its 90 s bound. Both paths do the same work, because an
undo is also a rolling update: two pods replaced one at a time, each running the migrate init
container, starting uvicorn and passing readiness, while each old pod waits out its `preStop`
sleep. The first measurement, on the dev overlay, took 36–39 s and missed the 30 s bound
(`docs/evidence/rollback-timing.txt`). The only difference was the dev overlay's halved CPU limit
(250m), which slows the Python start; the bound holds at the limit production actually runs.
