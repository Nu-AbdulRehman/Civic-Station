# 02 — The Week: day-by-day plan per developer

**Status:** Authoritative (Round 4)
**Depends on:** `01-work-breakdown-and-critical-path.md`
**Assumes:** the Lever-1 rebalance is applied — `P3`, `P7`, `P9`, `P22` move to Dev 1, and Dev 1 takes the larger share of `S3`

No calendar dates. **Day 1** is whenever the team starts. A "day" here is roughly **10 focused hours**, which is the honest price of compressing a four-week brief into one week (`01-…` §6.2, Lever 2). Agree that on Day 0, not on Day 5.

**★ marks a zero-float package.** A ★ package that slips one half-day slips the whole project, because there is no end buffer.

---

## Day 1 — Foundations, and unblocking Dev 2

**Gate M0 (by midday): `A1` merged, `main` protected.** Dev 2 has only 0.5 blocks of work that does not depend on `A1`. Everything else waits.

| Dev 1 (application) | Dev 2 (platform) |
|---|---|
| **★ A1** — backend skeleton: app factory, all 11 endpoints as stubs, real `/health` and `/ready`, domain enums, transition table, typed settings. **Open the PR before lunch.** | **P1** — create `dev`, protect `main` (PR + CI + 1 approval), create Issues from the design task tables, screenshot the protection settings |
| **A2** — error model + observability middleware (request id, structlog JSON, Prometheus) | *(blocked until `A1` merges — review it, that is the unblocking act)* |
| **A3** — Alembic scaffolding, migration 0001 with all CHECK constraints and a working downgrade, ORM model, index migration | **P2** — backend Dockerfile: multi-stage, pinned, non-root, **exec-form CMD**, HEALTHCHECK, cache-correct layer order, `.dockerignore` with measured context sizes |
| | **P11** — k3d cluster script + metrics-server; verify `kubectl top nodes` returns data |

**End-of-day check:** `alembic upgrade head` works; `docker build` produces a non-root backend image; a direct push to `main` is rejected by the server.

**Why `A2` is on Day 1 despite 2.5 float:** `P6` (Dev 2's CI test jobs) depends on it, and `P6` gates the whole CI chain.

---

## Day 2 — The triage core, and the stack coming up

| Dev 1 | Dev 2 |
|---|---|
| **★ A7** — triage contracts, `RuleBasedTriage` (with Urdu-influenced vocabulary), `SimulatedTriage` with all four failure modes, factory, `redact()` | **P6** — `ci.yml`: lint-and-type, test-backend with service containers, test-frontend |
| **A5** — cache port, stats read-through cache, invalidation | **P4** (start) — `compose.yaml`: five services, **three networks**, three volumes, healthchecks, `service_healthy`, `.env` substitution, dev bind mount |
| **A14** — frontend scaffold, `nginx.conf.template` + `envsubst` entrypoint, generated types, typed API client | |
| **P3** *(swapped in)* — frontend image: node build stage, nginx serve stage, size reported. **Hand to Dev 2 by end of day — `P12` needs it.** | |

**Also today, out of order on purpose:** Dev 1 opens the **`P7` deliberate-failure PR** if there is a spare hour (see Day 4 — it is listed there, but earlier is strictly better; the pipeline is smallest now).

**End-of-day check:** `RuleBasedTriage` returns a valid result for every adversarial input and never raises. The CI lint job fails on a deliberate lint error and passes when fixed.

---

## Day 3 — Everything converges on the backend

| Dev 1 | Dev 2 |
|---|---|
| **★ A8** — triage content-hash cache + outcomes list | **P4** (finish) — **capture `docker compose exec frontend ping database` failing** into `docs/evidence/network-isolation.txt` |
| **★ A9** — **the resilience pipeline**: cache → 10 s timeout → one jittered retry → validate → fallback → one WARNING → metrics. Plus prompt construction and the injection guardrail. *The single highest-value package in the project.* | **★ P12** — k8s base: namespace `civic-station`, both Deployments, postgres **StatefulSet + volumeClaimTemplates**, redis + PVC, four ClusterIP Services, ConfigMap + placeholder Secret |
| **A4** — repositories (with `created_at DESC, id DESC`) + idempotent seed of ≥ 30 complaints | **P10** — `ci.yml` integration job: Compose up, **poll** `/ready` (never sleep), POST/GET, assert category, assert `X-Cache` MISS → HIT, `down -v` |
| **A6** — rate limiter (`INCR`+`EXPIRE`, `X-Forwarded-For` resolution) + fail-open path | |

**Gate M1 (end of day): the stack runs in Compose with seeded data, and the frontend provably cannot reach the database.**

**End-of-day check:** the mandatory test — raising provider → 201 and `triaged_by == "rules:fallback"` — passes against the pipeline, even though routes are still stubs.

---

## Day 4 — The handoff

**This is the riskiest day in the plan.** `A10 → P13` is the only cross-developer dependency on the critical path. Dev 2 cannot wire probes correctly until Dev 1's real `/health` and `/ready` exist.

| Dev 1 | Dev 2 |
|---|---|
| **★ A10 (finish by midday)** — services, all routes wired to real service calls, `/health`, `/ready`, `/metrics`, `/api/version`, lifespan + SIGTERM drain, CORS. **Merge, then tell Dev 2 immediately.** | **P5** — `compose.prod.yaml` (no `build:`, no data ports, resource limits), `.env` hygiene, clean-clone verification — *safe work while waiting for the handoff* |
| **A11** — `LLMTriage` against Groq, `/api/meta/providers` | **★ P13** *(after handoff)* — all three probes, resources.requests/limits (**record the guesses**), Ingress `/` and `/api`, migration init container |
| **P7** *(swapped in)* — deliberate failing-test PR; screenshot red check + blocked merge; fix in the same PR; screenshot green | **★ P14** — HPA v2 with tuned behavior, VPA in `updateMode: "Off"`, PDB, rollout strategy with `preStop` |

**Gate M3 (end of day): running on Kubernetes with correct probes.** Prove it: stop PostgreSQL, watch backend pods leave the Service endpoints *without* their restart count increasing.

**If `A10` is not merged by end of Day 4, the project is one block behind and Lever 3 is already in play.** Say so out loud rather than hoping to catch up.

---

## Day 5 — Scaling, delivery, and the cut decision

| Dev 1 | Dev 2 |
|---|---|
| **A13** — backend test suite to ≥ 14 tests and ≥ 65 % coverage; retry-class accounting; injection test | **★ P15** — Kustomize overlays + kubeconform; image transformer for the SHA tag |
| **A15** — Submit page: mirrored validation, honest loading state, triage result rendering, three error states | **★ P16** — `cd.yml` build-push to GHCR (SHA + latest), Syft SBOM, digest as job output |
| **A16** — Dashboard: server-side list, filters, status control that offers **all** statuses and renders the 409 verbatim | **★ P19** — k6 script (varied filters and pages, ramp/plateau/drop), `kubectl get hpa -w` capture, replicas-vs-load chart |
| **S1** — Walkthrough 1 (45 min, both) | **P8** — `ci.yml` build + Trivy scan + kubeconform manifests jobs |

**Gate M4 (end of day): `kubectl get hpa` shows a real percentage and replicas rise under load.** If it shows `<unknown>/60%`, a `resources.requests.cpu` is missing — fix that before anything else.

### ⚠ The cut checkpoint

**At the end of Day 5, decide.** If M4 has not been reached, pull Lever 3 in order, immediately:

1. Drop **P20** (VPA loop) — saves 1.0 block, costs 3 marks, and **shortens the critical path**
2. Drop **P18** (`release.yml`) — 0.5 block
3. Drop **P23** (zero-downtime bonus) — 0.5 block
4. Drop **A12 + P9** (Ollama; three providers still satisfies Rubric F-01) — 1.0 block

Deciding on Day 7 is deciding too late to act on.

---

## Day 6 — Evidence, and the cross-area swap

| Dev 1 | Dev 2 |
|---|---|
| **A17** — Stats page + `X-Cache` badge + error boundary | **★ P17** — `cd.yml` deploy-k8s: k3d in the runner, apply `overlays/prod` at the SHA, `rollout status`, Ingress smoke test, `get hpa` |
| **A18** — five component tests, lint clean, three screenshots | **★ P20** — VPA loop: recommendation captured, requests updated **as its own commit**, load re-run, HPA behaviour change reported |
| **A12 + P9** — `OllamaTriage` + Ollama service + volume justifications | **★ P21** — multi-replica rate-limit proof, both persistence demos, both rollback mechanisms timed |
| **A19** — `TRIAGE.md` with real measured numbers; static layer check | **P18** — `release.yml`, least-privilege `permissions:`, action pinning |
| **S2** — cross-area swap merges, **deliberate merge conflict resolved**, `git shortlog -sn` balance check | |

**Gate M5/M6 (end of day): a green `cd.yml` run link exists, and every filename in the evidence manifest is on disk.**

**The merge conflict is produced here, naturally**, by both developers touching `compose.yaml` or `k8s/base/configmap.yaml` during the swap. Capture the markers, the resolution, the merge commit, and 2–4 sentences on why the surviving version won.

**Record the demo video today if the system is stable** — Day 7 leaves no room for a re-record, and re-records are normal.

---

## Day 7 — Assembly and submission

| Dev 1 | Dev 2 |
|---|---|
| **P22** *(swapped in)* — `scripts/check_submission.py` covering every §5.3 check plus the layer checks | **★ P24** — `RUNBOOK.md` (four sections as commands, including the triage-failure diagnostic path) + notes Q1, Q2, Q6, Q7 |
| **★ S3** — README assembly, Mermaid diagram, API table, badges, screenshots; notes **Q3, Q4, Q5**; ADR review pass; `AI-USAGE.md` | **P25** — evidence directory audit against the manifest |
| | **P23** — zero-downtime rollout under load (**bonus, only if everything else is green**) |
| **★ S4** — Walkthrough 2: each partner explains the *other's* area unaided. Live-modification practice. Video rehearsal. | |
| **★ S5** — record the demo video, both partners, ≤ 5 minutes, all seven beats | |
| **★ S6** — `check_submission.py` clean; manual walk of every §5.3 deduction; collect the six §5.8 submission items | |

**Gate M8: submitted.** Late submissions are not accepted and there is no retake. **Submit something imperfect on time.**

---

## Ordering rules, when the plan meets reality

1. **★ before everything.** A zero-float package outranks a more interesting one, always.
2. **Unblock your partner before you continue.** Reviewing a PR that unblocks the other developer beats another hour of your own work. On Day 1 and Day 4 this is the single highest-value thing either person can do.
3. **When behind, take from the float table, not from the rubric.** `A12`/`P9` (6.5 float) and `A15`–`A18` (7.0 float) absorb delay. Rubric marks do not.
4. **Frontend is the buffer.** `A15`–`A18` have 7 blocks of float and are the work most safely interrupted and resumed. They are *not* a cut candidate — Rubric B is 18 marks.
5. **Never trade away a test to save time.** The pipeline is green or the work is not done (`BR-DEL-004`). A skipped test is a mark lost plus a viva question you cannot answer.
6. **Evidence is not cleanup.** `P19 → P20 → P24 → S3 → S5` is a serial chain on the critical path occupying the last two-and-a-half days. Treating documentation as end-of-week filler is precisely how this plan fails.

---

## Standing daily rhythm

| When | What | Duration |
|---|---|---|
| Start of day | Standup: what I finished, what I am on, what is blocking me, **which ★ package is at risk** | 10 min |
| Midday | Handoff check — anything the other person is waiting on gets merged or explicitly deferred with a reason | 5 min |
| End of day | Gate check against the day's milestone; update the float table if anything slipped; open PRs for review overnight | 15 min |

**Review latency is the silent killer in a one-week plan.** A PR that waits overnight costs a block. Reviews happen within a few hours, not at end of day.

---

## Risk register

| Risk | Likelihood | Impact | Mitigation | Trigger |
|---|---|---|---|---|
| `A10 → P13` handoff slips | **High** | Project slips 1 block, no buffer | `A1` skeleton on Day 1 lets Dev 2 build almost everything before the handoff; Dev 2 has `P5` queued as safe waiting work | `A10` not merged by end of Day 4 |
| HPA reads `<unknown>/60%` | **High** | M4 missed, blocks P19→P20→P24 | `resources.requests` is its own task (`T-M7-005`) with its own check | `kubectl get hpa` on Day 4 |
| SIGTERM not received (shell-form `CMD`) | Medium | Zero-downtime demo fails; looks like a Kubernetes bug | Exec-form `CMD` is an explicit acceptance criterion on `P2`, Day 1 | Rollout drops requests |
| Rate limiter global because `X-Forwarded-For` is unset | Medium | 4 marks; invisible in single-client testing | Two-distinct-IP test is an acceptance criterion on `A6` | Two browsers share a quota |
| Alembic downgrade leaves the enum type | Medium | CI up/down/up fails | Explicit `DROP TYPE` called out in `04-M3-data.md` §2.3 | CI migration job red |
| k6 produces a flat CPU line | Medium | No scale-out to capture | Vary filters and page numbers; use `/api/stats` only as minority traffic | Backend CPU below target under plateau |
| Dev 2 oversubscribed | **High** | Platform work compresses least under AI assistance | Lever 1 rebalance, applied from Day 1 | Dev 2 more than half a day behind at any gate |
| Commit balance below 35 % | Medium | 3 marks | `T-M11-004` mid-week check | `git shortlog -sn` on Day 4 |
| Video re-record needed | Medium | Day 7 has no room | Record on Day 6 | System stable on Day 6 |
| Q8 (the failure) written retroactively | Medium | Reads as fiction; 2 marks | `docs/failure-log.md` kept from Day 1 | Empty log on Day 4 |
