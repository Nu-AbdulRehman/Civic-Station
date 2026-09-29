# Contributing

Rules for working on this repository. `CLAUDE.md` holds the full engineering rules; this page is
the part every contributor needs before the first commit.

## Branches

- `main` holds deployable software only. It accepts merges from `dev` through a pull request with
  green CI and one approval. Nobody pushes to it directly.
- `dev` is where work is integrated. Feature branches are cut from `dev` and merged back into it
  by pull request.
- Branch names carry the task id: `<type>/<task-id>-<slug>`, for example
  `feat/T-M5-006-triage-pipeline` or `fix/T-M6-010-ollama-cpu-limit`.

## Commits

Conventional Commits, with the task or requirement id when one applies:

```
feat(triage): fall back to rules on provider failure (FR-AI-008)
```

| Prefix | For |
|---|---|
| `feat` | New behaviour |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `test` | Tests or evidence only |
| `refactor` | Restructuring with no behaviour change |
| `ci` | Workflows and pipeline |
| `chore` | Tooling, dependencies, housekeeping |

`perf` is also accepted for a measured performance change.

## Pull requests

- Link the Issue the PR resolves (`Closes #<n>`).
- The partner reviews with a substantive comment; nobody approves their own PR.
- All eight CI checks must pass: `lint-and-type`, `test-backend`, `test-frontend`, `build`,
  `scan`, `manifests`, `integration`, `submission-check`.
- **Merge with a merge commit, never squash or rebase.** Squashing rewrites history that later
  branches and the commit record depend on.

## Before you push

```sh
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app tests seeds alembic && uv run pytest
cd frontend && npm run lint && npm run typecheck && npm run test:coverage
python scripts/check_submission.py
```

Never commit a secret, a `.env` file, or a real value in a Kubernetes Secret manifest. If one slips
through, follow `docs/RUNBOOK.md` §5 and record it in `docs/INCIDENTS.md`.

## AI assistance

Record every AI-assisted change in `docs/AI-USAGE.md`, in the format it describes.
