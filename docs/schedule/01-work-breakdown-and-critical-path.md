# 01 — Work Breakdown and Critical Path

**Status:** Authoritative (Round 4)
**Depends on:** the task tables in `docs/design/*`
**Companions:** `02-weekly-plan.md`, `03-collaboration-protocol.md`

---

## 1. Method and units

The 132 tasks in the design documents are too fine-grained to schedule directly — a 132-node network is a diagram nobody reads. They are grouped into **50 work packages** (19 application, 25 platform, 6 shared), each roughly a half-day of focused work, and the critical path is computed over the packages.

**Unit: 1 block = one half-day of focused work ≈ 4 hours.**
**Nominal capacity: 2 blocks per developer per day, 7 days = 14 blocks each, 28 total.**

No calendar dates. Day 1 is whenever the team starts.

Package IDs: `A*` = application (Dev 1), `P*` = platform (Dev 2), `S*` = shared.

---

## 2. Work packages — application (Dev 1)

| WP | Name | Tasks | Dur | Depends on |
|----|------|-------|-----|------------|
| **A1** | Backend skeleton, domain, config | T-M2-001/002/003 | 1.0 | — |
| A2 | Error model + observability middleware | T-M2-004/005 | 1.0 | A1 |
| A3 | Alembic, migration, ORM, indexes | T-M3-001…004 | 1.0 | A1 |
| A4 | Repositories + seed | T-M2-006, T-M3-005/006 | 1.0 | A3 |
| A5 | Cache port + stats cache + invalidation | T-M4-001/002/003 | 0.5 | A1 |
| A6 | Rate limiter + fail-open | T-M4-004/005 | 1.0 | A5 |
| **A7** | Triage contracts, rules, simulated, factory, redact | T-M5-001…005 | 1.5 | A1 |
| **A8** | Triage cache + outcomes list | T-M4-006/007 | 0.5 | A5, A7 |
| **A9** | Triage pipeline + prompt/guardrail | T-M5-006/007 | 1.5 | A7, A8 |
| **A10** | Services, routes, ops endpoints, lifespan, CORS | T-M2-007…013 | 1.5 | A2, A4, A6, A9 |
| A11 | LLMTriage (Groq) + `/api/meta/providers` | T-M5-008/010 | 1.0 | A9, A10 |
| A12 | OllamaTriage | T-M5-009 | 0.5 | A9, P9 |
| A13 | Backend test suite to threshold | T-M2-015, T-M5-011/012, T-M3-007/008 | 1.5 | A10, A11 |
| A14 | FE scaffold, nginx template, types, client | T-M1-001…004 | 1.0 | A1 |
| A15 | Submit page + error states | T-M1-005/006 | 1.0 | A14 |
| A16 | Dashboard, filters, status control | T-M1-007/008/009 | 1.0 | A14 |
| A17 | Stats page + error boundary | T-M1-010/011 | 0.5 | A14 |
| A18 | FE tests, lint, screenshots | T-M1-012/013/014 | 1.0 | A15, A16, A17 |
| A19 | `TRIAGE.md` + static layer check | T-M5-013, T-M2-014 | 0.5 | A11, A12, A13 |

**Subtotal: 19.0 blocks**

---

## 3. Work packages — platform (Dev 2)

| WP | Name | Tasks | Dur | Depends on |
|----|------|-------|-----|------------|
| P1 | Repo governance: `dev`, protection, Issues | T-M11-001/002, T-M8-001 | 0.5 | — |
| P2 | Backend image + `.dockerignore` | T-M6-001/002 | 1.0 | A1 |
| P3 | Frontend image | T-M6-003 | 0.5 | A14 |
| P4 | `compose.yaml`, networks, volumes, isolation proof, migrate/seed | T-M6-004/005/006 | 1.5 | P2, P3 |
| P5 | `compose.prod.yaml`, env hygiene, clean-clone check | T-M6-007/008/009 | 1.0 | P4 |
| P6 | `ci.yml` lint + backend/frontend test jobs | T-M8-002/003/004 | 1.0 | P1, A2 |
| P7 | Red/green merge-block evidence | T-M8-013 | 0.5 | P6 |
| P8 | `ci.yml` build + scan + manifests jobs | T-M8-005/006/007 | 0.5 | P6, P2, P3, P13 |
| P9 | Ollama service + volume justifications | T-M6-010/011 | 0.5 | P4 |
| P10 | `ci.yml` integration job | T-M8-008 | 1.0 | P4, P6 |
| P11 | k3d cluster + metrics-server | T-M7-001, T-M9-002 | 0.5 | P1 |
| **P12** | k8s base manifests, ConfigMap, Secret | T-M7-002/003 | 1.5 | P2, P3, P11 |
| **P13** | Probes, resources, ingress, migration job | T-M7-004…007 | 1.0 | P12, **A10** |
| **P14** | HPA, VPA, PDB, rollout strategy | T-M7-008/009/010 | 1.0 | P13 |
| **P15** | Kustomize overlays + kubeconform | T-M7-011 | 0.5 | P14 |
| **P16** | `cd.yml` build-push to GHCR | T-M8-009 | 0.5 | P10, P15 |
| **P17** | `cd.yml` deploy-k8s on ephemeral cluster | T-M8-010 | 1.0 | P16 |
| P18 | `release.yml`, permissions, action pinning | T-M8-011/012 | 0.5 | P16 |
| **P19** | k6 script, HPA capture, chart | T-M9-001/003/004 | 1.0 | P14 |
| **P20** | VPA loop + conflict write-up | T-M9-006/007 | 1.0 | P19 |
| **P21** | Multi-replica limiter, persistence demos, rollback | T-M9-008, T-M7-012/013, T-M3-009, T-M4-008/009 | 1.0 | P14, P19 |
| P22 | `scripts/check_submission.py` | T-M8-014 | 0.5 | P5, P15, A19 |
| P23 | Zero-downtime rollout (**bonus**) | T-M9-009 | 0.5 | P17, A10 |
| **P24** | `RUNBOOK.md` + notes Q1, Q2, Q6, Q7 | T-M10-005, T-M6-012, T-M8-015, T-M7-014 | 1.0 | P17, P20, P21 |
| P25 | Evidence directory audit | T-M10-009 | 0.5 | P7, P19, P20, P21 |

**Subtotal: 20.0 blocks**

---

## 4. Work packages — shared

| WP | Name | Tasks | Dur (each) | Depends on |
|----|------|-------|-----|------------|
| S1 | Walkthrough 1 | T-M11-006 | 0.5 | mid-week |
| S2 | Cross-area swap + deliberate merge conflict + shortlog balance | T-M11-007/005/004 | 0.5 | ~two-thirds point |
| **S3** | README assembly, notes Q3/Q4/Q5, ADR review, `AI-USAGE.md` | T-M10-002/004/006/007/008 | 1.0 | P24, A18, A19 |
| **S4** | Walkthrough 2 + video rehearsal + live-modification practice | T-M11-008/009 | 0.5 | S3 |
| **S5** | Demo video | T-M10-010 | 0.5 | S4 |
| **S6** | Submission pack + final deduction walk | T-M10-011/012 | 0.5 | S5, P22, P25 |

**Subtotal: 3.5 blocks each**

---

## 5. Critical path

Forward and backward pass over the network above, project start at block 0.

### 5.1 The critical path (zero float)

```
A1 → A7 → A8 → A9 → A10 → P13 → P14 → P15 → P16 → P17 → P24 → S3 → S4 → S5 → S6
1.0  1.5  0.5  1.5   1.5    1.0   1.0   0.5   0.5   1.0   1.0   1.0  0.5  0.5  0.5
```

**Project duration: 13.5 blocks ≈ 6.75 days at the nominal 2 blocks/day.**

A **second zero-float chain** branches at P14 and rejoins at P24:

```
P14 → P19 → P20 ┐
        └→ P21 ─┴→ P24
```

`P19`, `P20` and `P21` all have zero float. The scaling evidence is not a nice-to-have at the end — it is on the critical path, because `P24` (runbook and four engineering-note answers) cannot be written until the load tests have produced their numbers.

### 5.2 What the critical path actually says

Three findings worth acting on:

1. **The riskiest dependency in the whole plan is `A10 → P13`** — Dev 1 finishing the real backend (routes, services, real `/health` and `/ready`) before Dev 2 can wire probes correctly. It is the one cross-developer handoff on the critical path. If it slips a block, the whole project slips a block, and there is no buffer to absorb it.

2. **`A1` is the head of everything.** Dev 2 has almost no dependency-free work: only `P1` (0.5 blocks). Until the backend skeleton exists, Dev 2 is blocked. This is why `A1` is a half-day task that must be merged on Day 1 morning, before any real logic is written.

3. **Evidence capture is critical-path work, not cleanup.** `P19 → P20 → P24 → S3 → S5` means the load test, the VPA loop, the notes, the README and the video are a single serial chain occupying the last two-and-a-half days. Treating them as "we'll do the docs at the end" is exactly how this plan fails.

### 5.3 Float table — where the slack is

| Float | Packages | Meaning |
|---|---|---|
| **0.0** | A1, A7, A8, A9, A10, P13, P14, P15, P16, P17, P19, P20, P21, P24, S3, S4, S5, S6 | **Critical.** A one-block slip here slips the project. |
| 1.0 | A5 | Nearly critical |
| 1.5 | A3, A4 | Data layer — small buffer |
| 2.0 | A6, A14, P12 | |
| 2.5 | A2, P2, P23 | |
| 3.0 | A11, A13, A19 | |
| 3.5 | P1, P4, P10, P11, P18, P22 | Comfortable |
| 4.5 | P6 | |
| **6.5** | A12, P9 | **Ollama path — highest float, first cut candidate** |
| 7.0 | A15, A16, A17, A18 | **Frontend — surprisingly large float** |
| 7.5 | P5 | |
| 9.5 | P7 | Float is high, but **schedule it early anyway** (§5.4) |

### 5.4 Two packages whose float lies

Float says "you may start this late". Two packages should be started early regardless:

- **P7 (red/green merge-block evidence, 9.5 float).** A deliberate pipeline failure is cheap while the pipeline is small and has three jobs. On Day 6 it means breaking a large working system on purpose, and re-verifying everything afterwards. Do it on Day 2.
- **P1 (repo governance, 3.5 float).** Branch protection must exist *before* the PR history accumulates. Retrofitting it does not retroactively produce the five reviewed PRs that Rubric A wants.

### 5.5 The frontend's large float is a scheduling opportunity

`A15`–`A18` carry 7 blocks of float, because nothing downstream except the screenshots and the video depends on the frontend. That makes frontend work the natural **buffer absorber**: it can be pushed into whichever block is free, and it is the work most safely interrupted.

It is *not* a cut candidate — Rubric B is 18 marks, more than Kubernetes probes and HPA combined.

---

## 6. Capacity reality — read this before building the day plan

The dependency critical path is 13.5 blocks and fits in a 14-block week. **The resource demand does not.**

| | Blocks of work | Nominal capacity |
|---|---|---|
| Dev 1 | 19.0 + 3.5 shared = **22.5** | 14 |
| Dev 2 | 20.0 + 3.5 shared = **23.5** | 14 |
| **Total** | **46.0** | **28** |

At face value the week is **1.6× oversubscribed**. This is not a planning error — it is the honest consequence of compressing a brief that estimates 35–45 hours per student over four weeks into one week.

### 6.1 What AI assistance actually changes

The team is building with heavy AI assistance, which is a real multiplier — but not a uniform one. It compresses **writing**; it does not compress **waiting** or **debugging**.

| Work type | Packages | Compression |
|---|---|---|
| Code generation from a clear spec | A2–A19, P12, P22 | **High** — roughly 0.5× |
| Infrastructure config with an iteration loop | P2–P5, P13–P15 | Moderate — roughly 0.75× |
| CI pipeline iteration (each run costs minutes of wall clock) | P6–P10, P16–P18 | **Low** — roughly 0.85× |
| Load testing, evidence capture, video | P19–P21, P25, S5 | **None** — wall-clock bound |

Applying those factors:

| | Effective blocks | Capacity | Gap |
|---|---|---|---|
| Dev 1 | ≈ 13.5 | 14 | fits |
| Dev 2 | ≈ 18.5 | 14 | **−4.5** |

**Dev 2 is the binding constraint**, because platform work is exactly the work AI compresses least. The ownership split (`AD-013`) gives Dev 1 more *marks* but Dev 2 more *irreducible hours*.

### 6.2 Three levers, in the order to pull them

**Lever 1 — rebalance ~2.5 blocks from Dev 2 to Dev 1.** This is free: it closes most of the gap *and* satisfies the cross-area swap that `AD-013` and the viva require. Move to Dev 1:

| Package | Why it moves cleanly |
|---|---|
| **P3** (frontend image, 0.5) | Pairs with `A14`, where Dev 1 already wrote the nginx template |
| **P7** (red/green evidence, 0.5) | Small, self-contained, and forces Dev 1 to read the CI pipeline — a good swap task |
| **P9** (Ollama service, 0.5) | Pairs with `A12`, the provider Dev 1 implements anyway |
| **P22** (`check_submission.py`, 0.5) | Mostly static checks over application code Dev 1 wrote |
| **S3** (shared docs, +0.5 of Dev 2's share) | Dev 1 takes 1.5, Dev 2 takes 0.5 |

After rebalance: **Dev 1 ≈ 15.5, Dev 2 ≈ 16.0.** Both about 2 blocks over a 14-block week.

**Lever 2 — accept a longer day.** Two blocks over seven days is roughly **10 focused hours per day instead of 8**. That is the honest price of this timeline, and it should be agreed on Day 0, not discovered on Day 5.

**Lever 3 — the pre-committed cut order (`AD-012`).** Triggered by the Day 5 checkpoint, not by feel. In order:

| Cut | Saves | Marks lost |
|---|---|---|
| 1. **P20** VPA loop | 1.0 | 3 (Rubric H-06) |
| 2. **P18** `release.yml` | 0.5 | ~1 (part of Rubric I) |
| 3. **P23** zero-downtime bonus | 0.5 | +4 bonus only |
| 4. **A12 + P9** Ollama — drop to three providers, still satisfying Rubric F-01 | 1.0 | 0 |

**Total available: 3.0 blocks, at a cost of ~4 marks.**

**Never cut:** anything in M5 (AI layer, 25 marks), anything in M2 (backend, 25 marks), and never the fallback test. The brief's own priority order is F > C > I > H.

Note that cutting `P20` removes a zero-float package, which shortens the critical path by 1 block — it is the single most schedule-effective cut available, which is why it is first.

---

## 7. Milestones and their gates

| # | Milestone | Target block | Target day | Gate — do not pass without this |
|---|---|---|---|---|
| **M0** | Repo governed, skeleton merged | 1.0 | Day 1 AM | `A1` merged via PR; `main` protected; Dev 2 unblocked |
| **M1** | Stack runs in Compose | 4.0 | Day 2 | `docker compose up` works; `exec frontend ping database` fails |
| **M2** | Backend feature-complete | 6.0 | Day 3 PM | All contract tests 1–14 pass; **the mandatory fallback test passes** |
| **M3** | Running on Kubernetes with correct probes | 7.0 | Day 4 AM | Stopping PostgreSQL removes pods from endpoints without restarting them |
| **M4** | Autoscaling proven | 9.0 | Day 5 AM | `kubectl get hpa` shows a real percentage; replicas rise under k6 |
| **M5** | CD deploys to an ephemeral cluster | 10.0 | Day 5 PM | A green `cd.yml` run link exists (submission item 2) |
| **M6** | All evidence captured | 11.0 | Day 6 AM | Every filename in the evidence manifest exists |
| **M7** | Documentation complete | 12.0 | Day 6 PM | Eight notes answered with file:line; ADRs match the built system |
| **M8** | Submitted | 13.5 | Day 7 | `check_submission.py` clean; six §5.8 items collected |

**The Day 5 checkpoint (M4/M5) is the cut decision point.** If M4 has not been reached by the end of Day 5, pull Lever 3 immediately and in order. Deciding on Day 7 is deciding too late to act.
