# Engineering notes

The eight §5.2 answers are assembled here by T-M10-006. Sections are added as their owning
tasks complete; every claim cites a file and line in this repository.

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
`docs/evidence/rollback-timing.txt`: the declarative re-apply took 36.6–38.8 s against its 90 s
bound, but **`kubectl rollout undo` took 36.1–38.9 s, which misses ADR-0003's 30 s bound.** Both
paths do the same work, because an undo is also a rolling update: two pods replaced one at a
time, each running the migrate init container, starting uvicorn, and passing readiness, while
each old pod waits out its `preStop` sleep. The measurement was on the dev overlay, where the
backend CPU limit is halved to 250m, which slows the Python start. It has not yet been repeated
on the prod overlay. The levers are a faster start (prod limits) or a looser bound. `maxSurge`
is fixed by the design, and raising it would trade capacity headroom for rollback speed.
