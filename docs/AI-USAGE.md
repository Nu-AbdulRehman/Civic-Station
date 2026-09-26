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
