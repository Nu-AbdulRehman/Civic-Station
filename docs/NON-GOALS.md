# Civic-Station — Non-goals and known limitations

**Status:** Authoritative. Created 2026-09-25 by the specification audit (`docs/audit/01-specification-audit.md`).

This page lists what Civic-Station deliberately does not do. Everything here is a decision, not an oversight — each entry names the gap, what it leaves open, and where the work would attach if it came into scope.

It exists because the alternative is worse. A limitation nobody wrote down looks identical to a limitation nobody noticed, and at a viva the difference between those two is most of the mark. "We did not build authentication, here is the threat it leaves and here is the line it would attach to" is a good answer. Silence is not.

---

## 1. No authentication or authorisation

`PATCH /api/complaints/{id}/status` is open to any caller. Anyone who can reach the API can advance, resolve or reject any citizen's complaint. There are no user accounts, no sessions, no roles, and no operator identity anywhere in the system.

**Why it is out of scope.** The brief specifies no authentication: its API table (§2.2) has no auth column, the rubric has no line for it, and §5.3 attaches no deduction to its absence. Building it would be unmarked scope competing with marked work.

**What it leaves open.** Any unauthorised status change, and no audit trail of who changed what — the data model has no operator entity and no transition history, so `updated_at` is the only trace that a state change happened at all.

**Where it would attach.**

- `backend/app/routes/complaints.py` — a `Depends(require_operator)` on the `PATCH` route only. The other ten endpoints are genuinely public: a citizen submits, and the dashboard is a public transparency surface.
- A `status_transitions` table (`complaint_id`, `from_status`, `to_status`, `actor`, `at`) for the audit trail, written in the same transaction as the status change.
- The cheapest credible version is a shared `X-Operator-Token` checked against a Kubernetes Secret — roughly fifteen lines plus a frontend field. It protects against a casual visitor, not against anyone who reads the bundle, and that distinction would need saying.

**Related:** `AD-056`, `FR-FE-008`, `FR-BE-004`, `ADR-0004`.

---

## 2. Network segmentation does not hold on Kubernetes

In Compose, the frontend has no route to the database — three networks, `internal: true`, and a captured failing `ping` prove it. **On Kubernetes that property does not hold.** There is no `NetworkPolicy`, so every pod in the `civic-station` namespace can reach `postgres` and `redis` directly. `ClusterIP`-only Services prevent exposure *outside* the cluster; they do nothing about lateral movement inside it.

**Why it is out of scope.** `RUB-G-03` marks the Compose property, and the brief's §3.3 object list does not include a `NetworkPolicy`. k3d's default CNI (Flannel) does not enforce them without additional setup, so it is also not free.

**What it leaves open.** A compromised frontend pod on the cluster can open a connection to PostgreSQL. The deployment that CD actually produces is the one without the property the design argues for most strongly.

**Where it would attach.** `k8s/base/networkpolicy.yaml`: a default-deny ingress policy for the namespace, plus three allow rules — frontend ← ingress controller, backend ← frontend, postgres and redis ← backend. Roughly forty lines, and a CNI that enforces them (Calico, or k3d with `--k3s-arg --disable=flannel` plus a policy-capable CNI).

**Related:** `NFR-SEC-001`, `BR-SEC-001`, `ADR-0005`.

---

## 3. No cap on aggregate provider spend

The rate limiter bounds one client IP to 10 requests per 60 seconds. It does not bound total spend. Ten distinct IPs can legally drive 100 requests a minute into triage, above a typical free tier — and the limiter fails open for roughly ten seconds when Redis is unreachable (`ADR-0005`), during which the per-IP bound is absent too.

**Why it is out of scope.** The brief's §2.4 asks for a distributed per-IP limiter and marks that (`RUB-E-03`). A global budget is a different mechanism and is not asked for.

**What it leaves open.** A day's quota is exhaustible by a modest number of cooperating or coincidental callers. The consequence is degraded rather than catastrophic — every request past the quota falls back to `RuleBasedTriage` and still returns 201 — so the system's failure mode here is "worse classification", not "outage". That is worth knowing, and it is also the argument for why this is survivable rather than urgent.

**Where it would attach.** A second Redis counter keyed by day rather than by IP, checked in the same place as the per-IP limiter in `providers/cache/`, with a `TRIAGE_DAILY_BUDGET` setting; on exhaustion, skip the provider and go straight to rules, incrementing a `triage_budget_exhausted_total` counter. Roughly twenty lines. A circuit breaker on repeated provider failure would sit in the same place and is equally absent.

**Related:** `BR-CACHE-005`, `FR-CACHE-003`, `AD-017`.

---

## 4. No data retention, deletion or consent

Complaint rows — including `reporter_contact`, and complaint text that may name people and addresses — are kept indefinitely. There is no delete endpoint, no anonymisation job, no retention policy, no privacy notice on the submission form, and no consent flow.

**Why it is out of scope.** The brief's minimum schema has no retention column and the rubric has no line for it. `ADR-0004` covers what leaves the machine, which is what is marked.

**What it leaves open.** A citizen cannot have their complaint removed. The contact field is protected in transit — it is never sent to a model (`BR-TRIAGE-015`) — and not protected in storage. In a real municipal deployment all four of the missing pieces above would be required before the system could accept a single complaint.

**Where it would attach.** A `DELETE /api/complaints/{id}` endpoint plus a scheduled job nulling `reporter_contact` after a retention window, both behind the authentication of §1; a retention column or a policy applied by `created_at`; a notice on the Submit view. The dependency on §1 is the reason this is not a small change: an unauthenticated delete endpoint would be worse than no delete endpoint.

**Related:** `ADR-0004`, `FR-DATA-002`.

---

## 5. Images are signed nowhere

Images are scanned (Trivy, HIGH and CRITICAL with a fix available fail the build) and deployed by immutable commit-SHA tag. They are **not signed**, and signatures are not verified at deploy time.

**Why it is out of scope.** Cosign signing and digest deployment are an explicit bonus (`RUB-X-03`, +3), deferred by `AD-012`.

**What it leaves open.** The brief's §1.4 says a push to main "builds signed and scanned images". One half of that clause is implemented and one is not, so the README must not claim the sentence whole. A SHA tag is also still a tag: someone with registry write access could in principle move it, which a digest would prevent.

**Where it would attach.** `cosign sign` in `cd.yml` after `build-push`, `cosign verify` in `deploy-k8s` before apply, and the Kustomize image transformer taking the digest — already captured as a job output — instead of the tag.

**Related:** `ADR-0003`, `AD-034`.

---

## 6. Ollama is not deployed to Kubernetes

`OllamaTriage` exists, is required (`FR-AI-002`), and runs in the Compose stack. The cluster runs `TRIAGE_PROVIDER=llm`, or `simulated` in CI. There is no Ollama Deployment, Service or PVC in `k8s/`.

**Why it is out of scope.** `FR-K8S-003` specifies four Services, and the brief's §3.3 object list has no fifth workload. Model weights are also roughly 800 MB, which is a poor fit for an ephemeral in-runner cluster created fresh on every deploy.

**What it leaves open.** The buy-versus-host comparison in `docs/TRIAGE.md` is measured locally, not on the cluster, so its latency figures are laptop figures. That is stated where the numbers are reported.

**Where it would attach.** A `StatefulSet` with a PVC for `ollama_models`, an init container performing the pull, and a raised `startupProbe` budget for model load time.

**Related:** `FR-K8S-003`, `AD-046`.

---

## 7. Observability stops at the endpoint

`/metrics` exposes nine Prometheus series and `/api/meta/providers` exposes the last twenty triage outcomes. **Nothing scrapes either.** There is no Prometheus, no Grafana, no alerting, no tracing, and no log aggregation — logs go to stdout and are read with `docker compose logs` or `kubectl logs`.

**Why it is out of scope.** Prometheus plus Grafana is `RUB-X-04` (+2) and OpenTelemetry is `RUB-X-05` (+2); both are bonuses, declined by `AD-012`.

**What it leaves open.** Every measured figure the documentation reports — cache hit rate, fallback rate, HPA lag — is read by hand at a point in time rather than observed continuously. Nothing notices a rising fallback rate on its own.

**Where it would attach.** A `ServiceMonitor` and a Prometheus instance in the namespace; the metric names and buckets are already fixed in `FR-BE-009`, so the scraping side is the only missing part.

**Related:** `FR-BE-009`, `RUB-X-04`, `RUB-X-05`.

---

## 8. Smaller things, deliberately not built

| Not built | Why, and what it would cost |
|---|---|
| **Idempotency on `POST /api/complaints`** | No `Idempotency-Key`. A double submission creates two rows and, unless the content-hash cache hits, costs two inferences. The frontend disables its submit control (`FR-FE-003`), which handles the common case. A real fix is a key header plus a Redis-backed response cache. |
| **Optimistic concurrency on `PATCH .../status`** | No `ETag` or `If-Match`. Two concurrent operator transitions race, and a retried successful `PATCH` returns a 409 indistinguishable from a genuine conflict. With no operator identity (§1) and a single-operator demo, the race is not reachable in practice. |
| **Pagination beyond offset** | `LIMIT`/`OFFSET` degrades on deep pages. With 30 seeded rows it does not matter. Keyset pagination on `(created_at, id)` is the fix, and `ix_complaints_created_at_id` already supports it. |
| **Request body size limits** | No explicit cap beyond the 2000-character `text` check; nginx's default `client_max_body_size` is the effective bound. A `Content-Length` check in middleware would be the explicit version. |
| **Async triage with a pending state** | Rejected by `AD-004` on contract grounds: the brief's `POST` returns the classification, and a pending state would contradict `BR-TRIAGE-001`. |
| **Multi-tenancy, i18n, accessibility audit** | None attempted. Accessibility basics — labelled form fields, focus management, contrast — are in scope and expected; a full WCAG audit is not. |

---

## How to use this page

At viva, these are prepared answers rather than gaps. When asked "what would you do differently with another month", this page is the answer, in priority order: **authentication first** (it unblocks §1 and §4 together), then `NetworkPolicy`, then the spend cap.

When adding a feature, check whether it is listed here first. If it is, the entry says where it attaches and what it depends on. If a limitation is removed, remove its entry in the same change — a non-goals page that has drifted out of date is worse than none, because it asserts things about the system that are no longer true.
