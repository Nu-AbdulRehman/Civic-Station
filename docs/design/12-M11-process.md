# 12 — M11 Process and collaboration: design and implementation guide

**Owner:** Both
**Delivers:** `RUB-A-01`…`RUB-A-05`, and the viva factor that multiplies everything else. Mark totals are not quoted in design documents (`AD-047`).
**Depends on:** M8 `T-M8-001` (branch protection) on day 1

---

## 1. What this module is for

Fifteen marks come from how the work was done rather than what was built — and the viva factor multiplies the *entire* team mark by how well each partner can explain the submission, including code they did not write.

That second sentence is the one that matters. A team that builds everything and cannot explain half of it scores below a team that builds less and understands all of it.

---

## 2. Branching (`FR-PROC-001`, `BR-DEL-003`)

```
main  ← protected. Merges only: PR + green CI + 1 approval.
 └ dev ← integration branch, all feature branches merge here first
    ├ feat/triage-fallback
    ├ feat/k8s-probes
    └ fix/ratelimit-forwarded-for
```

Branch naming per `AD-042`: `<type>/<area>-<description>`.

**Nothing is committed directly to `main`** (−5). Branch protection makes this mechanical rather than a matter of remembering — which is why `T-M8-001` is a day-1 task, before the history accumulates.

---

## 3. Pull requests (`FR-PROC-002`, 4 marks)

**At least five merged PRs, each linked to an Issue, each with a substantive review comment from the partner.**

"Substantive" means the comment engages with the change: a question about a decision, a caught edge case, a request for a test. "LGTM" is not a review and will be read as not being one.

**Suggested PR boundaries** — natural seams that also keep each PR reviewable:

| PR | Contents | Author |
|---|---|---|
| 1 | Backend skeleton + domain + config + error model | Dev 1 |
| 2 | Images + Compose + networks + volumes | Dev 2 |
| 3 | Data layer: migrations, repositories, seed | Dev 1 |
| 4 | CI pipeline: lint, tests, build, scan, manifests, integration | Dev 2 |
| 5 | AI layer: providers, pipeline, guardrail | Dev 1 |
| 6 | Kubernetes base + overlays + probes + HPA/VPA | Dev 2 |
| 7 | Frontend: three views, client, tests | Dev 1 |
| 8 | CD pipeline + deploy job | Dev 2 |
| 9+ | Evidence, notes, ADR review | Both |

That is eight or nine, comfortably above the floor of five, and each is a coherent unit that a partner can actually review.

**Each PR links an Issue.** Create the Issues from the task tables in the design documents — the task IDs (`T-M5-006` and so on) are already the right granularity, and referencing them in commit messages produces a traceable history for free.

---

## 4. Commits (`FR-PROC-003`, 3 marks)

- **≥ 35 commits total**, Conventional Commit prefixes (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `refactor:`, `chore:`).
- **Neither partner below 35 %** by `git shortlog -sn`.
- **Branch prefixes must cover the same set as the commit prefixes**: `feat/`, `fix/`, `docs/`, `test/`, `ci/`, `refactor/`, `chore/`. A docs-only or test-only branch previously had no legal name, because the branch convention listed three prefixes and the commit convention seven.
- **Branch names carry the task or requirement id**, for example `feat/T-M5-006-triage-pipeline`, so the "every PR links an Issue" rule has a mechanical anchor rather than relying on the PR body.

**These are two separate thresholds and the count is the one that gets forgotten.** A team can satisfy 35 % each with 20 commits between them and still fail the line. Check both.

The 35 % floor is the one to watch under this ownership split (`AD-013`): Dev 1 owns roughly 90 marks of implementation surface and Dev 2 roughly 55, so Dev 1's commit count will naturally run ahead. Check `git shortlog -sn` **mid-week**, not at the end, when there is still time to rebalance. Documentation, evidence and the notes are legitimate commits and are a fair way to level the count — but the better fix is Dev 2 picking up application tasks during the swap (below).

Commit messages reference the requirement or task ID, for example `feat(triage): fall back to rules on provider failure (FR-AI-008)`.

---

## 5. The deliberate merge conflict (`FR-PROC-004`, 3 marks)

**One real conflict, on real code, resolved, with evidence and 2–4 sentences on why that version won.**

Do not manufacture it artificially in a scratch file — the marker is "on real code". The natural opportunity is the **cross-area swap** (§6): both developers touching the same shared surface at the same time. Good candidates:

- `compose.yaml` — Dev 1 adds the Ollama service for M5 while Dev 2 restructures networks for M6.
- `k8s/base/configmap.yaml` — Dev 1 adds a triage variable while Dev 2 reorganises the file.
- `scripts/check_submission.py` — both adding checks.

**Evidence to capture:** the file showing conflict markers, the resolved file, and the merge commit. Plus 2–4 sentences explaining why the surviving version won — not "I kept mine", but the actual reason.

---

## 6. The cross-area swap — mitigating viva risk

The ownership split concentrates knowledge (`AD-013`). The viva deliberately asks each partner about the other's code, and the individual mark is `team mark × viva factor`, where 0.75 is "solid on your own work, shaky on your partner's".

**Two mandatory mechanisms:**

**(a) Assigned cross-area work.** Around the two-thirds point of the week, each developer implements at least one task inside the other's area:

- **Dev 2 implements an application task** — a good choice is `T-M4-005` (rate-limiter fail-open path) or `T-M5-012` (the injection guardrail test). Both are small, self-contained, and force reading the triage pipeline.
- **Dev 1 implements a platform task** — a good choice is `T-M7-004` (probe wiring) or `T-M9-005`. Both force reading the manifests and understanding why liveness must not touch the database.

**(b) Cross-area engineering notes.** Q3 and Q5 are assigned across the boundary (see `11-M10-documentation.md` §5). Writing the answer forces the understanding, and the answer is itself marked.

**Two scheduled walkthrough sessions**, 30–45 minutes each:

| Session | When | Content |
|---|---|---|
| Walkthrough 1 | Mid-week | Dev 1 walks Dev 2 through the triage pipeline, the fallback path and the layering. Dev 2 walks Dev 1 through the networks, the probes and the image structure. |
| Walkthrough 2 | Before the video | Each partner explains the *other's* area unaided, with the repository open. Gaps found here are still fixable; gaps found at the viva are not. |

Walkthrough 2 doubles as video rehearsal.

---

## 7. Viva preparation (`FR-PROC-005`)

Questions this design invites, which both partners should be able to answer regardless of who wrote the code:

| Question | Where the answer lives |
|---|---|
| Why is PostgreSQL a StatefulSet and not a Deployment? | `08-M7` §2 |
| Why does `/health` not touch the database? | `BR-OPS-001` |
| Why does the stats cache have both a TTL and explicit invalidation? | `05-M4` §2.1 |
| Why must the rate limiter be in Redis? | `05-M4` §1 |
| Why is VPA in `Off` mode? | `08-M7` §4.2 |
| What guarantees build-once-deploy-many, exactly? | `ADR-0002` |
| Where does `internal: true` leave the Groq call? | `ADR`/`07-M6` §3.1 |
| Why does the frontend let a user attempt an invalid transition? | `BR-STATUS-005` |
| What does "correct" mean for the classifier, and how is CI deterministic? | `06-M5` §2.6 |
| Why is the Redis volume justified when a cache is rebuildable? | `05-M4` §2.6 |
| What is production running, and how do you know? | `ADR-0003` |

**"Cannot modify it live" is a 0.5 factor.** Practise small live changes: add an enum value end to end, change the rate limit, add a filter. Each should be a five-minute exercise that touches migration, domain, repository, route and frontend types — which is exactly what the layering was for.

---

## 8. Tasks

| ID | Task | Size | Owner | Depends on | Delivers | Done when |
|---|---|---|---|---|---|---|
| **T-M11-001** | Repository setup: `dev` branch, branch protection on `main`, Issue labels | S | Dev 2 | — | FR-PROC-001, RUB-A-01 | Direct push to `main` rejected; screenshot captured |
| T-M11-002 | Issues created from the task tables in all design documents | S | Both | Round 3 | RUB-A-03 | Every `T-*` task has an Issue |
| T-M11-003 | Commit and branch conventions written into `CONTRIBUTING.md`, including the seven prefixes, the id-in-branch-name rule, and merge-commit-not-squash | S | Both | — | FR-PROC-003, FR-CICD-012 | A reader can name a branch and write a commit message without asking |
| **T-M11-004** | Mid-week `git shortlog -sn` balance check and correction | S | Both | mid-week | RUB-A-04 | Both partners above 35 %, or a plan to get there |
| **T-M11-005** | Deliberate merge conflict during the cross-area swap, resolved with evidence | S | Both | T-M11-007 | FR-PROC-004, RUB-A-05 | Markers, resolution, merge commit, and 2–4 sentences captured |
| T-M11-006 | Walkthrough 1 (mid-week) | S | Both | mid-week | FR-PROC-005 | Both partners can describe the other's area |
| **T-M11-007** | Cross-area swap: each developer completes one task in the other's area | M | Both | two-thirds point | FR-PROC-005, AD-013 | Two merged PRs authored across the boundary |
| T-M11-008 | Walkthrough 2 + video rehearsal | S | Both | before recording | FR-PROC-005 | Each partner explains the other's area unaided |
| T-M11-009 | Live-modification practice: add an enum value end to end | S | Both | working system | Viva factor | Done in under ten minutes, without notes |

---

## 9. Standing agreements

- **The pipeline is green or the work is not done** (`BR-DEL-004`). No skipping tests, no `xfail` to get through, no re-running until it passes.
- **Review within a few hours**, not at the end of the day. A one-week schedule cannot absorb overnight review latency.
- **Conflicts on shared files** (`compose.yaml`, `configmap.yaml`, `check_submission.py`) are resolved by talking, not by force-pushing.
- **If your partner is not contributing, raise it early and in writing, not at the end.** The brief's phrasing is "say so in week 1, not week 5" (`:547`); the point is the ratio, not the calendar — escalate in the first fifth of whatever the real timeline is. The viva factor is the anti-free-riding mechanism and is not negotiable afterwards.
- **Merge commits, never squash** (`FR-CICD-012`). `FR-PROC-004` needs a preserved merge commit as marked evidence and the commit floor above needs the individual commits; squash-merging destroys both, silently, as a repository default.
- **If a decision is needed and the two of you disagree**, the owner of the module in question decides and records it as a new row in `OPEN-DECISIONS.md`. Stated because a 15-minute decision rule with no tie-breaker stalls on the one decision that actually matters.
