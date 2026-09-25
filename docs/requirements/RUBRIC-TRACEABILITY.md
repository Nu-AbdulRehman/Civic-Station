# Civic-Station — Rubric Traceability Matrix

**Status:** Authoritative. Revised 2026-09-25 by the specification audit (`docs/audit/01-specification-audit.md`).
**Source:** `docs/planning/Civic-Station_Problem_Statement.md` §4 and §5.3 (deductions)

## Purpose

The rubric is the real acceptance criteria. This matrix maps every marked line to the requirements that deliver it, the module that owns it, and the evidence that proves it. Use it in two directions:

- **Forward:** before writing a design document, check which rubric lines the module carries.
- **Backward:** before submitting, walk every row and confirm the evidence column actually exists.

A rubric line with no evidence is an unmarked line, regardless of whether the code works.

## The mark total does not add up, and this document does not pretend otherwise

The brief states **150 marks** at `Problem_Statement.md:389`. Its own section weights are A 15, B 18, C 25, D 12, E 10, F 25, G 15, H 20, I 20, J 15 — which **sum to 175**, plus 15 of bonus. §5.1 has the same problem: it calls parts A–G "110 marks" where those lines sum to 120.

Each row below carries the weight the brief gives it, and each section header carries the brief's section total. Those are faithfully reproduced. **What is not reproduced is a reconciliation**, because there is no honest way to derive one: normalising to 150 would silently change what every line is worth, and asserting 175 would contradict the brief's own headline.

**Action (`AD-047`): raise this with the instructor before submission.** Until it is answered, work every line — that is correct under either reading — and do not report a percentage anywhere, since the denominator is unknown. No design document states a mark total any more; each cites the rubric rows it delivers.

---

## A · Collaboration and version control — 15 marks

| ID | Rubric line | Marks | Requirements | Module | Evidence |
|----|-------------|-------|--------------|--------|----------|
| RUB-A-01 | `main` protected: no direct push, PR required, CI required, ≥ 1 approval | 3 | FR-CICD-012 | M8.4 | `docs/evidence/branch-protection.png` |
| RUB-A-02 | Two-branch model plus feature branches; nothing committed directly to `main` | 2 | FR-PROC-001, BR-DEL-003 | M11.1 | Git history, `git log --first-parent main` |
| RUB-A-03 | ≥ 5 merged PRs, each linked to an Issue, each with a substantive partner review | 4 | FR-PROC-002 | M11.1 | PR list |
| RUB-A-04 | ≥ 35 commits, conventional prefixes, neither partner below 35 % | 3 | FR-PROC-003 | M11.2 | `git shortlog -sn` |
| RUB-A-05 | One deliberate merge conflict resolved, with evidence and 2–4 sentences | 3 | FR-PROC-004 | M11.3 | `docs/evidence/merge-conflict/` |

## B · Frontend — 18 marks

| ID | Rubric line | Marks | Requirements | Module | Evidence |
|----|-------------|-------|--------------|--------|----------|
| RUB-B-01 | Submit view: validation, honest loading state, renders category/priority/summary/provider | 5 | FR-FE-001, FR-FE-002, FR-FE-003, FR-FE-004, FR-FE-005 | M1.1 | Component tests, screenshot |
| RUB-B-02 | Dashboard: pagination, filters, transitions, 409 surfaced verbatim | 5 | FR-FE-006, FR-FE-007, FR-FE-008, FR-FE-009, BR-STATUS-005 | M1.2 | Component tests, screenshot |
| RUB-B-03 | Stats view rendering aggregates and cache-hit state | 3 | FR-FE-010, FR-FE-011 | M1.3 | Component test, screenshot |
| RUB-B-04 | Runtime configuration — no baked-in API URL, one image everywhere | 3 | FR-FE-014, NFR-PORT-001, AD-001 | M1.5 | ADR-0002, one-digest-two-environments demo |
| RUB-B-05 | ≥ 5 meaningful component tests in CI | 2 | FR-FE-020 | M1.7 | CI run |

## C · Backend — 25 marks

| ID | Rubric line | Marks | Requirements | Module | Evidence |
|----|-------------|-------|--------------|--------|----------|
| RUB-C-01 | All ten endpoints to contract, correct status codes, field-level validation errors | 7 | FR-BE-001, FR-BE-002, FR-BE-003, FR-BE-004, FR-BE-005, FR-BE-006, FR-BE-007, FR-BE-008, FR-BE-009, FR-BE-010, FR-BE-029, BR-VAL-004 | M2.1 | Integration tests, OpenAPI schema |
| RUB-C-02 | Four-layer separation: no SQL outside repositories, no business rules in routes | 4 | FR-BE-011, FR-BE-016, NFR-ARCH-001, BR-DATA-003 | M2.1–M2.4 | Static check, code review |
| RUB-C-03 | Status state machine as an explicit transition table; invalid → 409 | 3 | FR-BE-014, BR-STATUS-002/004 | M2.2 | Parametrised tests over every edge |
| RUB-C-04 | `/health` and `/ready` correctly distinguished; `/health` does not touch the DB | 3 | FR-BE-007, FR-BE-008, BR-OPS-001, BR-OPS-002, NFR-REL-004 | M2.1 | Test with a raising session factory; Manual with Postgres stopped |
| RUB-C-05 | Structured JSON logging to stdout with propagated `request_id` | 3 | FR-BE-023, FR-BE-024 | M2.6 | Test, `docker compose logs` capture |
| RUB-C-06 | SIGTERM handled: in-flight requests drain before exit | 2 | FR-BE-021, NFR-REL-003 | M2.5 | Timed demonstration, rollout demo |
| RUB-C-07 | ≥ 14 backend tests, unit and integration, deterministic, coverage ≥ 65 % | 3 | FR-BE-027, NFR-TEST-003 | M2.7 | CI coverage report |

## D · Data layer — 12 marks

| ID | Rubric line | Marks | Requirements | Module | Evidence |
|----|-------------|-------|--------------|--------|----------|
| RUB-D-01 | Alembic migrations; zero schema DDL in application startup code | 4 | FR-DATA-001, FR-BE-022, BR-DATA-001 | M3.1 | CI up/down/up, static check |
| RUB-D-02 | Schema complete incl. `triaged_by`, `ai_summary`, `triage_latency_ms`, timestamptz | 3 | FR-DATA-002 | M3.1 | Migration review, integration test |
| RUB-D-03 | Two indexes, each justified by a named query in the notes — **delivered as three** (`AD-049`), because no two indexes could serve the queries the API issues | 2 | FR-DATA-003, BR-DATA-006, AD-016, AD-049 | M3.2 | Migration + `EXPLAIN` assertions + `ENGINEERING-NOTES.md` |
| RUB-D-04 | Idempotent seed of ≥ 30 realistic complaints; twice changes nothing | 3 | FR-DATA-004, BR-DATA-004, AD-022 | M3.3 | CI seed-twice check |

## E · Cache layer — 10 marks

| ID | Rubric line | Marks | Requirements | Module | Evidence |
|----|-------------|-------|--------------|--------|----------|
| RUB-E-01 | `/api/stats` read-through cache, 30 s TTL, correct `X-Cache` | 3 | FR-CACHE-001, BR-CACHE-002 | M4.1 | Integration test, CI smoke |
| RUB-E-02 | Cache invalidated on write, not left to expire | 2 | FR-CACHE-002, BR-CACHE-003 | M4.1 | Integration test |
| RUB-E-03 | Distributed Redis rate limiter on `POST /api/complaints`, 429 + `Retry-After` | 4 | FR-CACHE-003, FR-CACHE-007, BR-CACHE-004, BR-CACHE-005, BR-CACHE-006 | M4.2 | Integration test, plus the 4-replica proof: exactly 10 × 201 and 20 × 429 out of 30 |
| RUB-E-04 | Redis AOF on a named volume, with written justification | 1 | FR-CACHE-005 | M4.4 | Compose/manifest + notes |

## F · AI layer — 25 marks

| ID | Rubric line | Marks | Requirements | Module | Evidence |
|----|-------------|-------|--------------|--------|----------|
| RUB-F-01 | `TriageProvider` interface with ≥ 3 working implementations selected by env var | 5 | FR-AI-001, FR-AI-002, NFR-ARCH-002 | M5.1–M5.5 | Tests per provider, ADR-0001 |
| RUB-F-02 | Structured output requested **and** validated; malformed rejected safely | 5 | FR-AI-005, BR-TRIAGE-003/004 | M5.6 | Malformed-output tests |
| RUB-F-03 | Timeout, single jittered retry on retryable errors only, fallback, `triaged_by` recorded | 6 | FR-AI-006, FR-AI-007, FR-AI-008, BR-TRIAGE-005/007/008 | M5.6 | The mandatory fallback test + retry-count tests |
| RUB-F-04 | Content-hash caching of triage results with a measured, reported hit rate | 3 | FR-CACHE-004, BR-TRIAGE-011, AD-019 | M4.3, M5 | Test + reported number in `TRIAGE.md` |
| RUB-F-05 | Prompt-injection guardrail plus a test that submits an injection attempt | 3 | FR-AI-010, BR-TRIAGE-010 | M5.7 | Injection test |
| RUB-F-06 | `triage_latency_ms` recorded and surfaced through `/api/meta/providers` | 2 | FR-AI-009, FR-AI-012, BR-TRIAGE-013 | M5.8 | Endpoint response |
| RUB-F-07 | PII/data-governance ADR | 1 | NFR-PRIV-001, AD-003 | M10.2 | `docs/adr/0004-…md` |

## G · Docker and Compose — 15 marks

| ID | Rubric line | Marks | Requirements | Module | Evidence |
|----|-------------|-------|--------------|--------|----------|
| RUB-G-01 | Both images multi-stage, pinned base, non-root, exec-form CMD, cache-correct order | 4 | FR-CTR-001, FR-CTR-002, NFR-PERF-006, NFR-SEC-002 | M6.1, M6.2 | CI image inspection |
| RUB-G-02 | `.dockerignore` per context, before/after context sizes reported | 2 | FR-CTR-003 | M6.1, M6.2 | Numbers in the notes |
| RUB-G-03 | Two networks with `internal: true`; frontend provably cannot reach the DB — **delivered as three** (`AD-002`, `ADR-0005`): `edge`, `internal`, `egress`. The marked property is the isolation, which three networks satisfy; the deviation and its reasoning are in `ADR-0005` and engineering-notes Q7 | 4 | FR-CTR-005, BR-SEC-001, AD-002 | M6.5 | Captured failing `ping` and `getent hosts` |
| RUB-G-04 | Three named volumes, each justified; dev bind mount present, absent from prod | 2 | FR-CTR-007, FR-CTR-008 | M6.5 | Compose files + notes |
| RUB-G-05 | Healthchecks on all services with `depends_on: condition: service_healthy` | 2 | FR-CTR-009 | M6.3 | Compose review |
| RUB-G-06 | `compose.prod.yaml`: `image: ${IMAGE_TAG}`, no `build:`, no published DB/cache port | 1 | FR-CTR-011 | M6.4 | Checker script |

## H · Kubernetes — 20 marks

| ID | Rubric line | Marks | Requirements | Module | Evidence |
|----|-------------|-------|--------------|--------|----------|
| RUB-H-01 | Namespace, Deployments, StatefulSet + PVC, ClusterIP Services, Ingress `/` and `/api` | 5 | FR-K8S-001, FR-K8S-002, FR-K8S-003, FR-K8S-004 | M7.1 | Deploy job, `kubectl get all` |
| RUB-H-02 | ConfigMap and Secret separated; committed manifests carry placeholders only | 2 | FR-K8S-005, BR-SEC-003, AD-027 | M7.2 | Manifest review, secret scan |
| RUB-H-03 | All three probes correct: liveness DB-independent, readiness DB-dependent | 4 | FR-K8S-006, NFR-REL-004 | M7.3 | Manifests + stop-Postgres demo |
| RUB-H-04 | `resources.requests` and `limits` on every container | 2 | FR-K8S-007, NFR-SCALE-002 | M7.4 | Checker script |
| RUB-H-05 | HPA v2 with tuned `behavior`, `hpa -w` capture, replicas-vs-load chart from a real load test | 4 | FR-K8S-008, FR-LOAD-002, NFR-SCALE-003/004 | M7.4, M9.2 | `docs/evidence/hpa-watch.txt`, chart PNG |
| RUB-H-06 | VPA recommender mode, recommendations committed, requests updated, conflict explained | 3 | FR-K8S-009, FR-LOAD-003, NFR-SCALE-005 | M7.5, M9.3 | VPA output + notes Q6 |

## I · CI/CD — 20 marks

| ID | Rubric line | Marks | Requirements | Module | Evidence |
|----|-------------|-------|--------------|--------|----------|
| RUB-I-01 | `ci.yml` lint, type check, backend and frontend tests on every PR, as required checks | 4 | FR-CICD-001, FR-CICD-002, FR-CICD-003, FR-CICD-004 | M8.1 | Workflow + protection settings |
| RUB-I-02 | Compose integration smoke job asserting a real end-to-end request path | 3 | FR-CICD-008 | M8.1 | Pipeline run log |
| RUB-I-03 | Trivy image scan and kubeconform manifest validation in CI | 3 | FR-CICD-006, FR-CICD-007 | M8.1, M8.5 | Pipeline run |
| RUB-I-04 | `cd.yml` with `needs:` gating publish; images in GHCR tagged by commit SHA | 4 | FR-CICD-009, BR-DEL-001/002 | M8.2 | GHCR package page |
| RUB-I-05 | Kubernetes deploy job on an ephemeral cluster, waiting on rollout, smoke-testing the Ingress | 3 | FR-CICD-009 | M8.2 | Pipeline run |
| RUB-I-06 | Secrets from GitHub Secrets, scoped token, least-privilege `permissions:` | 2 | FR-CICD-011, NFR-SEC-007 | M8.5 | Workflow review |
| RUB-I-07 | Evidence of a red pipeline blocking a merge, then green | 1 | FR-CICD-013 | M8.4 | `docs/evidence/blocked-merge-*.png` |

## J · Documentation, portfolio, reflection — 15 marks

| ID | Rubric line | Marks | Requirements | Module | Evidence |
|----|-------------|-------|--------------|--------|----------|
| RUB-J-01 | README: problem, badges, Mermaid diagram, working quickstart, API table, screenshots | 4 | FR-DOC-001, NFR-PORT-004, NFR-DOC-001 | M10.1 | Clean-clone run |
| RUB-J-02 | Four ADRs: provider interface, frontend runtime config, deploy-by-SHA, PII — **delivered as five**, adding `ADR-0005` for the two Tier 1 decisions that had none (`AD-002` three networks, `AD-008` limiter fail-open) | 4 | FR-DOC-002, AD-005, AD-001, AD-034, AD-003, AD-002, AD-008 | M10.2 | `docs/adr/` — five files, each with a status, a real date and a `Decides:` line |
| RUB-J-03 | `docs/RUNBOOK.md`: deploy, roll back, read logs, triage-failure response | 2 | FR-DOC-003, NFR-OPS-003 | M10.3 | Runbook |
| RUB-J-04 | Demo video ≤ 5 min, both partners, prescribed content | 3 | FR-DOC-008 | M10.8 | Video link |
| RUB-J-05 | `docs/ENGINEERING-NOTES.md` answering all eight §5.2 questions with file-and-line references | 2 | FR-DOC-004, NFR-DOC-002 | M10.4 | Notes |

## Bonus — capped at +15

| ID | Item | Marks | Requirements | Module |
|----|------|-------|--------------|--------|
| RUB-X-01 | Zero-downtime rolling update under live load, zero failed requests | +4 | FR-LOAD-004, FR-BE-021, FR-K8S-011 | M9.4 |
| RUB-X-02 | GitOps (Argo CD or Flux) reconciling the cluster from the repository | +4 | — | M7 |
| RUB-X-03 | Deploy by digest with Cosign signing and verification | +3 | AD-034 | M8.2 |
| RUB-X-04 | Prometheus scraping `/metrics` plus a Grafana dashboard screenshot | +2 | FR-BE-009 | M9 |
| RUB-X-05 | OpenTelemetry tracing frontend → backend → LLM | +2 | — | M2.6 |

**Bonus scope, stated explicitly rather than left to a single word.** `AD-012` puts the bonuses out of scope **except `RUB-X-01`**, which is now in scope and required — the brief states the zero-downtime rollout in the body of §3.3 at `:293`, not only as a bonus at `:486`, and `NFR-REL-003` is a `MUST` whose only measure is that demonstration. So `FR-LOAD-004` is a `MUST`, and `RUB-X-01` is claimed as a consequence rather than as an extra.

`RUB-X-02`, `RUB-X-04` and `RUB-X-05` have no requirement and will not be attempted; that is **+8 deliberately declined**, recorded here so it is a decision rather than an oversight. `RUB-X-03` is partially served: `ADR-0003` explains why digest deployment is correct and why it is deferred, which is worth something at viva even unimplemented.

---

## The eight engineering-notes questions (§5.2)

Each is worth part of RUB-J-05 and each has an owning module. Generic answers score zero; each answer must cite the team's own files and lines.

| Q | Question | Owning module | Depends on |
|---|----------|---------------|-----------|
| 1 | Three laptop-vs-CI-runner differences and the exact line that freezes each | M6 | FR-CTR-004, NFR-PORT-003/005 |
| 2 | Where the pipeline sits on the CI/CD maturity ladder; the next rung and what it buys | M8 | FR-CICD-001, FR-CICD-002, FR-CICD-003, FR-CICD-004, FR-CICD-005, FR-CICD-006, FR-CICD-007, FR-CICD-008, FR-CICD-009, FR-CICD-010 |
| 3 | The exact line guaranteeing build-once-deploy-many, and what breaks without it | M1.5, M6 | AD-001, NFR-PORT-001 |
| 4 | What "correct" means for a probabilistic component, and how CI stayed deterministic | M5 | NFR-TEST-001, FR-AI-004 |
| 5 | HPA lag in seconds; where the time went; what would reduce it | M9.2 | FR-LOAD-002, NFR-SCALE-004 |
| 6 | Why VPA is in Off mode; the Auto-mode failure mode alongside the HPA | M7.5 | FR-K8S-009, NFR-SCALE-005 |
| 7 | Where `internal: true` leaves the hosted-LLM caller, and how it was resolved | M6.5 | AD-002, FR-CTR-006 |
| 8 | The failure that cost more than an hour: symptoms, the wrong belief, the line that revealed the truth | All | Kept as a running log from day 1 |

**Note on Q8:** this cannot be written retroactively without lying. `docs/failure-log.md` is created on day one and appended to as things break; one entry is promoted into the notes at the end. **Owner: both developers, appending as it happens** — it was previously assigned to "either", which in a team of two means nobody. `FR-DOC-004` requires all eight answers, so Q8 is not optional.

---

## Pre-submission checklist (walk this backward)

1. `python scripts/check_submission.py` returns clean — and it ran in CI as the required `submission-check` job, not only by hand (`FR-CICD-001`).
2. Every row in sections A–J above has a non-empty evidence column that exists on disk or at the linked URL, **and shows what its name claims.** The script checks existence; only a human checks the claim.
3. Every §5.3 deduction row in `FUNCTIONAL-REQUIREMENTS.md` Appendix A is verified by hand as well as by the script.
4. The four `Partly`-checked business rules in `BUSINESS-RULES.md` §9 are re-verified by eye.
5. The README quickstart (`make up`) is executed from a fresh clone in a fresh directory, on a machine with only Docker and `make`.
6. `git shortlog -sn` shows both partners above 35 %, and the total is at least 35 commits — two separate thresholds, and the count is the one that gets forgotten.
7. `git log --merges main` is non-empty, confirming merge commits were preserved rather than squashed (`FR-CICD-012`).
8. `docs/TRIAGE.md` has all seven sections of `AD-052`, none a placeholder, and the provider rate-limit line carries a date.
9. The six submission items in §5.8 are collected.
10. The mark-total discrepancy (`AD-047`) has been raised with the instructor.


---

## Coverage: requirements with no rubric row

Traceability runs in two directions only if both are complete. These `MUST` requirements deliver no marked line directly — they are prerequisites, guards, or properties the rubric assumes rather than scores. Listed so that "unmapped" means "deliberately unmapped" rather than "overlooked":

| Requirement | Why it has no row |
|---|---|
| `FR-DATA-005` | Persistence across restarts. The brief demands a demonstration at `:128` and the video covers it (`RUB-J-04`), but §4 has no line for it. Genuinely unscored and genuinely required. |
| `FR-BE-012`, `FR-BE-013` | CORS and request-id propagation. Prerequisites for `RUB-B-*` working at all. |
| `FR-BE-015`…`FR-BE-020` | Service and configuration layering. Scored indirectly through `RUB-C-02`. |
| `FR-BE-025`, `FR-BE-026` | Fallback warning and metric instrumentation. Scored through `RUB-C-05` and `RUB-F-06`. |
| `FR-BE-029` | `GET /api/version`. An eleventh endpoint added by `AD-014`; the rubric counts ten. |
| `FR-FE-012`…`FR-FE-019` | Typed client, error boundary, no-business-rules, no-secrets. `RUB-B-04` covers runtime config; the rest are properties, not features. |
| `FR-CACHE-006`, `FR-CACHE-007` | Degradation behaviour and the distributed-limiter proof. `RUB-E-03` marks the limiter; these prove it is correct rather than merely present. |
| `FR-AI-014` | The measured hit rate's data source. `RUB-F-04` marks the reported number; this makes it derivable. |
| `FR-CICD-005`, `FR-CICD-010` | No-publish-on-PR, and `release.yml`. The first is a property of `RUB-I-01`; the second is required by the brief's §3.4 with no rubric line. |
| `FR-K8S-010`, `FR-K8S-012`, `FR-K8S-014` | PDB, Kustomize, rollback. Scored through `RUB-H-01` and `RUB-J-03`. |
| `FR-LOAD-001` | The load script. The input to `RUB-H-05`, not a line itself. |
| `FR-DOC-005`, `FR-DOC-006`, `FR-DOC-007` | AI-usage disclosure, evidence directory, submission checker. The checker guards every §5.3 deduction; the evidence directory is where every other row's proof lives. |
| `FR-PROC-005`, `FR-PROC-006`, `FR-PROC-007` | Viva cross-ownership, credential rotation, credential provisioning. The first multiplies the whole mark; the other two are §5.3 obligations (−20) with no §4 line. |

---

## Appendix — revision history

| Date | Change |
|---|---|
| Round 1 | Initial matrix. |
| 2026-09-25 | Audit remediation (`docs/audit/01-specification-audit.md`). Recorded that the brief's section weights sum to 175 rather than the stated 150, with `AD-047`'s action. Range notation expanded to explicit ID lists so the matrix is checkable in both directions. Malformed `BR-OPS/NFR-REL-004` corrected. Bonus scope stated per item, with `RUB-X-01` moved in-scope and +8 explicitly declined. Q8 given an owner. Pre-submission checklist extended from six items to ten. Added the coverage table above. |
