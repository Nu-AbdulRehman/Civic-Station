# CLAUDE.md — Civic-Station. Read this before you touch anything.

This file is law for this repository. If something you're about to do conflicts with a
rule here, stop and say so instead of doing it anyway. "The user asked for it" is not
an exception to any rule marked **HARD**.

Source of truth order, when documents disagree:
`docs/planning/Civic-Station_Problem_Statement.md` (the brief, never edited) >
`docs/requirements/BUSINESS-RULES.md` > the resolution log at the bottom of
`docs/decisions/OPEN-DECISIONS.md` and the ADRs in `docs/adr/` >
`docs/design/00-conventions.md` and `docs/design/01-api-contract.md` >
the module guides `docs/design/NN-M*.md` > anything else, including this file's examples.
If a business rule and a design document disagree, the design document is the bug — say
so, don't quietly reconcile them. Everything under `docs/schedule/` is outside the
reading order except the ownership split (`AD-013`) and standing agreements.

Reading order and the full document index: `docs/README.md`.

---

## 0. What this system is, in one paragraph

A citizen submits a free-text complaint (text + location, optional contact). It is
redacted, then classified into category/priority/summary by a `TriageProvider` chosen
by `TRIAGE_PROVIDER` (`llm` = Groq, `ollama`, `rules`, `simulated`). It is persisted
in PostgreSQL and shown on an operator dashboard, where status moves through a fixed
state machine. The system's whole point, stated once: **the classifier must be
replaceable, and the system must not fall over when the provider is rate-limited, slow,
or wrong.** M5, the AI layer, is the highest-value module and the one the brief says
never to cut. If a change makes the provider harder to swap, or lets a provider failure
reach a citizen as a 5xx, it is wrong regardless of how clean the code looks.

---

## 1. HARD rules — never do these, no matter what you're asked

1. **Never commit a secret.** No `.env`, no `GROQ_API_KEY`, no `POSTGRES_PASSWORD`, no
   token: not in code, a commit message, a k8s manifest (not even base64, which is
   encoding, not encryption), a Dockerfile `ENV`/`ARG`, `.env.example`, or a log line.
   Generated `Secret` manifests contain `PLACEHOLDER_...` only (`BR-SEC-003`). If you
   ever output a real key, treat it as a live incident: flag it at once. A key in history
   means rotation plus an `INCIDENTS.md` entry.
2. **Never push to `main`.** `main` accepts merges only: PR + green CI + 1 approval. Work
   goes feature branch → `dev` → `main` (`BR-DEL-003`). If asked to "just push this,"
   refuse and open a PR instead. Merge commits, never squash (`FR-CICD-012`).
3. **Never issue SQL outside `backend/app/repositories/`.** No `select(`, `session`,
   `execute(`, `text(`, or ORM model import under `routes/`, `services/`, `providers/`.
   The only exemptions are `alembic/versions/` (DDL) and `backend/seeds/complaints.py`
   (`BR-DATA-003`). No `create_all`, ever. Schema changes come only from Alembic.
4. **Never write an `if status == ...` chain for the state machine.** Transitions are a
   lookup in the table in `backend/app/domain/`, mapping each status to a frozen set of
   successors, consulted by one function (`BR-STATUS-004`). Terminal states map to an
   empty set. Adding a status is a data edit plus a migration, not a new branch.
5. **Never let a triage failure become a 5xx.** `POST /api/complaints` returns `201` for
   every valid body whatever the provider does. Timeout, 429, 5xx, malformed JSON, a
   wrong enum, a 400-char "summary", provider entirely down: all of it ends in
   `RuleBasedTriage` with `triaged_by = "rules:fallback"` (`BR-TRIAGE-005/006`).
   `RuleBasedTriage` itself has no input for which it raises (`BR-TRIAGE-009`). If you
   write triage code that can raise past the fallback boundary in
   `providers/triage/pipeline.py`, you have broken the most important test in the
   assignment.
6. **Never retry a validation failure or a 400.** Bad model output goes straight to
   fallback, with no retries and no re-prompt (`AD-007`), and it is never repaired,
   coerced, or mapped to the "closest" enum (`BR-TRIAGE-003`). Only timeout / 429 / 5xx
   get **exactly one** retry after `uniform(0.25, 1.0)` s jitter (or `Retry-After`,
   capped at 5 s). Each call has a hard `TRIAGE_TIMEOUT_SECONDS` (10, refused above 15).
   The worst case for the whole operation is 21 s. Retry, timeout, and fallback live once,
   in `pipeline.py`, never inside individual providers.
7. **Never change the frozen API surface casually.** Enums, endpoint shapes, the error
   envelope, and header names (`X-Cache`, `Retry-After`) are defined in
   `docs/design/01-api-contract.md` and touch M1, M2, M8 and M9. A change is one PR that
   both developers agree on. It regenerates the frontend's typed client from OpenAPI
   and updates the contract tests (§14). If the two developers disagree, the module
   owner decides and records a new `AD` row.
8. **Never put a raw path or an unbounded value in a metric label.** Use `path_template`,
   never the literal URL: `/api/complaints/{id}`, not `/api/complaints/018f3a2c-...`.
   `error_class` is the closed set `Timeout`, `RateLimited`, `ServerError`,
   `ValidationFailed`, `Other`. It is never a provider's exception name. Metric names are
   fixed in `00-conventions.md` §6. Don't invent new ones.
9. **Never let the frontend own a business rule.** Under `frontend/src/` there is no
   transition map, no hand-written enum list, and no pre-filtering of status options.
   The frontend never authors its own 409 text. It sends the attempted transition and
   renders the server's `error.message` verbatim (`BR-STATUS-005`, `BR-VOCAB-005`).
   Nothing secret in the bundle, ever (`BR-SEC-002`).
10. **Never treat PostgreSQL as a `Deployment`.** It is a `StatefulSet` with
    `volumeClaimTemplates`. Never publish a database or cache port in
    `compose.prod.yaml`, and never give either one a `NodePort`/`LoadBalancer`.
    ClusterIP only (`BR-SEC-005`). The frontend never shares a Compose network with
    `database` or `cache` (`BR-SEC-001`, ADR-0005's three networks).
11. **Never deploy `:latest`, an untagged base image, or a floating
    `postgres`/`redis`/`node`/`python`/`nginx`/`ollama` tag.** Every image is pinned to a
    version or deployed by commit SHA (`image: ${IMAGE_TAG}`, ADR-0003). `APP_VERSION`
    is injected at runtime, never as a Docker build arg (`AD-014`).
12. **Never add a publish/deploy CI job without `needs:` on verification** (`BR-DEL-001`).
    Never give the build job registry credentials: nothing publishes from a PR.
13. **Never log, metric-label, or return in a response body any of these:** the API key,
    the DB password, `reporter_contact`, or a URL with embedded credentials. Complaint
    `text` is logged at `DEBUG` only. The raw prompt is never logged. `reporter_contact`
    is never sent to a third-party model (`BR-TRIAGE-015`). `cs:outcomes` entries carry
    exactly `complaint_id`, `provider`, `latency_ms`, `fallback`, `error_class`, `at`
    and nothing else (`FR-AI-012`). No error body ever contains a stack trace or a DB
    error string.
14. **Never write a test that can't fail.** Before calling a test done, revert the
    implementation, mentally or actually, and confirm the test goes red. An assertion
    that was never falsified is decoration, not a test.
15. **Never use `time.sleep()`, real network calls, or "just re-run it" in a test.**
    Fake the clock, use `SimulatedTriage` with `SIMULATED_FAILURE_MODE`
    (`raise`/`malformed`/`slow`), or use explicit async synchronization. Never skip a test,
    mark it `xfail`, or re-run it until it passes to get CI green (`BR-DEL-004`). A flaky
    test is a design bug in disguise.
16. **Never use `localhost` as a service-to-service address.** Use the service DNS names
    `backend`, `database`, `cache`, `ollama`. These names are the same in Compose and
    Kubernetes (`BR-SEC-004`). The exceptions are browser-facing `civic-station.localhost`,
    the Vite dev server, and a container's healthcheck against itself.
17. **Never let `/health` touch a dependency.** Liveness opens no DB connection, no Redis
    call, and no outbound request (`BR-OPS-001`). Dependencies belong in `/ready`.

## 2. The deduction ledger — costs more than most features are worth

These eleven automatic deductions from brief §5.3 total **−101 marks**. (The overall mark
total is unresolved, `AD-047`; don't quote one.) Avoiding a deduction is worth more than
most features. Check this list before saying any phase is done:

| Violation | Cost |
|---|---|
| `.env`, key, token or password anywhere in git history | −20 (+ rotate + incident note) |
| LLM key in a committed k8s manifest, even base64 | −15 |
| Unpinned base image, or `postgres`/`redis`/`node` without a tag | −8 |
| `localhost` for service-to-service calls | −8 |
| Frontend can reach the database (segmentation missing) | −8 |
| DB/cache port published in `compose.prod.yaml`, or NodePort/LB on the DB | −8 |
| Publish/deploy job not gated by `needs:` | −8 |
| Deploying `:latest` anywhere | −8 |
| PostgreSQL as a `Deployment` with no PVC | −8 |
| Commits pushed directly to `main` | −5 |
| README quickstart fails from a clean clone | −5 |

Each of these needs an automated detector in `scripts/check_submission.py`, which runs as
the required `submission-check` CI job. If you add code that could trip one, add or
confirm the detector in the same PR. Don't rely on memory.

## 3. Layer discipline (backend)

```
routes/        → schemas, services, deps        — HTTP only, thin handlers
services/      → repositories, provider ports, domain — business rules, orchestration order
repositories/  → db.models, sqlalchemy           — SQL, transactions, nothing else
providers/     → openai, httpx, redis            — vendor wire formats, isolated
  cache/         stats cache, rate limiter, triage cache, outcomes
  triage/        base, llm, ollama, rules, simulated, factory, prompt, redact, pipeline
domain/        → imports nothing from the app    — enums, TriageResult, transitions, errors
```

- `openai`, `redis`, and `httpx` are imported only under `providers/`. `httpx` may also
  appear in tests.
- `LLMTriage`/`OllamaTriage`/`RuleBasedTriage`/`SimulatedTriage` are named only in
  `providers/triage/` and tests. Everything else sees the `TriageProvider` Protocol.
- No module reads `os.environ`. It reads the one typed settings object in `config.py`.
  An unknown `TRIAGE_PROVIDER` fails at startup. It never silently defaults.
- A route with a `try/except` that maps a domain error to a status code is wrong. That
  is the registered exception handler's job, and it emits the single error envelope in
  `00-conventions.md` §4. A route with business logic is wrong. That logic belongs in a
  service.
- Rule order on `POST /api/complaints`: the rate limiter comes first. A 429 costs no
  inference and writes no row (`BR-CACHE-006`). Next comes triage. Persistence comes
  last. Stats invalidation happens before the response (`BR-CACHE-003`).
- 404 outranks 409 on `PATCH` (`BR-STATUS-007`). A rejected transition changes nothing,
  including `updated_at` (`BR-STATUS-006`).

## 4. Testing discipline

- Fast loop: `pytest backend/tests/unit` plus the contract tests from
  `01-api-contract.md` §14. Run it before every commit.
- Honest loop: `pytest backend/tests/integration` against real PostgreSQL and Redis
  (Compose locally, service containers in CI per `AD-010`). Never swap in SQLite. It has
  no native enums, no `gen_random_uuid()`, and no `timestamptz`, so a green SQLite suite
  against a Postgres system is a false signal.
- Use `TRIAGE_PROVIDER=simulated` in every test and CI run. Never make a live LLM call in
  CI. Coverage on `app/` stays at 65 % or above.
- **The fallback test comes first and is never skipped:** provider always raises → still
  `201`, `triaged_by == "rules:fallback"`, and exactly one `triage.fallback` WARNING.
  Its siblings are the malformed-output, timeout, and injection-guardrail tests
  (`BR-TRIAGE-010`). Never comment one out to get CI green faster.
- State-machine tests are parametrised over **every** edge, valid and invalid, including
  self-transitions.
- Lint and type checks must pass: `ruff`, `mypy`, `eslint`, `tsc --noEmit`.

## 5. When you're unsure

- Don't invent a resolution to an ambiguity. Check the resolution log in
  `docs/decisions/OPEN-DECISIONS.md` first. All 56 decisions are RESOLVED, so don't
  re-decide one. Then check `docs/audit/01-specification-audit.md` (the short list and
  the deviation register) and `docs/NON-GOALS.md` before proposing anything that looks
  missing: auth, NetworkPolicy, and a global spend cap are deliberately out of scope.
- If a design decision isn't covered anywhere, record it as a new row in the
  `OPEN-DECISIONS.md` resolution log, in one paragraph, **before** writing the code. If it
  is significant, also add a paragraph to `docs/ENGINEERING-NOTES.md`.
- When something breaks, append it to `docs/failure-log.md` as it happens. Q8 of the
  engineering notes cannot be written retroactively.
- If you're about to touch code your session didn't write, check for a handover file at
  `docs/handover/HANDOVER-<branch>.md` first. It may say "do not touch." Ownership split
  (`AD-013`, hybrid): Dev 1 owns the application layers and Dev 2 owns the platform
  layers, with a mandatory cross-area swap. Each task's owner is in the `Owner` column
  of its design doc's task table.
- Requirement IDs (`FR-*`, `NFR-*`, `BR-*`, `AD-*`, `T-M*-nnn`) are permanent. Reference
  them in commits (`feat(triage): fall back to rules on provider failure (FR-AI-008)`)
  and branches (`feat/T-M5-006-triage-pipeline`).

## 6. Mandatory skill invocations — never skip these, never do them silently

This project runs three Claude Code skills at fixed points in every session. They are not
optional, and a task being small is not a reason to skip one. If you are doing real work
on this repo and one of these points comes up, you invoke the skill. You do not simulate
it in your head and move on.

| Skill | Fires when | Input | Must produce | Fails if |
|---|---|---|---|---|
| **`caveman`** | Start of every phase, before writing any code | The module's task table in `docs/design/NN-M*.md` + the `BR-*`/`FR-*` it delivers | A stripped task list: nouns and verbs only, every item independently completable in ≤90 min, each tagged with its `T-M*-nnn` | Any line contains "consider", "maybe", "as needed"; fewer than 5 items; a line doesn't start with a verb |
| **`ponytail`** | The moment a design decision has ≥2 defensible answers, mid-phase, whenever it happens | The decision + the constraining `BR-*`/`AD-*` rows | A decision-record stub, which becomes a new `OPEN-DECISIONS.md` row, an ADR, or an `ENGINEERING-NOTES.md` paragraph | Fewer than 2 rejected alternatives named, or a rejection with no reason given |
| **`grilling`** | End of phase, before opening the PR, always, even for a small diff | The full diff against `dev` | ≥3 concrete findings with `file:line`: error paths, timeouts, resource cleanup, edge cases the happy path skipped | Fewer than 3 findings, a finding with no `file:line`, or findings silently dropped instead of turned into a commit or a documented `WONTFIX` |

**Rules that make this non-negotiable:**

1. **Do not skip `caveman` because you already know the tasks.** What gets checked is the
   stripped task list itself, not your mental model of it.
2. **Do not skip `grilling` because the diff is small or "obviously fine."** A diff that
   really is fine still produces findings, such as timeouts to add or cleanup to verify.
   At minimum it produces an explicit statement that nothing was found, and why that is
   credible for *this specific diff*. A rubber stamp doesn't count.
3. **Log every skill invocation in `docs/AI-USAGE.md` at the moment it happens**, not
   reconstructed later from memory. Format:
   ```markdown
   ## <date> · <branch>
   - **Tool:** Claude Code + `<skill>`
   - **Shaped / Wrote:** <what it touched>
   - **I changed:** <what you overrode or rejected and why, citing a BR/FR/AD id if one applies>
   ```
   The "I changed" line is mandatory even when you accepted the output as-is. In that
   case write "accepted as-is" rather than omitting the line. Specific disclosure carries
   no penalty. An undisclosed skill invocation is what costs marks at the viva.
4. **`ponytail` fires the moment the fork appears, not in end-of-phase cleanup.** If you
   notice mid-implementation that you're choosing between two designs, stop and invoke
   it there. Don't keep coding and rationalize the choice afterward in `grilling`.
5. **PR review is done by the partner, never by you on your own PR.** Running a review on
   your own diff does not satisfy `FR-PROC-002`, which requires a substantive review
   comment from the partner on every PR. "LGTM" is not a review.

## 7. Before you say a task is done

Run through this, out loud, not just in your head:

- [ ] Does this cross a layer boundary it shouldn't? (§3)
- [ ] Did I add anything to a metric label, log line, or response body that could be PII,
      a secret, or unbounded cardinality?
- [ ] Does every new triage failure path still return 201 with `rules:fallback`, and
      emit exactly one WARNING?
- [ ] Did I write a test that I confirmed would fail without the implementation?
- [ ] Is the task's `Done when` condition from its design doc demonstrably true?
- [ ] Did I change `01-api-contract.md`'s surface without a both-agreed PR that also
      regenerated the typed client?
- [ ] Would this trip any row in the deduction ledger (§2), and does
      `python scripts/check_submission.py` still pass?
- [ ] Am I about to commit directly to `main`?
- [ ] Did `caveman` run at the start of this phase, `ponytail` at every design fork, and
      `grilling` before this PR, and is each one logged in `docs/AI-USAGE.md`?

If any answer is "yes" where it shouldn't be, fix it before reporting completion. Don't
report the task as done and mention the caveat afterward.

## 8. Log every completed task in `docs/AI-USAGE.md`

After you complete a task, append one entry to the `## Task log` section of
`docs/AI-USAGE.md` before you report completion. Keep it to 1–2 lines: what you did and
which files it touched, with any `T-M*-nnn`/`FR-*` id that applies. Format:

```markdown
- <date> · <branch> · <what was done, 1–2 lines>
```

This is separate from the per-skill entries required by §6 rule 3. Both go in the same
file. A task with no entry is an undisclosed AI contribution (`FR-DOC-005`).
