# 09 — M8 CI/CD: design and implementation guide

**Owner:** Dev 2 (`AD-013`)
**Depends on:** M6 (images), M7 (manifests), M2/M1 (tests to run)
**Delivers:** `RUB-I-01`…`RUB-I-07`, and three automatic deductions. Mark totals are not quoted in design documents (`AD-047`).
**Stack:** GitHub Actions, GHCR, Trivy, Syft, kubeconform, k3d-in-runner

---

## 1. What this module is for

Gated verification, then publication, then deployment — in that order, enforced by `needs:`, so nothing is ever published from code already known to be broken.

The integration job is the direct answer to *does my code work with everybody else's code?*, and it is the job that will catch the `localhost` bug before a human does.

---

## 2. Branch and protection model

Two long-lived branches: `dev` for work, `main` for deployable software. Feature branches off `dev` (`AD-042`).

`main` protected (`FR-CICD-012`): no direct pushes, PR required, ≥ 1 approval, and **all eight `ci.yml` jobs required as status checks** — `lint-and-type`, `test-backend`, `test-frontend`, `build`, `scan`, `manifests`, `integration`, `submission-check`.

**Enumerating them is the point.** "CI required as a status check" is satisfied by requiring one job, which leaves `scan`, `manifests` and `integration` advisory while the merge button stays green — a gate that only appears to be a gate. The eight names in the branch-protection rule must match the eight job ids exactly.

**Merge method: merge commit, not squash.** `FR-PROC-004` needs a preserved merge commit as marked evidence and `FR-PROC-003` needs ≥ 35 commits; squash-merging destroys both, and it is a repository setting nobody thinks to check.

A commit pushed directly to `main` is −5, and branch protection is what makes that mechanically impossible rather than a matter of discipline.

Screenshot of the protection settings, showing all eight checks, goes in `docs/evidence/branch-protection.png`.

---

## 3. `ci.yml` — on pull request to `main`, on push to `dev`

| Job | Steps | Notes |
|---|---|---|
| `lint-and-type` | `ruff` + `mypy` (backend); `eslint` + `tsc --noEmit` (frontend) | Fast; fails first |
| `test-backend` | `pytest` with coverage ≥ 65 % on `app/`, `TRIAGE_PROVIDER=simulated`, PostgreSQL + Redis as **service containers** (`AD-010`) | No network to a model, ever |
| `test-frontend` | Vitest, the ≥ 5 component tests of `FR-FE-020`'s required mapping, with coverage ≥ 50 % on `frontend/src/` | A coverage gate on the backend and none on the frontend meant half the code had a number and half had a promise |
| `build` | Build both images. **Do not push.** | A PR must not publish artifacts |
| `scan` | Trivy on both images, fail on HIGH/CRITICAL **with a fixed version available** | The qualifier matters: an unfixable CVE should not block a PR forever |
| `manifests` | `kustomize build overlays/prod \| kubeconform -strict` | Catches a broken manifest in 20 s instead of on the cluster |
| `integration` | `docker compose up -d` → wait for `/ready` → POST a complaint → GET it back → assert the category → assert `X-Cache` goes MISS then HIT → assert `exec frontend ping database` **fails** → `docker compose down -v` | The starred contract tests from `01-api-contract.md` §14, plus the one §5.3 check that needs a running stack |
| `submission-check` | `python scripts/check_submission.py` | **Previously defined and wired into nothing** (`FR-DOC-007`), so every §5.3 deduction guard ran only when a human remembered. Now a required check |

**Wait for `/ready`, never `sleep`.** A polling loop with a timeout is the correct shape; a fixed sleep is how a pipeline becomes flaky, and a flaky pipeline trains a team to ignore red (`NFR-REL-006`).

**`docker compose down -v` in the integration job is deliberate** — it starts clean each run. Note that this is the opposite of the persistence demonstration (`FR-DATA-005`), which must *not* use `-v`. Both are correct in their context.

---

## 4. `cd.yml` — on push to `main`

```
test  ──needs──► build-push  ──needs──► deploy-k8s
```

| Job | Steps |
|---|---|
| `test` | The full suite again, on the merged result |
| `build-push` | `needs: test`. Build both images, push to **GHCR** tagged `${{ github.sha }}` **and** `latest`. Emit an SBOM with Syft. **Capture the image digest as a job output.** |
| `deploy-k8s` | `needs: build-push`. Create a k3d cluster in the runner, apply `overlays/prod` with the SHA tag, wait on `kubectl rollout status`, smoke-test through the Ingress with an explicit `Host` header, print `kubectl get hpa`. **On smoke-test failure: `kubectl rollout undo`, print `describe` and pod logs, exit non-zero** |

**The deploy job fails closed.** Previously its only failure mode was a red tick, which leaves a broken deployment running and reports the problem to nobody who can act on it. Rolling back automatically also exercises the mechanism `FR-K8S-014` documents on every bad deploy, rather than once on video.

**The SBOM has a destination.** `syft` writes SPDX JSON per image, uploaded as a workflow artifact named `sbom-<image>-<sha>` with 90-day retention, and attached to the GitHub Release by `release.yml`. An SBOM that is emitted and discarded is not a deliverable (`FR-CICD-009`).

**`needs:` on every publishing and deploying job is non-negotiable** — its absence is −8 (`BR-DEL-001`).

**Deploy by SHA, never `:latest`** (`ADR-0003`). `:latest` may be pushed; it may never be deployed (−8). The digest is captured even though the tag is what deploys, so adopting digest deployment later is a small change.

---

## 5. `release.yml` — on tag `v*`

Build, push semver-tagged images, generate release notes. Semver tags are for humans and consumers; the commit SHA remains what deployment references, because a semver tag is applied by a person and can be moved.

This is the **second** item in the declared cut order (`AD-012`), after the VPA loop. This document previously called it the first while the decision log called it the second; the log wins, and they now agree.

---

## 6. Supply-chain controls (`FR-CICD-011`, `NFR-SEC-007`)

- **Least-privilege `permissions:` block on every workflow.** The default token scope is broader than any of these jobs needs. `contents: read` by default; `packages: write` only on the publishing job; `id-token`/`security-events` only where actually used.
- **`GITHUB_TOKEN` with `packages: write` for GHCR** — a scoped, revocable token, never an account password.
- **Actions pinned** to at least a major version tag; commit-SHA pinning is a bonus.
- **All credentials from GitHub Secrets.** `GROQ_API_KEY` is a repository secret; it appears in the CD environment and in the `kubectl create secret` step, never in a file.
- **Trivy** fails the build on HIGH/CRITICAL with a fix available.
- **Syft** emits an SBOM per image as SPDX JSON, uploaded as a retained workflow artifact and attached to the Release — not generated and dropped.
- **Images are scanned but not signed.** Cosign signing and verification are deferred with digest deployment (`ADR-0003`, `RUB-X-03`). The brief's §1.4 says a push to main "builds signed and scanned images"; one half of that is implemented, and `docs/NON-GOALS.md` §5 says which.

---

## 7. Evidence that the gate works (`FR-CICD-013`)

One mark, and it must be produced deliberately:

1. Open a PR containing a deliberately failing test.
2. Screenshot the red check **and** the blocked merge button.
3. Fix it in the same PR.
4. Screenshot the green state and the now-enabled merge.

Files: `docs/evidence/blocked-merge-red.png`, `blocked-merge-green.png`.

Do this **early in the week**, while the pipeline is small and a deliberate failure is cheap. Doing it on the last day means introducing a failure into a large working system.

---

## 8. Invariants this module must not violate

| Rule | Deduction |
|---|---|
| `BR-DEL-001` — `needs:` on publish/deploy | −8 |
| `BR-DEL-002` — never deploy `:latest` | −8 |
| `BR-DEL-003` — `main` protected, no direct commits | −5 |
| `BR-SEC-003` — secrets from GitHub Secrets only | −20 if one lands in the tree |

---

## 9. Tasks

| ID | Task | Size | Owner | Depends on | Delivers | Done when |
|---|---|---|---|---|---|---|
| **T-M8-001** | Branch protection on `main`: PR required, CI required, 1 approval; screenshot | S | Dev 2 | — | FR-CICD-012, RUB-A-01 | A direct push to `main` is rejected by the server |
| T-M8-002 | `ci.yml` skeleton with `lint-and-type` | S | Dev 2 | M2 T-M2-001, M1 T-M1-001 | FR-CICD-002 | Fails on a lint error, passes when fixed |
| **T-M8-003** | `test-backend` job with PostgreSQL + Redis service containers, `TRIAGE_PROVIDER=simulated`, coverage gate | M | Dev 2 | M2 T-M2-015 | FR-CICD-003, AD-010 | Coverage below 65 % fails the job |
| T-M8-004 | `test-frontend` job | S | Dev 2 | M1 T-M1-012 | FR-CICD-004 | Five component tests run in CI |
| T-M8-005 | `build` job — build both images, **no push** | S | Dev 2 | M6 T-M6-001/003 | FR-CICD-005 | No registry write on a PR |
| T-M8-006 | `scan` job — Trivy, fail on fixable HIGH/CRITICAL | S | Dev 2 | T-M8-005 | FR-CICD-006 | A known-vulnerable base fails the job |
| T-M8-007 | `manifests` job — kustomize + kubeconform | S | Dev 2 | M7 T-M7-011 | FR-CICD-007 | A deliberately broken manifest fails in under a minute |
| **T-M8-008** | `integration` job — Compose up, poll `/ready`, POST/GET, assert category, assert MISS→HIT, down `-v` | **L** | Dev 2 | M6 T-M6-006 | FR-CICD-008 | Starred contract tests pass against real containers; no `sleep` used for synchronisation |
| **T-M8-009** | `cd.yml` — `test` → `build-push` (GHCR, SHA + latest, Syft SBOM, digest output) | M | Dev 2 | T-M8-003…008 | FR-CICD-009, BR-DEL-001 | Images appear in GHCR with SHA tags; SBOM attached |
| **T-M8-010** | `cd.yml` `deploy-k8s` — k3d in runner, apply `overlays/prod` at the SHA, `rollout status`, Ingress smoke, `get hpa` | **L** | Dev 2 | T-M8-009, M7 T-M7-011 | FR-CICD-009 | A green run link exists (submission item 2) |
| T-M8-011 | `release.yml` on `v*` | S | Dev 2 | T-M8-009 | FR-CICD-010 | A test tag produces semver images and notes |
| T-M8-012 | Least-privilege `permissions:` on all three workflows; actions pinned | S | Dev 2 | T-M8-011 | FR-CICD-011, NFR-SEC-007 | No workflow uses default broad permissions |
| **T-M8-013** | Red-then-green merge-block evidence | S | Dev 2 | T-M8-002 | FR-CICD-013, RUB-I-07 | Two screenshots in `docs/evidence/` |
| T-M8-014 | `scripts/check_submission.py` — all §5.3 mechanical checks + the M2 layer checks | M | Dev 2 | M2 T-M2-014 | FR-DOC-007 | Clean run from the repository root |
| T-M8-015 | Engineering-notes Q2 (maturity ladder) drafted | S | Dev 2 | T-M8-010 | RUB-J-05 | Names the rung, justifies it, names the next rung and what it buys |

**T-M8-001 and T-M8-013 should happen on day 1–2**, not at the end. Protection has to exist before the PR history accumulates, and a deliberate failure is cheap while the pipeline is small.

---

## 10. `scripts/check_submission.py` — what it checks

A lint, not a grader. It catches the mechanical failures behind most of §5.3:

| Check | Deduction guarded |
|---|---|
| No secret-shaped strings in the working tree or in `git log -p` | −20 |
| No non-placeholder value in committed Kubernetes Secret manifests | −15 |
| Every `FROM`, every Compose `image:`, every manifest image has an explicit tag | −8 |
| No `localhost` in `compose*.yaml`, `k8s/`, or `frontend/src/` | −8 |
| `compose.prod.yaml` publishes no `database`/`cache` port and has no `build:` key | −8 |
| No `:latest` in any deployed overlay | −8 |
| Every publishing/deploying job has `needs:` | −8 |
| `postgres` is a StatefulSet with a `volumeClaimTemplates` | −8 |
| No SQL/session imports under `routes/`, `services/`, `providers/` | Rubric C-02 |
| No `create_all` or `CREATE TABLE` outside `alembic/versions/` | Rubric D-01 |
| No concrete triage class named outside `providers/triage/` and tests | Rubric F-01 |
| No status-transition map or hand-written enum list under `frontend/src/` | Rubric B-02 |
