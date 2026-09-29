# Runbook

Commands for operating Civic-Station. Every block is copy-paste; `<sha>` is a full commit SHA from
`main`. Kubernetes commands assume the namespace `civic-station` and a `kubectl` context pointing
at the cluster (`k3d-civic-station` locally).

---

## 1. Deploy

### Normal path: merge to `main`

A merge to `main` runs `.github/workflows/cd.yml`: the eight CI checks, then images pushed to GHCR
as `:<sha>`, then a deploy of that SHA to a k3d cluster in the runner with an Ingress smoke test.
There is nothing to run by hand. Watch it under **Actions → CD**.

### By hand, to a cluster you control

```sh
SHA=<sha>
REGISTRY=ghcr.io/nu-abdulrehman

# Once per cluster: the Secret (never committed; AD-027, AD-064). URL-safe password only.
kubectl create namespace civic-station --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic app-secrets -n civic-station \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 16)" \
  --from-literal=GROQ_API_KEY="<key>"

# Deploy the SHA: scripts/deploy-k8s.sh pins both images and APP_VERSION to it, applies the prod
# overlay, waits for every rollout, and refuses to apply a render that still has the placeholder tag.
REGISTRY=$REGISTRY sh scripts/deploy-k8s.sh deploy "$SHA"
EXPECT_PROVIDER=llm sh scripts/deploy-k8s.sh smoke "$SHA"
```

A fresh local cluster is `sh scripts/k3d-up.sh` (dev overlay, locally built images). The cluster
needs the VPA CRDs and Traefik configured as `scripts/k3d-cluster.sh` does; on any other cluster,
apply `k8s/cluster/traefik-config.yaml`'s equivalent so the Ingress keeps the client address
(`AD-068`).

### With Docker Compose

```sh
make up                                                     # development, builds from source
IMAGE_TAG=<sha> docker compose -f compose.prod.yaml up -d --wait   # production images, credentials from .env
```

### What is running?

```sh
curl -H 'Host: civic-station.localhost' http://127.0.0.1:8081/api/version   # {"version": "<sha>", "provider": ...}
kubectl get deploy backend -n civic-station -o jsonpath='{.spec.template.spec.containers[0].image}'
```

The two must agree (ADR-0003).

---

## 2. Roll back

### During an incident: imperative, about 25 s

```sh
kubectl rollout undo deployment/backend -n civic-station
kubectl rollout undo deployment/frontend -n civic-station
kubectl rollout status deployment/backend -n civic-station --timeout=300s
```

Measured at 22.3–24.5 s with production limits (`docs/evidence/rollback-timing-prod-limits.txt`).
`cd.yml` runs the same command automatically when its smoke test fails (`AD-065`).

**Then, once the fire is out, re-apply the known-good SHA declaratively.** `rollout undo` does not
update `kubectl apply`'s record of the last applied state, so a later `apply` of the bad release
would change nothing and look like a success (`docs/failure-log.md`, 2026-09-28):

```sh
REGISTRY=ghcr.io/nu-abdulrehman sh scripts/deploy-k8s.sh deploy <good-sha>
```

### Declarative only: about 25 s

Re-apply the previous good SHA with the `deploy-k8s.sh` command above. The cluster and the
repository agree again as soon as it finishes.

### Compose

```sh
IMAGE_TAG=<good-sha> docker compose -f compose.prod.yaml up -d --wait
```

### Schema changes

Every Alembic revision is expand-then-contract, because old pods serve against the new schema during
a rollout (`08-M7` §2.1). Rolling the application back therefore never needs a schema downgrade. Do
not run `alembic downgrade` on a live database.

---

## 3. Read logs

Every backend log line is one JSON object on stdout with `ts`, `level`, `msg`, `request_id` and
`logger` (`AD-057`). Complaint text appears only at `DEBUG`; keys and contact details never.

```sh
# Kubernetes: all backend pods, including the migrate init container
kubectl logs -n civic-station -l app=backend -c backend --tail=200 -f
kubectl logs -n civic-station deploy/backend -c migrate

# Compose
docker compose logs -f backend
```

Useful filters (`jq` or `grep`):

```sh
kubectl logs -n civic-station -l app=backend -c backend --since=15m | grep '"level": "WARNING"'
kubectl logs -n civic-station -l app=backend -c backend --since=15m | grep '"msg": "triage.fallback"'
kubectl logs -n civic-station -l app=backend -c backend | grep '<request-id>'   # one request, end to end
```

Every error response carries `request_id`, and the frontend shows it, so a user's report can be
matched to its log lines. Metrics are at `GET /metrics` (Prometheus text).

Probe state without logs:

```sh
kubectl get pods -n civic-station                 # READY 0/1 = readiness failing (DB or cache), RESTARTS = liveness
kubectl describe pod -n civic-station <pod>       # probe failures and events
curl -s -H 'Host: civic-station.localhost' http://127.0.0.1:8081/api/stats -D - -o /dev/null | grep -i x-cache
```

---

## 4. When triage starts failing

A provider failure never becomes an error for the citizen: every valid complaint still gets a
`201`, classified by the keyword rules and marked `triaged_by: rules:fallback`. The symptom is
therefore quiet: rising `rules:fallback` counts, not errors.

**1. Confirm and classify it.**

```sh
curl -s -H 'Host: civic-station.localhost' http://127.0.0.1:8081/api/meta/providers
kubectl logs -n civic-station -l app=backend -c backend --since=15m | grep triage.fallback
```

Each `triage.fallback` line names an `error_class`:

| `error_class` | Meaning | Action |
|---|---|---|
| `RateLimited` | The provider's quota is spent (Groq's free tier allows about 8,000 tokens a minute) | Nothing breaks; the rules answer until the window resets. If sustained, lower traffic or change plan |
| `Timeout` | Each call took longer than `TRIAGE_TIMEOUT_SECONDS` (10 s) | Check provider status. For Ollama, check CPU: `docker stats` and `ollama ps` (`docs/failure-log.md`, 2026-09-29) |
| `ServerError` | The provider returned 5xx | Provider outage; wait, or switch provider (step 3) |
| `ValidationFailed` | The model answered with JSON that fails the schema | A model change on the provider's side. Check `TRIAGE_MODEL` is still served; re-run `scripts/measure_triage.py` |
| `Other` | Everything else, including 401 and 404 | A bad or revoked key (401) or a retired model (404). Test the key: step 2 |

**2. Test the provider directly** from inside a backend pod, which proves key, model and egress in
one call:

```sh
kubectl exec -n civic-station deploy/backend -c backend -- python -c "
import os, httpx
r = httpx.get('https://api.groq.com/openai/v1/models', headers={'Authorization': 'Bearer ' + os.environ['GROQ_API_KEY']}, timeout=10)
print(r.status_code, [m['id'] for m in r.json().get('data', [])] if r.status_code == 200 else r.text[:200])"
```

A 401 means rotate the key (section 5). A 200 without `TRIAGE_MODEL` in the list means the model
was retired: pick a served one, update `TRIAGE_MODEL` in the ConfigMap, record it in `AD-045`, and
roll out.

**3. Switch provider** if the hosted model is down for long. The rules classifier needs nothing
external:

```sh
kubectl set env deployment/backend -n civic-station TRIAGE_PROVIDER=rules
```

Revert with `kubectl set env deployment/backend -n civic-station TRIAGE_PROVIDER-` once the provider
recovers, then re-apply the overlay.

---

## 5. Rotate a secret

A Secret update does not reach running pods, because values are read as environment variables at
container start. Rotation is always two commands (`FR-PROC-006`):

```sh
kubectl create secret generic app-secrets -n civic-station \
  --from-literal=POSTGRES_PASSWORD="$(kubectl get secret app-secrets -n civic-station -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d)" \
  --from-literal=GROQ_API_KEY="<new key>" --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deployment/backend -n civic-station
```

For CD, update the `GROQ_API_KEY` repository secret (Settings → Secrets and variables → Actions).

**If a key was exposed** (committed, logged or pasted anywhere public):

1. Revoke it at the provider first; rotation without revocation leaves the leaked key live.
2. Rotate as above, in every place it is used.
3. If it reached git history, removing the commit is not enough: the key is burned. Rotate anyway.
4. Write an entry in `docs/INCIDENTS.md`: what leaked, when, how it was found, what was revoked.

`python scripts/check_submission.py` scans the tree and the full git history for key-shaped strings
and fails the `submission-check` CI job on a match.

---

## 6. Quick reference

| Task | Command |
|---|---|
| Start locally | `make up` |
| Local cluster | `sh scripts/k3d-up.sh` |
| Seed demo data on the cluster | `kubectl exec -n civic-station deploy/backend -c backend -- python -m seeds.complaints` |
| Offline triage (Ollama) | `make pull-models`, then `TRIAGE_PROVIDER=ollama docker compose --profile ollama up -d --wait` |
| Scale test | `k6 run load/k6-script.js` with `sh scripts/watch_scaling.sh 660 <prefix>` |
| Repository checks | `python scripts/check_submission.py` |
