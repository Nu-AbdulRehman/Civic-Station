# Civic-Station — Module Map

**Status:** Authoritative. Revised 2026-09-25 by the specification audit (`docs/audit/01-specification-audit.md`).
**Source of truth:** `docs/planning/Civic-Station_Problem_Statement.md`
**Purpose:** Defines the canonical module and sub-module identifiers used by every other document in this repository. Requirement IDs, business-rule IDs, design documents, and tasks all key off the identifiers on this page. Do not invent a module ID that is not listed here; if one is genuinely missing, add it here first and then reference it.

> **`M1`–`M11` on this page mean *modules*, and nothing else.** `docs/schedule/01-work-breakdown-and-critical-path.md` also uses `M0`–`M8` as *schedule milestone* labels, where `M1` means "stack runs in Compose" rather than "frontend". The two namespaces collide, so a bare `M4` is ambiguous across the document set. **Inside the requirements, business rules, design documents and ADRs, `M<n>` always means the module defined here.** The schedule documents are not used (see `docs/audit/01-specification-audit.md`, Appendix A); if they are ever revived, their milestones must be renumbered `MS-1`…`MS-8`.

---

## 1. Reading order for an implementing agent

1. This document — learn the module identifiers.
2. `docs/requirements/FUNCTIONAL-REQUIREMENTS.md` — what the system must do.
3. `docs/requirements/NON-FUNCTIONAL-REQUIREMENTS.md` — the qualities it must have.
4. `docs/requirements/BUSINESS-RULES.md` — the invariants that must never be violated.
5. `docs/decisions/OPEN-DECISIONS.md` and the ADRs under `docs/adr/` — the choices already made.
6. The design document for the module being implemented, under `docs/design/`.
7. `docs/audit/01-specification-audit.md` — the known defects, deviations from the brief, and their resolutions.
8. `docs/NON-GOALS.md` — what this system deliberately does not do, and why.

The schedule documents under `docs/schedule/` are **not** part of the reading order. They plan a one-week build that is not being followed; their milestone labels collide with the module IDs above, and Appendix A of the audit records their defects.

---

## 2. Module hierarchy

| ID | Module | Owning concern | Primary artefacts |
|----|--------|----------------|-------------------|
| **M1** | Frontend | Presentation and interaction only | `frontend/` |
| **M2** | Backend | HTTP contract, business rules, orchestration | `backend/app/` |
| **M3** | Data layer | Durable state, schema evolution, seed data | `backend/alembic/`, `backend/app/repositories/` |
| **M4** | Cache layer | Redis as cache *and* as distributed rate limiter | `backend/app/providers/cache/` |
| **M5** | AI / triage layer | Replaceable classification with enforced trust boundaries | `backend/app/providers/triage/` |
| **M6** | Containerisation | Images, Compose, networks, volumes | `Dockerfile`s, `compose*.yaml` |
| **M7** | Kubernetes | Declarative operations, probes, scaling | `k8s/` |
| **M8** | CI/CD | Gated verification, publication, deployment | `.github/workflows/` |
| **M9** | Load and scaling evidence | Proof that scaling behaves as claimed | `load/`, `docs/evidence/` |
| **M10** | Documentation and portfolio | Everything a stranger reads | `docs/`, `README.md` |
| **M11** | Process and collaboration | Branches, PRs, reviews, viva readiness | Repository settings, Git history |

---

## 3. Sub-modules

### M1 — Frontend

| ID | Sub-module | Scope |
|----|------------|-------|
| M1.1 | Submit view | Complaint submission form, validation, loading state, triage result rendering |
| M1.2 | Dashboard view | Paginated and filtered complaint list, status transition control, server error surfacing |
| M1.3 | Stats view | Aggregate counts and cache-state display |
| M1.4 | API client and types | Typed client checked against the backend OpenAPI schema |
| M1.5 | Runtime configuration and serving | nginx configuration, environment injection, multi-stage build contract |
| M1.6 | Application shell | Routing, layout, error boundary, shared state |
| M1.7 | Frontend test suite | Vitest component tests |

### M2 — Backend

| ID | Sub-module | Scope |
|----|------------|-------|
| M2.1 | Routes layer | HTTP parsing, serialisation, status codes. No business rules. |
| M2.2 | Services layer | Triage orchestration, status state machine, statistics computation |
| M2.3 | Repositories layer | All SQL. Nothing else in the system issues SQL. |
| M2.4 | Provider ports | Interfaces and factories for triage and cache; owns no vendor logic itself |
| M2.5 | Application lifecycle | Configuration loading, dependency wiring, startup, SIGTERM drain |
| M2.6 | Observability middleware | Request ID propagation, structured JSON logging, Prometheus metrics |
| M2.7 | Backend test suite | Unit and integration tests, deterministic, coverage gate |

### M3 — Data layer

| ID | Sub-module | Scope |
|----|------------|-------|
| M3.1 | Schema and migrations | Alembic revisions, enum types, constraints |
| M3.2 | Index strategy | The two required indexes and the queries that justify them |
| M3.3 | Seed data | Idempotent loader of ≥ 30 realistic complaints |
| M3.4 | Persistence contract | Volume and PVC behaviour proven across restarts |

### M4 — Cache layer

| ID | Sub-module | Scope |
|----|------------|-------|
| M4.1 | Stats read-through cache | 30 s TTL, `X-Cache` header, write invalidation |
| M4.2 | Distributed rate limiter | Per-client-IP limiting of complaint submission, 429 plus `Retry-After` |
| M4.3 | Triage content-hash cache | 24 h TTL de-duplication of inference, hit-rate measurement |
| M4.4 | Redis operations | AOF persistence, named volume, connection handling and degradation |

### M5 — AI / triage layer

| ID | Sub-module | Scope |
|----|------------|-------|
| M5.1 | Triage contracts | `TriageResult`, `TriageProvider`, provider factory and selection |
| M5.2 | `LLMTriage` | Hosted free-tier provider implementation |
| M5.3 | `OllamaTriage` | Local containerised model implementation |
| M5.4 | `RuleBasedTriage` | Deterministic keyword classifier — never fails |
| M5.5 | `SimulatedTriage` | Seeded fake with configurable failure injection, for CI |
| M5.6 | Resilience pipeline | Timeout, single jittered retry, schema validation, fallback, `triaged_by` recording |
| M5.7 | Prompt construction and injection guardrail | Untrusted-text delimiting, output constraint, injection test |
| M5.8 | Triage observability | Latency measurement, recent-outcome ring buffer, `/api/meta/providers` |

### M6 — Containerisation

| ID | Sub-module | Scope |
|----|------------|-------|
| M6.1 | Backend image | Multi-stage, pinned, non-root, cache-correct, healthcheck |
| M6.2 | Frontend image | Node build stage, nginx serve stage, size budget |
| M6.3 | `compose.yaml` (dev) | Build contexts, bind mount, healthchecks, dependency ordering |
| M6.4 | `compose.prod.yaml` | Image references only, no published data ports, resource limits |
| M6.5 | Networks and volumes | Two-network segmentation, three named volumes, proven isolation |

### M7 — Kubernetes

| ID | Sub-module | Scope |
|----|------------|-------|
| M7.1 | Workload manifests | Namespace, Deployments, StatefulSet, Services, Ingress |
| M7.2 | Configuration and secrets | ConfigMap, Secret with committed placeholders only |
| M7.3 | Probes and pod lifecycle | Startup, liveness, readiness, `preStop`, termination grace |
| M7.4 | Resources and HPA | Requests and limits on every container, HPA v2 with tuned behaviour |
| M7.5 | VPA | Recommender mode, recommendation capture, request revision loop |
| M7.6 | Availability and rollout | PodDisruptionBudget, rolling update strategy, rollback procedures |
| M7.7 | Kustomize overlays | `base/` plus `overlays/dev` and `overlays/prod` |

### M8 — CI/CD

| ID | Sub-module | Scope |
|----|------------|-------|
| M8.1 | `ci.yml` | Lint, type check, tests, build, scan, manifest validation, Compose integration |
| M8.2 | `cd.yml` | Gated test, build-push to GHCR, ephemeral-cluster deploy and smoke test |
| M8.3 | `release.yml` | Tag-triggered semver publication and release notes |
| M8.4 | Repository governance | Branch protection, required checks, approvals |
| M8.5 | Supply chain controls | Trivy, SBOM, action pinning, least-privilege permissions, secret handling |

### M9 — Load and scaling evidence

| ID | Sub-module | Scope |
|----|------------|-------|
| M9.1 | Load generator | k6 (or `hey`) script and profiles |
| M9.2 | HPA scale-out capture | metrics-server install, `kubectl get hpa -w` capture, replicas-vs-load chart |
| M9.3 | VPA recommendation loop | Before/after requests, recommendation output, behavioural analysis |
| M9.4 | Zero-downtime rollout demo | Load during `kubectl set image`, failed-request count |

### M10 — Documentation and portfolio

| ID | Sub-module | Scope |
|----|------------|-------|
| M10.1 | `README.md` | Problem, badges, Mermaid diagram, quickstart, API table, screenshots |
| M10.2 | ADRs | Four mandatory records plus any further decisions taken |
| M10.3 | `docs/RUNBOOK.md` | Deploy, roll back, read logs, triage-failure response |
| M10.4 | `docs/ENGINEERING-NOTES.md` | The eight questions, with file-and-line references |
| M10.5 | `docs/AI-USAGE.md` and `docs/TRIAGE.md` | AI attribution; triage design, prompts and measured behaviour |
| M10.6 | Evidence artefacts | Screenshots and captures under `docs/evidence/` |
| M10.7 | `scripts/check_submission.py` | Mechanical pre-submission lint |
| M10.8 | Demo video | ≤ 5 minutes, both partners speaking, prescribed content |

### M11 — Process and collaboration

| ID | Sub-module | Scope |
|----|------------|-------|
| M11.1 | Branch and PR flow | `dev` plus feature branches, protected `main`, PR/Issue linkage |
| M11.2 | Commit conventions | Conventional prefixes, commit floor, contribution balance |
| M11.3 | Merge conflict exercise | One deliberate conflict on real code, resolved with written rationale |
| M11.4 | Viva readiness | Cross-ownership knowledge, per-partner walkthroughs |

---

## 4. Dependency direction between modules

The arrows below are compile-time and runtime dependency directions. A dependency in the reverse direction is a design failure.

```
M1 Frontend ──HTTP──► M2 Backend
                         │
                         ├──► M2.2 Services ──► M2.3 Repositories ──► M3 Data
                         │                  └──► M2.4 Ports ──┬──► M5 AI
                         │                                    └──► M4 Cache
                         └──► M2.6 Observability (cross-cutting)

M6 Containerisation packages M1 + M2 and composes M3 + M4 + M5(local)
M7 Kubernetes deploys the images M6 produces
M8 CI/CD verifies M1–M7 and publishes M6 artefacts, deploys via M7
M9 measures M7
M10 documents M1–M9
M11 governs how M1–M10 get built
```

**Invariants, stated so that none is left indeterminate:**

- M1 never depends on M3, M4 or M5.
- M2.1 (routes) never depends on M3 directly.
- M2.3 (repositories) never depends on M2.2 (services).
- M5 never depends on M2.2 or M2.3 — the triage layer knows nothing of services or persistence.
- **M5 *does* depend on M4**, through the cache port only. `FR-CACHE-004` puts the triage content-hash cache in Redis and `FR-AI-012` puts the outcomes ring buffer there, so this dependency is required, not tolerated. It was previously unstated, which left the invariant indeterminate: a reader could not tell whether M5 → M4 was permitted or a violation.
- M4 never depends on M5, M2.2 or M2.3. The cache port is a leaf.

---

## 5. Identifier conventions used across all documents

| Prefix | Meaning | Example |
|--------|---------|---------|
| `FR-<MOD>-nnn` | Functional requirement | `FR-BE-003` |
| `NFR-<CAT>-nnn` | Non-functional requirement | `NFR-SEC-004` |
| `BR-<DOMAIN>-nnn` | Business rule / invariant | `BR-STATUS-002` |
| `AD-nnn` | Architectural decision requiring a human choice | `AD-007` |
| `ADR-nnnn` | Accepted architectural decision record | `ADR-0001` |
| `T-<MOD>-nnn` | Implementation task, defined in that module's design document | `T-M5-012` |
| `RUB-<X>-nn` | Rubric line item | `RUB-F-03` |

Module abbreviations used inside requirement IDs: `FE` (M1), `BE` (M2), `DATA` (M3), `CACHE` (M4), `AI` (M5), `CTR` (M6), `K8S` (M7), `CICD` (M8), `LOAD` (M9), `DOC` (M10), `PROC` (M11).

**Where each identifier actually lives**, because two of these conventions were declared here and then used nowhere:

| Prefix | Defined in | Referenced from |
|---|---|---|
| `FR-*`, `NFR-*`, `BR-*` | `FUNCTIONAL-REQUIREMENTS.md`, `NON-FUNCTIONAL-REQUIREMENTS.md`, `BUSINESS-RULES.md` | each other, `RUBRIC-TRACEABILITY.md`, the design documents |
| `AD-*` | `docs/decisions/OPEN-DECISIONS.md` (resolution log) | requirements, design documents, ADRs |
| `ADR-*` | `docs/adr/` | `OPEN-DECISIONS.md`, `FR-DOC-002` |
| `T-*` | the task table at the end of each `docs/design/*.md` | that same table only |
| `RUB-*` | `RUBRIC-TRACEABILITY.md` | that document, and now cited by ID from requirements rather than in prose |

**Sub-module IDs (`M1.1`, `M2.4`, …) are cited by the design documents and by `RUBRIC-TRACEABILITY.md`.** They appear as headings in the M1 and M2 sections of `FUNCTIONAL-REQUIREMENTS.md` and not in M3–M11, which is a formatting inconsistency rather than a missing definition — the identifiers are defined on this page and are valid to cite wherever they are useful.
