# 11 — M10 Documentation and portfolio: design and implementation guide

**Owner:** Shared — each developer writes the notes for their own area, plus one from the other's (`AD-013`)
**Depends on:** every other module
**Delivers:** `RUB-J-01`…`RUB-J-05`, and the difference between a working system and a portfolio artefact. Mark totals are not quoted in design documents (`AD-047`).

---

## 1. What this module is for

*A stranger clones your repository and, with one command, has the whole system running with seeded data.* Everything here serves that sentence, plus the viva.

The governing rule is `NFR-DOC-001`: **everything a claim in the README asserts, you can demonstrate.** A README that describes a feature the repository cannot show is worse than one that omits it.

---

## 2. `README.md` (`FR-DOC-001`, 4 marks)

Required contents, in this order:

1. **The problem, in three sentences.** Not the assignment brief — the actual problem: unsorted complaint queues, the burst main behind three streetlight complaints.
2. **Badges.** CI status, CD status, coverage.
3. **Mermaid architecture diagram.** Five services, three networks, the arrows that exist and — worth marking explicitly — the arrow that does not exist between frontend and database.
4. **Quickstart.** One command from a clean clone to a seeded, running system. **Verified from a fresh clone in a fresh directory**, not from the working copy where everything already exists (−5 if it fails).
5. **API table.** The eleven rows from `01-api-contract.md` §13.
6. **Screenshots.** Submit, Dashboard, Stats.
7. **Configuration table.** The environment variable registry from `00-conventions.md` §3.
8. **Links** to the ADRs, the runbook, the engineering notes, and `TRIAGE.md`.
9. **Framework declaration** — the brief requires saying so if Flask is used. We use FastAPI; say that too, with the reason in one line.

---

## 3. ADRs (`FR-DOC-002`)

**Five**, each carrying a status, a real ISO date, the decisions it records, options considered, and consequences:

| File | Decides | `AD` rows |
|---|---|---|
| `0001-provider-interface.md` | The `TriageProvider` seam and the resilience pipeline | `AD-005`, `AD-006`, `AD-007`, `AD-009` |
| `0002-frontend-runtime-config.md` | nginx `/api` proxy, no baked-in URL | `AD-001` |
| `0003-deploy-by-sha.md` | Immutable deployment references, both rollback paths | `AD-034` |
| `0004-pii-and-data-governance.md` | What leaves the machine, redaction, residual risk | `AD-003` |
| `0005-network-topology-and-limiter-degradation.md` | Three networks instead of the brief's two; the limiter fails open | `AD-002`, `AD-008` |

**The fifth was added by the audit.** Both decisions it records are Tier 1 — one deviates from the brief's prescribed topology, the other trades security for availability on the only control guarding a paid resource — and both had been resolved in `OPEN-DECISIONS.md` and implemented in module design documents with no ADR. Those are the two decisions a viva is most likely to probe, and "it is in a module design document" is a weaker answer than a page.

**Which `AD` rows belong to which ADR is now stated in both places**, here and in `OPEN-DECISIONS.md`. The two previously disagreed: the log mapped `AD-005 → ADR-0001` alone while `ADR-0001` claimed four rows.

**Dates are real dates.** All four original ADRs carried `**Date:** Round 2`, which cannot be ordered against the code it describes.

**Task for this module:** review each against what was actually built and correct any drift. An ADR that describes a design the code does not have is worse than no ADR — it is a claim that fails at viva.

Decisions taken later get ADR 0006 onward. **Which decisions need an ADR:** every Tier 1 row in `OPEN-DECISIONS.md`, plus any Tier 2 row that deviates from the brief. The rule is stated because the earlier wording — "further decisions taken during the week get ADR 0005 onward" — covered only future decisions, leaving already-resolved Tier 1 rows such as `AD-002` and `AD-008` with no home and no rule requiring one.

---

## 4. `docs/RUNBOOK.md` (`FR-DOC-003`, 2 marks)

Four sections, each a **command sequence**, not prose (`NFR-OPS-003`):

1. **Deploy** — locally with Compose; to the cluster with Kustomize at a SHA; how the secret is created.
2. **Roll back** — `kubectl rollout undo` (fast, imperative, the 3 a.m. answer) and re-applying the previous overlay at the previous SHA (declarative, auditable, the correct answer once the fire is out). Say when you would use each.
3. **Read logs** — `kubectl logs -n civic-station -l app=backend --tail`, how to filter by `request_id`, the stable event names from `00-conventions.md` §5.
4. **When triage starts failing** — the actual diagnostic path: check `/api/meta/providers` for the fallback rate → check `triage_fallback_total` and its `error_class` label → is it 429 (quota), timeout (provider slow), or validation (prompt drift)? → the remediation for each, including switching `TRIAGE_PROVIDER` to `rules` or `ollama` as a deliberate degradation.

Section 4 is the one that reads as though written by someone who has operated the system. It is worth writing properly.

---

## 5. `docs/ENGINEERING-NOTES.md` (`FR-DOC-004`, 2 marks)

The eight §5.2 questions. **Generic answers score zero.** Every answer cites the team's own files and line numbers.

| Q | Owner | Drafted in task |
|---|---|---|
| 1 — Three laptop/CI differences and the line freezing each | Dev 2 | `T-M6-012` |
| 2 — CI/CD maturity rung, next rung, what it buys | Dev 2 | `T-M8-015` |
| 3 — The line guaranteeing build-once-deploy-many | **Dev 1** *(cross-area)* | The `envsubst` line in the frontend entrypoint (`ADR-0002`) |
| 4 — What "correct" means for a probabilistic component; how CI stayed deterministic | Dev 1 | M5 design §2.6 |
| 5 — HPA lag in seconds, where it went | Dev 1 *(cross-area)* | `T-M9-005` |
| 6 — Why VPA is Off; the Auto failure mode | Dev 2 | `T-M7-014`, `T-M9-007` |
| 7 — Where `internal: true` leaves the hosted-LLM caller | Dev 2 | `T-M6-012` |
| 8 — **The failure that cost more than an hour** | Either | See below |

**Q3 and Q5 are deliberately assigned across the ownership boundary** (`AD-013`), because the viva multiplies the individual mark by how well each partner explains the other's work. Writing the answer forces the understanding.

**Q8 cannot be written retroactively without lying.** Keep `docs/failure-log.md` from day 1: one line per thing that cost real time — the symptom, what you wrongly believed first, and the exact command or log line that told you the truth. At the end, promote the best entry into the notes. Strong candidates, based on where this design is most likely to bite: shell-form `CMD` breaking SIGTERM and therefore the zero-downtime rollout; a missing `resources.requests.cpu` producing `<unknown>/60%`; `X-Forwarded-For` not set so the rate limiter became global; an Alembic downgrade that does not drop the enum type.

---

## 6. `docs/TRIAGE.md` (`FR-AI-013`)

Owned by M5 (`T-M5-013`), listed here because it is a documentation deliverable:

Seven required sections (`AD-052`), each of which something else depends on:

| Section | Depended on by |
|---|---|
| **Pinned model names** — `qwen/qwen3.8-27b`, `llama3.2:1b` | `AD-045`; the env registry defaults must match |
| **The prompt, verbatim**, with `PROMPT_VERSION` | `FR-AI-010`; it exists nowhere else in the document set |
| **The output JSON schema**, verbatim | `FR-AI-005`; the validator is written against it |
| **Observed provider rate limits, with the date seen** | `AD-006`; `AD-017`'s limit of 10/minute is only defensible against a real quota |
| **Measured triage cache hit rate**, naming the counters | `NFR-PERF-004`, `FR-AI-014` — `triage_cache_hits_total / (hits + misses)`, over the stated population |
| **Measured fallback rate** | `AD-007`; it is the honest measure of prompt quality |
| **Groq vs Ollama** over the same seeded inputs: median and p95 latency per provider, agreement rate, quality notes | `RUB-F-*`; the buy-versus-host trade-off measured rather than asserted |

Plus the injection guardrail design and what its test proves.

**`scripts/check_submission.py` fails if any of the seven headings is missing or is followed by fewer than 20 characters** (`FR-AI-013`). Real numbers, with the command used to obtain them. A placeholder here is visible from across the room — and this file previously had seven downstream dependants and did not exist.

---

## 7. `docs/AI-USAGE.md` (`FR-DOC-005`)

Names the AI tools used, which parts they wrote or shaped, and **what was changed afterwards and why**.

Specific disclosure carries no penalty whatsoever. Presenting AI-generated work as original is plagiarism under course policy. More practically: the viva does not care who wrote a line, only whether it can be defended — and a line that cannot be defended is worth nothing regardless of its author.

Given how this project is being built, this file should be substantial and specific. Vagueness here reads worse than the disclosure it is avoiding.

---

## 8. Demo video (`FR-DOC-008`, 3 marks)

**≤ 5 minutes, both partners speaking.** Required beats, and five minutes is tight, so rehearse:

| Beat | Seconds | Shows |
|---|---|---|
| Clean clone → one command → running system | ~45 | Quickstart works |
| Submit a complaint, AI triage returns category/priority/summary/provider | ~45 | The product |
| Force a provider failure → still 201, `triaged_by = rules:fallback` | ~45 | The core engineering |
| `docker compose exec frontend ping database` **fails** | ~20 | Network segmentation |
| HPA scaling under load | ~60 | Real autoscaling |
| Rollback — `rollout undo`, timed | ~45 | Operability |
| Persistence — `down`/`up`, rows survive | ~20 | Durability |

Both partners must speak. Record it on the second-to-last day, not the last — re-recording is common and there must be room for it.

---

## 9. `docs/evidence/` (`FR-DOC-006`)

The complete manifest, gathered from every module:

```
branch-protection.png          blocked-merge-red.png       blocked-merge-green.png
merge-conflict/                network-isolation.txt       hpa-watch.txt
scaling-chart.png              k6-timeseries.json          vpa-recommendation.txt
ratelimit-multireplica.txt     persistence-compose.txt     persistence-k8s.txt
screenshot-submit.png          screenshot-dashboard.png    screenshot-stats.png
zero-downtime.txt              build-context.txt           sigterm.txt
probes.txt                     rollback-timing.txt
```

**Four names changed and four files were added**, so this manifest and `FR-DOC-006` now list the same set:

- `k6-summary.json` → **`k6-timeseries.json`**. The summary is an aggregate; the chart needs a time series (`AD-051`), and naming the file after the aggregate is how the wrong artefact gets committed.
- `replicas-vs-load.png` → **`scaling-chart.png`**, matching `FR-LOAD-002`.
- `zero-downtime-rollout.txt` → **`zero-downtime.txt`**, and **no longer marked `(bonus)`** — it is required (`AD-012`).
- Added **`build-context.txt`** (`FR-CTR-003`), **`sigterm.txt`** (`FR-BE-021`), **`probes.txt`** (`FR-K8S-006`) and **`rollback-timing.txt`** (`FR-K8S-014`) — four requirements produced captures with nowhere named to put them.

`hpa-watch.txt` must carry timestamps (`AD-051`); a capture without them cannot yield the Q5 lag figure.

---

## 10. Tasks

| ID | Task | Size | Owner | Depends on | Delivers | Done when |
|---|---|---|---|---|---|---|
| T-M10-001 | `docs/failure-log.md` created on day 1 and appended to as things break | S | **Both, appending as it happens** | — | RUB-J-05 Q8 | Has entries before the notes are assembled. Q8 cannot be written retroactively without lying, and it was previously assigned to "either", which in a team of two means nobody |
| T-M10-002 | README skeleton: problem, Mermaid diagram, API table, config table | M | Dev 1 | M2 T-M2-001 | FR-DOC-001 | Diagram matches the real topology |
| **T-M10-003** | README quickstart written and verified from a fresh clone — **`make up` verbatim**, on a machine with only Docker and `make` | S | Dev 2 | M6 T-M6-009 | FR-CTR-012, FR-DOC-001 | Works in a directory that has never seen the project. **Carries a −5 deduction** (§5.3), so CI runs the documented command literally rather than reproducing its steps — the deduction is for the *documented* path failing |
| T-M10-004 | README badges + screenshots | S | Dev 1 | M1 T-M1-014, M8 T-M8-002 | FR-DOC-001 | Badges reflect real workflow status |
| T-M10-005 | `RUNBOOK.md` — all four sections as commands | M | Dev 2 | M7 T-M7-013 | FR-DOC-003 | Section 4 is a real diagnostic path |
| T-M10-006 | `ENGINEERING-NOTES.md` assembled from the eight drafted answers | M | Both | Q-drafting tasks | FR-DOC-004 | Every answer has a file:line reference |
| T-M10-007 | ADR review pass against the built system, **all five** | S | Both | end of build | FR-DOC-002 | No ADR describes a design that is not there; each has a status, a real date and a `Decides:` line matching `OPEN-DECISIONS.md` |
| T-M10-012 | `docs/NON-GOALS.md` reviewed against the built system | S | Both | end of build | AD-056, ADR-0004 | Every limitation still true; any that was closed is removed. A stale non-goals page asserts false things about the system |
| T-M10-013 | `docs/INCIDENTS.md` created — a real entry, or the explicit line "No incidents to date." | S | Both | — | FR-PROC-006 | Exists and is unambiguous. An empty file does not distinguish "nothing happened" from "nobody wrote it down" |
| T-M10-008 | `AI-USAGE.md` | S | Both | — | FR-DOC-005 | Specific per area, not a single paragraph |
| T-M10-009 | Evidence directory completeness audit against the manifest | S | Dev 2 | all evidence tasks | FR-DOC-006 | Every filename in §9 exists |
| **T-M10-010** | Demo video recorded, both partners, ≤ 5 min | M | Both | working system | FR-DOC-008 | All seven beats present, under time. The brief lists six at `:482`; the seventh is persistence, which `:128` separately requires a demonstration of |
| T-M10-011 | Submission pack: the six §5.8 items collected | S | Both | T-M10-010 | §5.8 | Repository URL, cd run link, GHCR links, video link, `git shortlog -sn`, HPA capture + chart |
| T-M10-012 | Final `check_submission.py` run + manual deduction walk-through | S | Both | everything | §5.3 | Clean script run **and** a by-hand pass over Appendix A of the FR document |

---

## 11. The backward walk (do this before submitting)

1. `python scripts/check_submission.py` → clean.
2. Every row in `RUBRIC-TRACEABILITY.md` sections A–J has evidence that actually exists.
3. Every §5.3 deduction verified **by hand**, not only by the script.
4. README quickstart run from a fresh clone in a fresh directory.
5. `git shortlog -sn` shows both partners above 35 %.
6. Read the README top to bottom and, for each claim, name the command that demonstrates it. Any claim without one is either demonstrated or deleted.
