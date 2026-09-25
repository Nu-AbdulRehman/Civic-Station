# AGENTS.md — Civic-Station

Operational reference for any coding agent working in this repo (Claude Code, Codex,
Cursor, etc.). For the non-negotiable rules, read `CLAUDE.md` first. This file assumes
you have, doesn't restate the "never" list, and tells you how to move.

## Project

Two-developer build of a municipal complaint intake and AI-triage system. Backend:
FastAPI + Pydantic v2 (fully async), SQLAlchemy 2.0 async + asyncpg, PostgreSQL 16,
Redis 7. Frontend: React 18 + Vite + TypeScript, served by `nginx:1.27-alpine`. Deploy
target: Kubernetes on k3d (bundled Traefik, Kustomize), with GitHub Actions CI/CD. The
triage provider is Groq (`llama-3.1-8b-instant`) behind a `TriageProvider` seam, with
Ollama, keyword rules, and a seeded simulator as alternatives.

**Status:** planning is done and audited; implementation has not started. Code paths
below are the target layout from `docs/design/00-conventions.md` §1, not files that
exist yet. Specification index and reading order: `docs/README.md`. Wire contract:
`docs/design/01-api-contract.md`.

## Repo layout

```
backend/app/
  main.py            app factory + lifespan + middleware wiring — nothing else
  config.py          the ONLY environment reader; one typed settings object
  domain/            enums, TriageResult, transition table, domain errors — pure, no I/O
  routes/            HTTP only, thin; dependencies via FastAPI DI
  services/          business rules, orchestration order
  repositories/      all SQL
  providers/
    cache/           Redis port: stats cache, rate limiter, triage cache, outcomes
    triage/          base (Protocol), llm, ollama, rules, simulated, factory,
                     prompt, redact, pipeline (timeout/retry/validate/fallback)
  observability/     JSON logging, request-id middleware, Prometheus metrics
  db/                engine, session factory, ORM models
backend/alembic/versions/            the only place DDL lives
backend/tests/{unit,integration}/
backend/seeds/complaints.py          idempotent seed (UUIDv5 + ON CONFLICT DO NOTHING)
frontend/src/{api,components,pages}/ api/client.ts is the only fetch caller;
                                     api/types.ts is generated and committed
k8s/base/, k8s/overlays/{dev,prod}/
load/k6-script.js
scripts/check_submission.py          deduction guard, a required CI check
scripts/plot_scaling.py
compose.yaml, compose.prod.yaml, .env.example
docs/                                spec (see docs/README.md), plus the files below
```

Files produced during implementation, all under `docs/`: `ENGINEERING-NOTES.md`,
`RUNBOOK.md`, `TRIAGE.md`, `AI-USAGE.md`, `INCIDENTS.md`, `failure-log.md`, and
`evidence/` (14 named artefacts, listed in `FR-DOC-006`).

## Commands

Only commands the spec names. Add new ones here in the same PR that creates them.

```bash
make up                                   # clean clone → seeded running system; the README quickstart, verbatim
make pull-models                          # one-time Ollama weight pull into ollama_models (AD-046)
python -m seeds.complaints                # from backend/; idempotent, a second run is a no-op
pytest                                    # backend suite; CI gate is coverage ≥ 65 % on app/
ruff check . && mypy .                    # backend lint + types
npx eslint . && npx tsc --noEmit          # frontend lint + types
npx vitest                                # frontend component tests; CI gate ≥ 50 % coverage
python scripts/check_submission.py        # deduction guard; run before every PR
kustomize build k8s/overlays/prod | kubeconform -strict
kustomize build k8s/overlays/prod | grep -c ':latest'   # must print 0
```

After any backend contract change, regenerate `frontend/src/api/types.ts` from
`/openapi.json` with `openapi-typescript` and commit it. A `tsc --noEmit` failure after
regeneration is intended: that's how a breaking contract change surfaces in CI.

The 30 contract tests in `01-api-contract.md` §14 assert the wire shape. Never edit
one to make a change pass. If a contract test fails, the code is wrong, unless the
contract itself is being changed through the process in `CLAUDE.md` §1.7.

Integration tests run against real PostgreSQL and Redis. Locally that means Compose. In
CI they are service containers (`AD-010`). Never use SQLite.

## CI shape (`docs/design/09-M8-cicd.md`)

- `ci.yml` runs on PRs to `main` and pushes to `dev`. Jobs: `lint-and-type`,
  `test-backend`, `test-frontend`, `build` (no push), `scan` (Trivy, fails on fixable
  HIGH/CRITICAL), `manifests`, `integration`, `submission-check`. All eight are
  required checks.
- `cd.yml` runs on pushes to `main`: `test` → `build-push` → `deploy-k8s`, chained
  by `needs:`. The deploy uses the commit SHA (ADR-0003).
- `integration` waits by polling `/ready` and never uses `sleep`. It ends with
  `docker compose down -v`. The persistence demo must **not** use `-v`.

## Environment

The full registry, with defaults, is in `00-conventions.md` §3. `.env.example` lists
every variable with placeholders. `.env` is git-ignored.

`TRIAGE_PROVIDER` switches the classifier with zero call-site changes. An unknown value
fails at startup.
- `rules`: the default. Keyword classifier, no key and no network needed.
- `simulated`: used in every test and CI run. Seeded (`SIMULATED_SEED`), with failure
  injection through `SIMULATED_FAILURE_MODE=none|raise|malformed|slow`.
- `ollama`: local model on the `internal` network, zero egress. Needs
  `make pull-models` first.
- `llm`: Groq through the `openai` SDK. Needs `GROQ_API_KEY`.

Never require a real key on the default path. A stranger must be able to clone and run
with `make up` and nothing else. Bump `PROMPT_VERSION` whenever the prompt changes: it
is part of the triage cache key and the outcomes key.

Service DNS names, the same in Compose and k8s: `backend`, `database`, `cache`,
`ollama`. k8s namespace: `civic-station`. Ingress host: `civic-station.localhost`.

## Conventions

- **Git:** feature branch → `dev` → `main`. The branch name is
  `<type>/<T-or-FR-id>-<desc>`, for example `feat/T-M5-006-triage-pipeline`, with type
  one of `feat|fix|docs|test|ci|refactor|chore`. Commits use Conventional Commits and
  reference the requirement ID. One PR per branch, linked to an Issue, with a
  substantive partner review. Merge commits only, never squash.
- **Process floors** (`12-M11-process.md`): at least 35 commits total, neither partner
  below 35 % by `git shortlog -sn`, and at least 5 merged PRs. There is one real merge
  conflict, on real code, with evidence.
- **Handover:** a session that ends with an unmerged branch leaves
  `docs/handover/HANDOVER-<branch>.md`. It records position, what's green, what's
  half-done, the literal next command, and what will bite. Write it at close and read it
  at open. Delete it in the merge commit.
- **Decisions:** a decision the spec doesn't dictate becomes a new row in the
  `docs/decisions/OPEN-DECISIONS.md` resolution log. It also gets one paragraph in
  `docs/ENGINEERING-NOTES.md` if it needs defending at viva: what was chosen, what the
  alternative was, and why. Never re-decide a resolved `AD-*`.
- **Logs:** structured JSON to stdout, never to a file. Every line has `request_id`.
  Event names come from the stable list in `00-conventions.md` §5. Use `SecretStr` for
  `GROQ_API_KEY`, `POSTGRES_PASSWORD`, and `DATABASE_URL`.
- **Enums:** use `StrEnum` for every closed vocabulary (`Category`, `Priority`,
  `Status`, `TriagedBy`), declared once in `domain/`. Wire format and Python equality
  then line up with no `.value` ceremony. The DB enum comes from the migration, and the
  frontend type comes from OpenAPI.
- **Errors:** services raise domain errors (`ComplaintNotFoundError`,
  `InvalidTransitionError`, `RateLimitExceededError`). One set of exception handlers
  maps them to the envelope. No service imports `HTTPException`.
- **Failures:** append to `docs/failure-log.md` when something breaks, not afterwards.

## Mandatory skill cadence

Three Claude Code skills fire at fixed points in every session, and none is optional:
- `caveman`: at phase start, produces a stripped task list tagged with `T-M*-nnn` ids.
- `ponytail`: at every design fork, produces a decision stub with its rejected
  alternatives.
- `grilling`: before every PR, produces at least 3 hardening findings with `file:line`.

Full trigger conditions and acceptance tests are in `CLAUDE.md` §6. That is the
authority. This is the reminder that the cadence applies to every session, not only the
first. Log every invocation in `docs/AI-USAGE.md` when it happens, including what you
overrode and why.

## Definition of done for a phase

"The code runs" is not enough. A phase is done when:
1. Every task's `Done when` condition in its `docs/design/NN-M*.md` table is
   demonstrably true.
2. The unit, contract, and integration tests are green, and the coverage gates hold.
3. `python scripts/check_submission.py` reports no new violations.
4. Each affected row in `docs/requirements/RUBRIC-TRACEABILITY.md` has both its test
   and its evidence artefact in `docs/evidence/`. One without the other doesn't count.
5. A handover file exists if the branch isn't merging immediately.
6. `caveman`, `ponytail` (if a fork occurred), and `grilling` fired at their required
   points and are logged in `docs/AI-USAGE.md`, per `CLAUDE.md` §6.

## Where to look when stuck

| Question | File |
|---|---|
| What does the API actually promise? | `docs/design/01-api-contract.md` |
| What must never break? | `docs/requirements/BUSINESS-RULES.md` |
| Was this already decided? | `docs/decisions/OPEN-DECISIONS.md` resolution log, `docs/adr/` |
| Known spec defects and deviations from the brief | `docs/audit/01-specification-audit.md` (short list, deviation register) |
| Is this missing on purpose? | `docs/NON-GOALS.md` |
| Exact fallback, retry, and timeout logic | `docs/design/06-M5-ai-triage.md` §2.2 |
| Env var, error body, log event, or metric name | `docs/design/00-conventions.md` §3–§6 |
| What test and evidence prove this rubric line? | `docs/requirements/RUBRIC-TRACEABILITY.md` |
| Who owns this task? | the `Owner` column of the module's design doc |
| Is this a trap someone already hit? | `docs/failure-log.md`, `docs/INCIDENTS.md`, any `docs/handover/*` |
