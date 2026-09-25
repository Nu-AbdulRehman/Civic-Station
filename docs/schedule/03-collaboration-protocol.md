# 03 — Collaboration Protocol

**Status:** Authoritative (Round 4)
**Depends on:** `01-work-breakdown-and-critical-path.md`, `02-weekly-plan.md`, `docs/design/12-M11-process.md`

This document is the organisational half of the plan: who owns what, how work moves between the two developers, how disagreements are settled, and what happens when the schedule slips. Rubric A is 15 marks for exactly this, and the viva factor multiplies everything else by how well each partner understands the other's work.

---

## 1. Ownership

Per `AD-013`, with the Lever-1 rebalance from `01-…` §6.2 applied.

| | Dev 1 — **Application** | Dev 2 — **Platform** |
|---|---|---|
| **Owns** | M1 frontend, M2 backend, M3 data, M5 AI/triage, M4 application side | M6 containers, M7 Kubernetes, M8 CI/CD, M9 load & scaling, M4 operations side |
| **Also carries** (rebalance) | `P3` frontend image, `P7` merge-block evidence, `P9` Ollama service, `P22` submission checker, the larger share of `S3` | |
| **Marks surface** | ~90 | ~55 |
| **Irreducible hours** | Lower — application work compresses well under AI assistance | **Higher** — CI iteration, cluster debugging and evidence capture are wall-clock bound |

**The asymmetry is deliberate and worth stating:** Dev 1 owns more marks, Dev 2 owns more hours. Neither is the harder job. The rebalance exists because AI assistance shortens writing, not waiting.

**Shared, jointly owned:** M10 documentation, M11 process, the engineering notes, the video, the submission pack.

---

## 2. Branch and PR flow

```
main   ← protected: PR required, CI required, ≥ 1 approval, no direct push
 └ dev ← integration branch; everything merges here first
    ├ feat/<area>-<desc>
    ├ fix/<area>-<desc>
    └ ci/<desc>
```

**Rules:**

- Every work package becomes one PR, or a small number of them. The package boundaries in `01-…` were chosen to be reviewable units.
- Every PR links an Issue. The Issues come from `T-M11-002`, generated from the design-document task tables — so the task IDs (`T-M5-006`, …) are already the right granularity.
- Every PR carries a **substantive** review comment from the other developer. A question about a decision, a caught edge case, a request for a test. "LGTM" is not a review and will be read as not being one.
- Commit messages: Conventional Commits, referencing the requirement — `feat(triage): fall back to rules on provider failure (FR-AI-008)`.
- **Target: 8–9 merged PRs**, comfortably above the floor of 5.

### 2.1 Review service level

**A PR that waits overnight costs a block, and the week has no buffer.**

| Situation | Response time |
|---|---|
| PR blocks a ★ (zero-float) package | **Within the hour.** Interrupt what you are doing. |
| PR blocks the other developer at all | Within a few hours |
| Everything else | Same day |

On Day 1 and Day 4, reviewing your partner's PR is the highest-value thing either person can do. `A1` blocks Dev 2 entirely; `A10` blocks the entire critical path.

### 2.2 The two handoffs that matter

| Handoff | When | What Dev 2 does while waiting |
|---|---|---|
| **`A1` → `P2`** — backend skeleton to backend image | Day 1, by midday | `P1` repo governance, `P11` cluster setup |
| **`A10` → `P13`** — real `/health` and `/ready` to probe wiring | Day 4, by midday | `P5` production Compose, `.env` hygiene, clean-clone verification |

Both are announced explicitly — "A10 is merged, probes are unblocked" — not inferred from a notification. A handoff nobody noticed is a handoff that did not happen.

---

## 3. Shared-file protocol

Four files both developers will touch. Conflicts here are expected, and one of them is a deliverable.

| File | Owner of record | Protocol |
|---|---|---|
| `compose.yaml` | Dev 2 | Dev 1 requests service additions (e.g. Ollama) rather than editing directly — except during the Day 6 swap, where the conflict is the point |
| `k8s/base/configmap.yaml` | Dev 2 | Dev 1 supplies the variable name and value; Dev 2 places it |
| `scripts/check_submission.py` | Dev 1 (after rebalance) | Dev 2 supplies the §5.3 infrastructure checks as a list; Dev 1 implements |
| `.env.example` | Dev 2 | Any new variable is added by whoever introduces it, in the same PR |

**Conflicts are resolved by talking, never by force-push.** `git push --force` to a shared branch is prohibited; force-push to your own unmerged feature branch is fine.

---

## 4. The deliberate merge conflict (3 marks)

**Do not manufacture it in a scratch file.** The rubric says "on real code", and a contrived conflict reads as contrived.

**Produce it naturally during the Day 6 cross-area swap**, when both developers are touching the same shared surface. Best candidates, in order:

1. `compose.yaml` — Dev 1 adds the Ollama service (`P9`) while Dev 2 restructures networks or resource limits.
2. `k8s/base/configmap.yaml` — Dev 1 adds a triage variable while Dev 2 reorganises the file.
3. `scripts/check_submission.py` — both adding checks.

**Capture:** the file with conflict markers, the resolved file, the merge commit hash, and **2–4 sentences on why the surviving version won** — the actual reason, not "I kept mine". Store under `docs/evidence/merge-conflict/`.

---

## 5. The cross-area swap (viva insurance)

The ownership split concentrates knowledge. The viva deliberately asks each partner about the other's code, and **individual mark = team mark × viva factor**, where 0.75 is "solid on your own work, shaky on your partner's" and 0.5 is "describes what the code does but not why, cannot modify it live".

Three mechanisms, all mandatory, all already in the schedule:

### 5.1 Assigned cross-area implementation (Days 4–6)

| Developer | Crosses into | Package |
|---|---|---|
| Dev 1 | Platform | `P3` (frontend image), `P7` (CI merge-block evidence), `P9` (Ollama service), `P22` (submission checker) |
| Dev 2 | Application | One of `T-M4-005` (rate-limiter fail-open) or `T-M5-012` (injection guardrail test) — both small, self-contained, and both force reading the triage pipeline |

Dev 1's crossing is larger because it doubles as the capacity rebalance.

### 5.2 Cross-assigned engineering notes

| Question | Written by | About |
|---|---|---|
| **Q3** — the exact line guaranteeing build-once-deploy-many | **Dev 1** | Dev 2's territory (the `envsubst` line in the frontend entrypoint) |
| **Q5** — HPA lag in seconds and where it went | **Dev 1** | Dev 2's load test |
| Q1, Q2, Q6, Q7 | Dev 2 | Dev 2's own area |
| Q4 | Dev 1 | Dev 1's own area |
| Q8 — the failure | Either | Whoever had the better failure |

Writing the answer forces the understanding, and the answer is itself marked.

### 5.3 Two walkthroughs

| Session | Day | Format |
|---|---|---|
| **Walkthrough 1** | Day 5, ~45 min | Dev 1 walks Dev 2 through the triage pipeline, the fallback path, and the four-layer separation. Dev 2 walks Dev 1 through the three networks, the three probes, and the image structure. Questions encouraged; nobody defends anything. |
| **Walkthrough 2** | Day 7, ~45 min | Reversed and unaided: each partner explains the **other's** area with the repository open and no help. Gaps found here are still fixable. Gaps found at the viva are not. Doubles as video rehearsal. |

### 5.4 Live-modification drill

"Cannot modify it live" is a 0.5 viva factor — it halves the team mark. Practise one end-to-end change until it takes under ten minutes without notes:

**Add a new complaint category.** It touches the domain enum, an Alembic migration (`ALTER TYPE`), the rules classifier keywords, the frontend's generated types, the seed data, and the stats zero-fill. Six files, one coherent change — which is exactly what the layering was built for, and exactly the kind of thing an examiner asks for.

---

## 6. Commit balance (3 marks)

**Neither partner below 35 % by `git shortlog -sn`.**

This split puts Dev 1 ahead by default — roughly 90 marks of implementation surface versus 55. Watch it:

- **Check on Day 4** (`T-M11-004`), not on Day 7.
- If Dev 2 is trending low, the correction is the swap tasks in §5.1 plus taking a larger share of the notes and evidence commits — not padding with trivial commits, which is visible and reads badly.
- Documentation, evidence and manifest commits count and are legitimate work.

---

## 7. Decision-making and disagreement

| Situation | Resolution |
|---|---|
| Disagreement inside one person's ownership area | The owner decides. The other may record an objection in the PR; it is not a blocker. |
| Disagreement on a shared file or a cross-cutting contract | Check `docs/decisions/OPEN-DECISIONS.md` first — it is probably already decided. If genuinely new: decide in under 15 minutes, record it as a new row in the resolution log, move on. |
| A decision would change a **business rule** | Stop. Rules cascade into tests and into the database. Changing one requires an explicit note of what changed and why, in `BUSINESS-RULES.md`. |
| A decision would change the **API contract** | It touches four modules (M1, M2, M8, M9). Both developers agree, and `01-api-contract.md` is updated in the same PR. |
| Schedule slip | Declare it at the next standup. Consult the float table. Pull from float before pulling from scope, and from the `AD-012` cut order before pulling from the rubric. |

**Nothing is decided silently.** A decision that only exists in one person's head is a viva question the other person will fail.

---

## 8. Escalation and the honest conversation

The brief is explicit: *if your partner is not contributing, say so in week 1, not week 5.* In a one-week build, that means **by the Day 3 standup**.

The signal is not "my partner is slow" — platform work genuinely produces fewer visible commits per hour. The signal is a **missed gate with no communication**: a ★ package not merged, not flagged at standup, and not explained.

The protocol: raise it at the standup, in terms of the gate rather than the person ("M3 is not met and I do not know where we are"), reassign against the float table, and if it persists past a second gate, escalate to the instructor before the submission rather than after. The viva factor is the anti-free-riding mechanism and is not negotiable afterwards.

---

## 9. Definition of done — team level

A work package is done when **all** of these are true:

1. The `Done when` condition in the design document is demonstrably true.
2. Business rules it touches are honoured — checked against `BUSINESS-RULES.md`, not from memory.
3. Lint and type checks pass; the pipeline is green.
4. A test exists if the package added non-trivial logic.
5. The PR is merged, linked to an Issue, and carries a substantive review from the other developer.
6. Any evidence artefact the package produces is committed to `docs/evidence/` with the filename the manifest expects.
7. Nothing secret entered the working tree.

**The pipeline is green or the work is not done.** No skipped tests, no `xfail` to get through a gate, no re-running until it passes.

---

## 10. The one-page summary

- **Dev 1** owns the application. **Dev 2** owns the platform. Dev 1 carries four platform packages as rebalance and as viva insurance.
- **Two handoffs decide the week:** `A1` on Day 1 morning, `A10` on Day 4 morning. Announce both explicitly.
- **Reviews within the hour** when they block a ★ package. Overnight review latency costs a block the schedule does not have.
- **Decide fast, record always.** Fifteen minutes, then write it in the resolution log.
- **The Day 5 checkpoint is the cut decision.** Pull Lever 3 in order; do not renegotiate the order at the moment of pain.
- **Walkthroughs are not optional.** The viva multiplies everything by how well you explain the code you did not write.
- **Submit something imperfect on time.** Late submissions are not accepted and there is no retake.
