# Civic-Station — Documentation Index

This directory is the project's specification. It is written to be executed: an AI coding agent should be able to implement Civic-Station from these documents without re-reading the original assignment brief, and without inventing a business rule.

**Status:** planning complete, audited, and remediated. Implementation can begin.
**Last audit:** 2026-09-25 — [`audit/01-specification-audit.md`](audit/01-specification-audit.md). Read its short list before starting.

---

## Documents

Every path below is a link, so a broken reference is findable rather than merely plausible.

### The brief

| Document | What it is |
|---|---|
| [`planning/Civic-Station_Problem_Statement.md`](planning/Civic-Station_Problem_Statement.md) | The original assignment. **Never edited** — it is the external contract. Note that it contains two arithmetic errors of its own, recorded in `AD-047`. |

### Requirements — what and why

| Document | What it is | Owner |
|---|---|---|
| [`requirements/MODULE-MAP.md`](requirements/MODULE-MAP.md) | 11 modules, canonical identifiers. `M1`–`M11` always mean modules here. | Both |
| [`requirements/FUNCTIONAL-REQUIREMENTS.md`](requirements/FUNCTIONAL-REQUIREMENTS.md) | Every `FR`, with acceptance criteria and a verification method | Both |
| [`requirements/NON-FUNCTIONAL-REQUIREMENTS.md`](requirements/NON-FUNCTIONAL-REQUIREMENTS.md) | Every `NFR`, in 12 categories, each with a stated measurement | Both |
| [`requirements/BUSINESS-RULES.md`](requirements/BUSINESS-RULES.md) | The invariants. **Read before writing any code.** | Both |
| [`requirements/RUBRIC-TRACEABILITY.md`](requirements/RUBRIC-TRACEABILITY.md) | Rubric line ↔ requirement ↔ module ↔ evidence, in both directions | Both |

### Decisions

| Document | What it is |
|---|---|
| [`decisions/OPEN-DECISIONS.md`](decisions/OPEN-DECISIONS.md) | 56 decisions, all RESOLVED. **The resolution log at the bottom is authoritative** — where a design document disagrees with it, the log wins. |
| [`adr/0001-provider-interface.md`](adr/0001-provider-interface.md) | The `TriageProvider` seam and the resilience pipeline |
| [`adr/0002-frontend-runtime-config.md`](adr/0002-frontend-runtime-config.md) | nginx `/api` proxy, no baked-in URL |
| [`adr/0003-deploy-by-sha.md`](adr/0003-deploy-by-sha.md) | Immutable deployment references, both rollback paths |
| [`adr/0004-pii-and-data-governance.md`](adr/0004-pii-and-data-governance.md) | What leaves the machine, and why that is acceptable |
| [`adr/0005-network-topology-and-limiter-degradation.md`](adr/0005-network-topology-and-limiter-degradation.md) | Three networks instead of the brief's two; the limiter fails open |

### Design — how

| Document | Module | What it owns |
|---|---|---|
| [`design/00-conventions.md`](design/00-conventions.md) | shared | Layout, the environment-variable registry, the error model, the log schema, metric names |
| [`design/01-api-contract.md`](design/01-api-contract.md) | shared | The wire format, and 30 contract tests |
| [`design/02-M1-frontend.md`](design/02-M1-frontend.md) | M1 | Three views, runtime configuration, the typed client |
| [`design/03-M2-backend.md`](design/03-M2-backend.md) | M2 | Four layers, middleware order, lifecycle |
| [`design/04-M3-data.md`](design/04-M3-data.md) | M3 | Schema, three indexes, migrations, seed |
| [`design/05-M4-cache.md`](design/05-M4-cache.md) | M4 | Five keyspaces, the distributed limiter, degradation |
| [`design/06-M5-ai-triage.md`](design/06-M5-ai-triage.md) | M5 | Four providers, the resilience pipeline, the guardrail |
| [`design/07-M6-containers.md`](design/07-M6-containers.md) | M6 | Two images, three networks, three volumes |
| [`design/08-M7-kubernetes.md`](design/08-M7-kubernetes.md) | M7 | Manifests, probes, HPA and VPA, rollout |
| [`design/09-M8-cicd.md`](design/09-M8-cicd.md) | M8 | Three workflows, eight required checks, gates |
| [`design/10-M9-load-evidence.md`](design/10-M9-load-evidence.md) | M9 | The load profile, scaling evidence, the VPA loop |
| [`design/11-M10-documentation.md`](design/11-M10-documentation.md) | M10 | README, five ADRs, runbook, notes, evidence manifest |
| [`design/12-M11-process.md`](design/12-M11-process.md) | M11 | Branches, PRs, commits, the conflict, viva prep |

### Audit and scope

| Document | What it is |
|---|---|
| [`audit/01-specification-audit.md`](audit/01-specification-audit.md) | 136 specification defects found on 2026-09-25, banded by severity, with the deviation register and the method. **Start with its short list.** |
| [`NON-GOALS.md`](NON-GOALS.md) | What this system deliberately does not do, what each gap leaves open, and where the work would attach |

### Not part of the reading order

| Document | Why |
|---|---|
| [`schedule/01-work-breakdown-and-critical-path.md`](schedule/01-work-breakdown-and-critical-path.md) | Plans a one-week build that is not being followed. Its `M0`–`M8` milestone labels also collide with the module IDs. Defects recorded in the audit's Appendix A; not remediated. |
| [`schedule/02-weekly-plan.md`](schedule/02-weekly-plan.md) | As above |
| [`schedule/03-collaboration-protocol.md`](schedule/03-collaboration-protocol.md) | As above — though its ownership split (`AD-013`) and its standing agreements are still the ones in force, and `design/12-M11-process.md` carries the same material |

### Produced during implementation

None of these exists yet. Each is required, and each has an owning requirement.

| Path | Required by |
|---|---|
| `ENGINEERING-NOTES.md` | `FR-DOC-004` — the eight §5.2 answers, each citing a `path:line`, plus eight further items |
| `RUNBOOK.md` | `FR-DOC-003` — deploy, both rollbacks with timings, logs, credential rotation, triage failure |
| `TRIAGE.md` | `FR-AI-013`, `AD-052` — seven sections, seven downstream dependants |
| `AI-USAGE.md` | `FR-DOC-005` |
| `INCIDENTS.md` | `FR-PROC-006` — a real entry, or the explicit line "No incidents to date." |
| `failure-log.md` | `T-M10-001` — kept from day one, because Q8 cannot be written retroactively |
| `evidence/` | `FR-DOC-006` — 14 named artefacts |

---

## Reading order for an implementing agent

1. [`requirements/MODULE-MAP.md`](requirements/MODULE-MAP.md) — learn the identifiers.
2. [`requirements/BUSINESS-RULES.md`](requirements/BUSINESS-RULES.md) — learn what must never break. **Before writing any code.**
3. [`design/00-conventions.md`](design/00-conventions.md) — layout, error model, log schema, env registry, metric names. Shared and non-negotiable.
4. [`design/01-api-contract.md`](design/01-api-contract.md) — if your module touches HTTP at all.
5. [`requirements/FUNCTIONAL-REQUIREMENTS.md`](requirements/FUNCTIONAL-REQUIREMENTS.md) — the section for your module.
6. [`requirements/NON-FUNCTIONAL-REQUIREMENTS.md`](requirements/NON-FUNCTIONAL-REQUIREMENTS.md) — the quality constraints on it.
7. [`decisions/OPEN-DECISIONS.md`](decisions/OPEN-DECISIONS.md) resolution log, plus the five ADRs — **every decision is RESOLVED; do not re-decide one.**
8. [`design/<NN>-<module>.md`](design/) — your module's implementation guide and task table.
9. [`audit/01-specification-audit.md`](audit/01-specification-audit.md) — the known defects and the deviations from the brief.
10. [`NON-GOALS.md`](NON-GOALS.md) — before proposing anything that looks missing.
11. [`requirements/RUBRIC-TRACEABILITY.md`](requirements/RUBRIC-TRACEABILITY.md) — before submitting, walked backward.

---

## Quick facts

| | |
|---|---|
| Modules | 11 |
| Decisions | 56, all resolved. `AD-045`–`AD-056` were added by the audit |
| ADRs | 5 |
| Contract tests | 30, in `design/01-api-contract.md` §14 |
| Evidence artefacts | 14 named files, in `FR-DOC-006` |
| Mark total | **Unresolved.** The brief says 150; its own section weights sum to 175. See `AD-047` — raise it with the instructor. No document here quotes a total. |
| Deviations from the brief | 6, each with its mark exposure, in the audit's deviation register |
| Highest-value module | M5, the AI layer — the one §5.1 says never to cut |
| Deliberately out of scope | Authentication, Kubernetes `NetworkPolicy`, a global spend cap, data retention, image signing. All in [`NON-GOALS.md`](NON-GOALS.md) |

---

## Rules for anyone editing these documents

- The problem statement in `planning/` is never edited. It is the external contract.
- **The resolution log in `decisions/OPEN-DECISIONS.md` wins** over any design document that disagrees with it.
- A business rule changes only with an explicit note of what changed and why. Rules cascade into tests and into database constraints; a silent change makes a green suite meaningless.
- A change to [`design/01-api-contract.md`](design/01-api-contract.md) touches four modules (M1, M2, M8, M9). Both developers agree, in one PR. If they cannot, the module owner decides and records a new `AD` row.
- Every requirement keeps its ID forever. Superseded requirements are marked superseded, not deleted, so that tests and commit messages referencing them stay meaningful.
- A new decision becomes a new row in the `OPEN-DECISIONS.md` resolution log, not a comment in a file.
- Evidence artefacts live in `evidence/` with the filenames named in `FR-DOC-006` and [`design/11-M10-documentation.md`](design/11-M10-documentation.md) §9. The two lists must match.
- **When a limitation in [`NON-GOALS.md`](NON-GOALS.md) is closed, remove its entry in the same change.** A stale non-goals page asserts false things about the system.
