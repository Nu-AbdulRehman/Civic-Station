# 08 — M7 Kubernetes: design and implementation guide

**Owner:** Dev 2 (`AD-013`)
**Depends on:** M6 (images), M2 `T-M2-011` (real probes), M2 `T-M2-012` (SIGTERM)
**Delivers:** `RUB-H-01`…`RUB-H-04`, and four automatic deductions. **`RUB-H-05` and `RUB-H-06` belong to M9** (`10-M9-load-evidence.md`), which produces the scaling and VPA evidence — this document specifies the manifests those rows are measured against. Previously both documents claimed Rubric H's marks, double-counting them. Mark totals are not quoted in design documents (`AD-047`).
**Stack:** k3d with bundled Traefik (`AD-028`), Kustomize `base/` + `overlays/{dev,prod}` (`AD-011`)

---

## 1. What this module is for

Declarative operations, and the fact that autoscaling is impossible without resource requests.

Two ideas carry most of the marks: **probes that mean different things**, and **a scaling signal with a denominator**. Both are places where a plausible-looking manifest is silently wrong and only shows up under load or under failure.

---

## 2. Objects

Namespace **`civic-station`** (`AD-030` — the brief writes `Civic-Station`, which Kubernetes rejects because object names must be RFC 1123 lower-case; the correction is noted in the engineering notes).

| Object | Detail |
|---|---|
| Namespace | `civic-station`. Nothing in `default`. |
| Deployment `backend` | ≥ 2 replicas, HPA-managed |
| Deployment `frontend` | ≥ 2 replicas |
| **StatefulSet `postgres`** | With `volumeClaimTemplates` → PVC. **A Deployment for the database is −8.** |
| Deployment `redis` + PVC | AOF on the PVC |
| Services × 4 | `backend`, `frontend`, `postgres`, `redis` — **all ClusterIP.** The database is never NodePort or LoadBalancer (−8). **No Ollama Service:** the cluster runs `TRIAGE_PROVIDER=llm`, or `simulated` in CI. Ollama is Compose-only (`docs/NON-GOALS.md` §6) — 800 MB of weights is a poor fit for a cluster created fresh on every deploy. |
| Ingress | One host; `/` → frontend, `/api` → backend |
| ConfigMap | Non-secret configuration |
| Secret | DB password, LLM key — **committed manifests carry placeholders only** (−15 for a real key, base64 included) |
| HPA | On the backend, `autoscaling/v2` |
| VPA | On the backend, `updateMode: "Off"` |
| PDB | `minAvailable: 1` on the backend |
| **No NetworkPolicy** | Deliberate, and the one place this deployment is weaker than Compose. Pod-to-pod traffic inside the namespace is unrestricted, so a compromised frontend pod **can** reach `postgres`. `ClusterIP` stops external exposure, not lateral movement. `BR-SEC-001` holds in Compose and not here; the default-deny policy plus three allow rules that would close it is in `docs/NON-GOALS.md` §2. |
| `securityContext` | `runAsNonRoot: true`, `runAsUser` 1000 (backend) / 101 (frontend), `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true` on the frontend (its writable paths are already `/tmp`, per `07-M6-containers.md`). Not on the backend, which writes nothing but would need `/tmp` mounted as an `emptyDir` to claim it. |

**Why a StatefulSet and not a Deployment.** A Deployment's pods are interchangeable and its volume story is shared; a StatefulSet gives each pod a stable identity and its own PVC through `volumeClaimTemplates`, so a rescheduled `postgres-0` reattaches *its* disk. With a Deployment and a shared or absent PVC, a rescheduled pod can come up against an empty volume, or two pods can attempt the same data directory. Be ready to say this at viva; it is an explicitly flagged question.

### 2.1 Migrations on the cluster

Migrations run as an **init container** on the backend Deployment. Never from application startup (`BR-DATA-001`).

**The choice is made, not offered.** A pre-rollout `Job` is arguably cleaner, but it needs its own ordering mechanism — a hook, or a pipeline step that waits — and it can be forgotten. An init container cannot be forgotten: no backend pod starts until it exits 0. The cost is that it runs once per pod, which is safe because Alembic is idempotent.

With multiple replicas, several init containers race. Alembic takes a lock on the version table, so the losers wait and then no-op.

**The constraint this creates, which matters more than the choice.** The init container migrates **before** the new pod starts, while `maxUnavailable: 0` keeps old pods serving. For the duration of a rollout, **the old code runs against the new schema.** Every revision must therefore be backward-compatible with the previous application version: add nullable columns and new tables in the release that starts writing them, and drop or narrow only in a later release. This is expand-then-contract, it is required rather than advisory, and it is stated in `04-M3-data.md` §2.3 as well.

---

## 3. Probes — the part that must be right

**Backend** — every value explicit, because a probe with an unstated period is a probe whose behaviour is unstated:

```
startupProbe:   /health  periodSeconds: 2  failureThreshold: 30  timeoutSeconds: 2
livenessProbe:  /health  periodSeconds: 10 failureThreshold: 3   timeoutSeconds: 2
readinessProbe: /ready   periodSeconds: 5  failureThreshold: 2   timeoutSeconds: 2
```

**The other three workloads get probes too**, since `FR-CTR-009` requires a healthcheck on every Compose service and the manifests should not be weaker than the Compose file:

| Workload | Liveness | Readiness |
|---|---|---|
| `postgres` | `pg_isready -U $POSTGRES_USER` | same, `periodSeconds: 5` |
| `redis` | `redis-cli ping` | same, `periodSeconds: 5` |
| `frontend` | `httpGet /` on 8080 | same, `periodSeconds: 10` |

`/ready`'s own dependency checks run concurrently under a 1-second timeout each (`READINESS_TIMEOUT_SECONDS`), so the endpoint answers within 1 second — comfortably inside its 2-second probe timeout. A readiness endpoint slower than its own probe period is a second failure mode stacked on the first.

**The three do different things and a mistake is expensive:**

- A failing **liveness** probe **restarts the pod**. It must therefore depend on nothing but the process. `/health` opens no connection (`BR-OPS-001`). Wire liveness to `/ready` and a slow database becomes a restart loop across the entire deployment — a partial outage turned total.
- A failing **readiness** probe **removes the pod from the Service**. It *should* depend on the database and cache, because a pod that cannot reach them cannot serve.
- The **startup** probe exists so that a slow boot is not mistaken for a failure. Without it, liveness starts probing immediately and a cold start becomes a crash loop.

**The demonstration:** stop PostgreSQL, observe that backend pods leave the Service endpoints while their restart count stays unchanged. That single observation proves all three are wired correctly.

---

## 4. Resources, and the HPA denominator

**Every container declares `resources.requests` and `resources.limits`** for CPU and memory (`FR-K8S-007`).

This is not hygiene, it is a precondition: **the HPA computes utilisation as usage ÷ request.** With no `resources.requests.cpu` there is no denominator, and the HPA sits at `<unknown>/60%` forever. Every semester several teams debug a "broken HPA" that is a missing three-line block.

**The starting values** (`AD-048`), which are the recorded guess that `FR-LOAD-003`'s step 1 needs:

| Container | `requests.cpu` | `requests.memory` | `limits.cpu` | `limits.memory` |
|---|---|---|---|---|
| backend | `100m` | `256Mi` | `500m` | `512Mi` |
| frontend | `20m` | `32Mi` | `100m` | `128Mi` |
| postgres | `200m` | `512Mi` | `1000m` | `1Gi` |
| redis | `50m` | `64Mi` | `200m` | `256Mi` |

**The backend's `100m` is deliberately small**, so that a plateau above the 60 % target is reachable with a load a student laptop can generate. A larger request would need more offered load to cross the threshold, and the demonstration would fail for lack of a load generator rather than for lack of autoscaling.

**These are a guess, and the notes say so.** That is the point of the VPA loop: record the guess, measure, compare, update. A document that presented them as derived would remove the only interesting part of `FR-LOAD-003`.

### 4.1 HPA (`FR-K8S-008`)

```
autoscaling/v2, minReplicas: 2, maxReplicas: 10
metric: Resource cpu, Utilization, averageUtilization: 60
behavior:
  scaleUp:   stabilizationWindowSeconds: 0     # users are waiting
  scaleDown: stabilizationWindowSeconds: 300   # flapping is expensive
```

The asymmetry is the point and is worth stating at viva: adding capacity late costs user-visible latency; removing it early costs a re-scale and a cold pod. Asymmetric windows encode that the two mistakes are not equally bad.

**metrics-server must be installed** or the HPA has no metric source at all.

### 4.2 VPA in recommender mode (`FR-K8S-009`)

```
updatePolicy: { updateMode: "Off" }   # recommend only — do not evict
```

**Why Off, stated plainly** (engineering-notes Q6): HPA scaling on CPU and VPA in `Auto` mode adjusting CPU requests act on the *same signal* and fight each other. VPA raises the request → computed utilisation (usage ÷ request) drops → HPA scales in → per-pod load rises → VPA raises the request again. Recommender mode plus a human decision is current industrial practice for exactly this reason.

The loop to run (`FR-LOAD-003`): record the guessed requests → run the load test → `kubectl describe vpa backend-vpa` and commit Target / Lower Bound / Upper Bound → update requests to match → re-run → report what changed about HPA behaviour.

---

## 5. Rollout and disruption

```
strategy.rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }
terminationGracePeriodSeconds: 30
lifecycle.preStop: exec: ["sh", "-c", "sleep 5"]
```

**Both numbers are exact, not approximate.** 5 seconds covers Endpoints propagation across nodes; 30 seconds then leaves 25 for in-flight work against a 21-second worst-case request (`FR-AI-006`). `preStop` was previously written as `sleep ~5s` — and this is the value that decides whether the zero-downtime demonstration passes, so an approximation in the manifest is an approximation in the result.

**Why `preStop` exists.** On pod deletion, two things happen concurrently: the kubelet sends SIGTERM, and the endpoints controller removes the pod from the Service. There is no ordering guarantee. Without a `preStop` delay, the process can begin shutting down while the Service is still routing to it — which is a dropped request during every rolling update. The sleep gives endpoint propagation a head start, and the backend's SIGTERM drain (`FR-BE-021`) handles what is already in flight.

`maxUnavailable: 0` means capacity never dips below the desired count during an update. `PodDisruptionBudget minAvailable: 1` protects against voluntary disruption (a node drain) taking the last pod.

Together with the drain, these are what make the zero-downtime demonstration (`FR-LOAD-004`) nearly free — **and it is required, not a bonus.** The brief states it in the body of §3.3 at `:293`, and `NFR-REL-003` is a `MUST` whose only measure is that demonstration (`AD-012`).

---

## 6. Configuration and secrets

ConfigMap carries non-secret configuration: `TRIAGE_PROVIDER`, TTLs, rate-limit values, log level, `BACKEND_ORIGIN` for the frontend.

Secret carries the database password and the LLM API key. **Committed manifests contain placeholders only** (`FR-K8S-005`). Base64 is encoding, not encryption — a base64'd real key in a committed manifest is −15.

Real values are supplied by `kubectl create secret generic … --from-literal` (`AD-027`), documented in the runbook and executed in CI from GitHub Secrets. A Kustomize `secretGenerator` over a git-ignored `.env` is the local-development convenience.

**Rotation, because replacing a Secret is not enough** (`FR-PROC-006`). Values are injected as environment variables at container start, so an updated Secret does **not** reach a running pod. Rotation is therefore two commands:

```
kubectl create secret generic app-secrets -n civic-station \
  --from-literal=GROQ_API_KEY=<new> --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deployment/backend -n civic-station
```

Without the second, the old credential stays live in every running pod — which is the failure mode that makes a rotation look complete and not be. The full procedure, including revoking at the source and writing the incident note that §5.3 requires alongside the −20, is in `docs/RUNBOOK.md`.

---

## 7. Kustomize layout (`FR-K8S-012`)

```
k8s/base/         namespace, backend, frontend, postgres, redis, ingress,
                  configmap, secret, hpa, vpa, pdb + kustomization.yaml
k8s/overlays/dev  LOG_LEVEL=DEBUG, TRIAGE_PROVIDER=simulated, limits halved
k8s/overlays/prod LOG_LEVEL=INFO, TRIAGE_PROVIDER=llm, AD-048 limits,
                  image tags set to the commit SHA
```

**Neither overlay changes `replicas`.** The dev overlay previously said "lower replicas" — which cannot happen: the HPA's `minReplicas: 2` takes effect immediately and overrides any lower value in the Deployment, so a lowered dev replica count would silently not occur. Overlays differ in configuration and resource limits, and `replicas` is the HPA's to own.

**Helm is not an alternative.** `AD-011` settled on Kustomize; the earlier "Helm is permitted with an ADR" left the CI `manifests` job unable to be written against either.

The deployed image tag is set by a Kustomize **image transformer** driven by the pipeline (`ADR-0003`). The committed overlay holds a placeholder tag; `:latest` is never deployed (−8).

`kustomize build overlays/prod | kubeconform` runs on every PR and catches a broken manifest in twenty seconds instead of on the cluster.

---

## 8. Ingress

One host, `civic-station.localhost` (`AD-029`), `/` → frontend Service, `/api` → backend Service. k3d's bundled Traefik serves as the controller, which removes an install step and a class of "why is my Ingress pending" debugging.

Note that `/api` routing now exists at two layers — the Ingress and the frontend's nginx proxy (`ADR-0002`). Both work; the Ingress path is the one the CI smoke test exercises. The CI smoke test sends an explicit `Host` header so it does not depend on DNS.

---

## 9. Invariants this module must not violate

| Rule | Deduction |
|---|---|
| PostgreSQL as a Deployment with no PVC | −8 |
| NodePort/LoadBalancer on the database | −8 |
| Real key in a committed manifest | −15 |
| Deploying `:latest` | −8 |
| `BR-OPS-001` — liveness independent of the database | correctness, plus 4 marks |

---

## 10. Tasks

| ID | Task | Size | Owner | Depends on | Delivers | Done when |
|---|---|---|---|---|---|---|
| T-M7-001 | k3d cluster setup script + metrics-server install, documented | S | Dev 2 | — | FR-LOAD-002 | `kubectl top nodes` returns data |
| **T-M7-002** | `base/`: namespace, both Deployments, postgres StatefulSet + volumeClaimTemplates, redis + PVC, four ClusterIP Services | **L** | Dev 2 | M6 T-M6-003 | FR-K8S-001/002/003 | `kubectl get all -n civic-station` shows everything Running |
| T-M7-003 | ConfigMap + Secret with placeholders; `kubectl create secret` documented | S | Dev 2 | T-M7-002 | FR-K8S-005, AD-027 | Secret scan over manifests clean |
| **T-M7-004** | All three probes wired correctly | M | Dev 2 | T-M7-002, M2 T-M2-011 | FR-K8S-006, NFR-REL-004 | Stopping PostgreSQL: pods leave endpoints, restart count unchanged |
| T-M7-005 | `resources.requests` and `limits` on every container; original guesses recorded | S | Dev 2 | T-M7-002 | FR-K8S-007, NFR-SCALE-002 | Checker script passes; guessed values written down for the VPA loop |
| T-M7-006 | Ingress `/` and `/api` on one host | S | Dev 2 | T-M7-002 | FR-K8S-004 | `curl -H 'Host: civic-station.localhost'` reaches both |
| T-M7-007 | Migrations as an init container or pre-rollout Job | S | Dev 2 | T-M7-002, M3 T-M3-002 | BR-DATA-001 | Fresh cluster comes up migrated; choice justified in the notes |
| **T-M7-008** | HPA v2 with tuned `behavior` | M | Dev 2 | T-M7-005, T-M7-001 | FR-K8S-008, NFR-SCALE-003 | `kubectl get hpa` shows a real percentage, never `<unknown>` |
| T-M7-009 | VPA installed; `backend-vpa` in `updateMode: "Off"` | M | Dev 2 | T-M7-005 | FR-K8S-009 | `kubectl describe vpa` returns recommendations after load |
| T-M7-010 | PDB `minAvailable: 1`; rollout strategy, `terminationGracePeriodSeconds`, `preStop` | S | Dev 2 | T-M7-002, M2 T-M2-012 | FR-K8S-010/011 | Rolling update completes with no capacity dip |
| T-M7-011 | Kustomize base + dev/prod overlays; image transformer for the SHA tag | M | Dev 2 | T-M7-002…010 | FR-K8S-012/013, ADR-0003 | `kustomize build overlays/prod \| kubeconform` clean; no `:latest` |
| T-M7-012 | Postgres pod-delete persistence demonstration | S | Dev 2 | T-M7-002 | FR-DATA-005 | Rows survive `kubectl delete pod postgres-0`; captured |
| T-M7-013 | Both rollback mechanisms exercised and timed | S | Dev 2 | T-M7-011 | FR-K8S-014, NFR-OPS-002 | `rollout undo` under 30 s; declarative re-apply also proven |
| T-M7-014 | Engineering-notes Q6 (VPA Off) drafted | S | Dev 2 | T-M7-009 | RUB-J-05 | Explains the HPA/VPA feedback loop concretely |

---

## 11. Verification checklist

```
kubectl get all -n civic-station                     # nothing in default
kubectl get svc -n civic-station                     # all ClusterIP
kubectl get hpa -n civic-station                     # a percentage, not <unknown>
kubectl get statefulset postgres -n civic-station    # exists; PVC bound
kustomize build k8s/overlays/prod | grep -c ':latest'   # 0
kustomize build k8s/overlays/prod | kubeconform -strict
kubectl delete pod postgres-0 -n civic-station        # rows survive
kubectl scale deploy/backend --replicas=0 ... # NOT part of the demo; HPA min is 2
```
