# ADR-0003 — Deploy by immutable reference

- **Status:** Accepted
- **Date:** 2026-09-16 (accepted). Revised 2026-09-25 by the specification audit.
- **Decides:** `AD-034`
- **Related requirements:** `FR-K8S-013`, `FR-CICD-009`, `BR-DEL-001`, `BR-DEL-002`, `NFR-OPS-004`

## Context

A deployment must answer one question instantly: **what is production running?** The answer has to be something that can be pasted into `git show` and that cannot change underneath you.

A mutable tag cannot do this. `:latest` points at a different image after every push, so two pods started ten minutes apart can be running different code while reporting the same tag. A rollback to "the previous latest" is not expressible. An incident investigation that starts with "which commit is this?" has no answer.

The pipeline also publishes artefacts, and publishing from unverified code is how a broken build reaches a registry that something else then pulls.

## Decision

**Every image is published to GHCR tagged with the commit SHA. Deployments reference the SHA tag. `:latest` may be published; it is never deployed.**

- `cd.yml` builds and pushes both images tagged `${{ github.sha }}` **and** `latest`, in a job gated by `needs: test`.
- The `deploy-k8s` job is gated by `needs: build-push` and applies `overlays/prod` with the image tag set to the same SHA, via a Kustomize image transformer.
- The build job captures the image **digest** as a job output, so the digest is recorded in the run even though the SHA tag is what is deployed.
- `GET /api/version` returns the commit SHA, passed in as a Docker build argument, so the running system can be asked directly rather than inferred from a manifest.
- Registry authentication uses `GITHUB_TOKEN` with `packages: write` — a scoped, revocable token, never an account password — under a least-privilege `permissions:` block.

**Rollback has two documented mechanisms**, and the distinction matters:

| Mechanism | When | Property |
|---|---|---|
| `kubectl rollout undo deployment/backend -n civic-station` | During an incident | Fast, imperative, **within 30 seconds** measured to `rollout status` returning. The cluster no longer matches the repository, which is acceptable while the fire is burning and unacceptable afterwards. |
| Re-apply the previous overlay at the previous SHA | Once the incident is contained | Declarative, auditable, reproducible, **within 90 seconds** measured the same way. The repository and the cluster agree again. |

Both figures are measured and captured to `docs/evidence/rollback-timing.txt` (`FR-K8S-014`). Two bounds rather than one, because the declarative path is slower by nature and holding it to the imperative path's 30 seconds would misreport it.

**The deploy job uses the imperative path automatically.** `FR-CICD-009` runs `rollout undo` when the post-deploy smoke test fails, so the mechanism is exercised on every bad deploy rather than only demonstrated once on video.

**"What is production running?" has two answers that must agree**: the image tag in the deployed manifest, and `GET /api/version` (`FR-BE-029`). The endpoint reads `APP_VERSION` from the environment at **runtime**, never from a Docker build argument — baking the SHA into the image would make the artefact commit-specific and contradict `NFR-PORT-001`, which is the property this whole ADR depends on (`AD-014`).

## Alternatives considered

**Deploy by digest (`@sha256:...`).** Strictly stronger: a digest identifies the exact bytes, whereas a SHA tag is still a tag and could in principle be overwritten by someone with registry write access. Deferred to bonus scope (`AD-012`, `RUB-X-03`) because it requires threading the digest from the build job through the Kustomize transformer, plus Cosign signing and verification to be worth the full bonus — work that competes with core deliverables. The digest is captured as a job output regardless, so adopting it later is a small change.

**A related limit worth stating:** the brief's §1.4 says a push to main "builds **signed** and scanned images". Scanning is implemented (Trivy, `FR-CICD-006`); **signing is not**, because Cosign is part of the deferred bonus. So one clause of that sentence is met and one is not, and this ADR says which rather than letting the README imply both.

**Deploy `:latest`.** Rejected; it is an automatic −8 and it makes the central question unanswerable.

**Semantic version tags as the deployment reference.** `release.yml` publishes semver tags on `v*` tags, which is the right thing for humans and consumers. But a semver tag is applied by a person and can be moved; the commit SHA is the machine-truthful identifier and is what deployment uses.

## Consequences

**Good.**
- "What is production running?" is answered by one string that maps to exactly one commit, and `GET /api/version` returns it from inside the running system.
- No publishing or deploying job can run on code that has not passed the test job, because `needs:` gates both.
- Rollback to any previously deployed state is expressible, because every previously deployed state has a name that still means the same thing.

**Costs.**
- Every deployment is a new manifest value, so the deployed tag must be injected by the pipeline rather than committed. The committed overlay therefore contains a placeholder tag, and a human running `kubectl apply` by hand must supply the SHA — documented in the runbook.
- The registry accumulates one image per commit to `main`. Acceptable at this scale; a retention policy is a real concern at production scale and is noted as such rather than implemented.
- The commit SHA is baked into the image as a build argument. This is the one thing that is legitimately environment-independent-but-build-time, and the engineering notes explain why it does not violate build-once-deploy-many: the SHA identifies the artefact, it does not configure it.
