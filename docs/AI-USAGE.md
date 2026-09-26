# AI usage

## Documentation

The final documentation in this repository was written with AI assistance (Claude Code).
The AI drafted, structured and formatted the text. All guidance behind it came from a
human in the loop: what to build, how to build it, scope and non-goals, and every ADR and
resolution-log decision in `docs/decisions/OPEN-DECISIONS.md`. The AI recorded those
decisions; it did not make them. The problem statement in `docs/planning/` is the course
brief and was not AI-written.

## Task log

One entry per completed task, appended by the agent that did it (`CLAUDE.md` §8).

- 2026-09-26 · main · Created `docs/AI-USAGE.md` with the Documentation disclosure and
  added the task-logging rule to `CLAUDE.md` §8.
- 2026-09-26 · main · Added the task-log rule to `AGENTS.md` (new "Task log" section and
  item 7 of the phase definition of done).
- 2026-09-26 · feat/T-M2-001-backend-skeleton · A1 (T-M2-001/002/003, FR-BE-010/018/020,
  BR-VOCAB-*, BR-STATUS-002/004): contract-first FastAPI skeleton with all 11 endpoints stubbed,
  `domain/` (enums, transition table, errors, models), typed `config.py`, 32 unit tests,
  root `.gitignore`. Files: `.gitignore`, `backend/**`.
- 2026-09-26 · feat/T-M2-004-errors-observability · A2 (T-M2-004/005, BR-VAL-004, FR-BE-023/024/026,
  NFR-OBS-001/003): single error envelope incl. 400/404/405/413/415/500, request-id middleware,
  structlog JSON logs, fixed Prometheus metrics, path param renamed to `{id}`; AD-057/058 recorded.
  Files: `backend/app/{errors,main}.py`, `backend/app/observability/*`, `backend/tests/**`,
  `docs/decisions/OPEN-DECISIONS.md`.
- 2026-09-26 · feat/T-M3-001-schema-migration · A3 (T-M3-001…004, FR-DATA-001/002/003,
  BR-DATA-001/002, AD-020/021/026/049): async Alembic env, revision `0001` (enum types, table,
  every CHECK, three indexes, strict type drop), `Mapped` ORM model, engine factory,
  `DatabaseSettings`, 20 integration tests against real PostgreSQL. Files: `backend/alembic*`,
  `backend/app/{config.py,db/*}`, `backend/tests/integration/*`, `backend/pyproject.toml`.
- 2026-09-26 · feat/T-M2-006-repositories-seed · A4 (T-M2-006, T-M3-005/006, FR-BE-016/017,
  FR-DATA-004, BR-STATUS-006/007, AD-016/022/059): `ComplaintRepository` (create, get, filtered
  page + total, locked status change, GROUP BY counts), 30-row idempotent seed, migrate/seed
  commands in `README.md`, 13 integration tests. Files: `backend/app/repositories/complaints.py`,
  `backend/seeds/*`, `backend/tests/integration/*`, `README.md`, `OPEN-DECISIONS.md`.

## Skill invocations

One entry per skill run (`CLAUDE.md` §6 rule 3).

### 2026-09-26 · feat/T-M2-001-backend-skeleton
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A1 (T-M2-001/002/003) from the
  `03-M2-backend.md` task table, `00-conventions.md` §3/§4 and `01-api-contract.md`.
- **I changed:** accepted as-is. Noted one document conflict: `06-M5-ai-triage.md` places
  `TriageResult` in `providers/triage/base.py`, while `00-conventions.md` §1 and T-M2-002 place it
  in `domain/`. Conventions outrank module guides, so it lives in `domain/` and `base.py` will
  re-export it in T-M5-001.

### 2026-09-26 · feat/T-M2-004-errors-observability
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A2 (T-M2-004/005).
- **I changed:** accepted as-is. Added the 413/415 body checks to A2 because `01-api-contract.md`
  §0 places them in middleware and they must emit the §4 envelope.

### 2026-09-26 · feat/T-M2-004-errors-observability
- **Tool:** Claude Code + `ponytail`
- **Shaped / Wrote:** Decision stubs `AD-057` (log field names) and `AD-058` (500 and
  framework-level error envelopes) in the `OPEN-DECISIONS.md` resolution log.
- **I changed:** accepted as-is. Also collapsed the request-id, logging and metrics steps of
  `03-M2-backend.md` §2.3 into one ASGI middleware; the fixed order is preserved inside it.

### 2026-09-26 · feat/T-M3-001-schema-migration
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A3 (T-M3-001…004).
- **I changed:** Put all three indexes in revision `0001`, following `04-M3-data.md` §2.3 and
  `FR-DATA-003`/`AD-049`; the same document's task table still says "Revision 0002: the two
  indexes" (T-M3-004), which §2.3 itself calls the stale wording. `0002` stays reserved.

### 2026-09-26 · feat/T-M2-006-repositories-seed
- **Tool:** Claude Code + `caveman`
- **Shaped / Wrote:** Stripped task list for work package A4 (T-M2-006, T-M3-005/006).
- **I changed:** T-M3-006 reduced to documenting the migrate and seed commands in `README.md`:
  there is no `compose.yaml` yet, and wiring it is T-M6-006 (Dev 2, `AD-013`).

### 2026-09-26 · feat/T-M2-006-repositories-seed
- **Tool:** Claude Code + `ponytail`
- **Shaped / Wrote:** Decision stub `AD-059` (the repository owns the transaction; status change
  is lock, check, update in one method).
- **I changed:** accepted as-is.
