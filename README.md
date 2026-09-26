# Civic-Station

## Database migrations and seed

The schema is created only by Alembic, never at application startup (`BR-DATA-001`). Both
commands run from `backend/` as a deliberate step, with `DATABASE_URL` in the environment:

```sh
uv run alembic upgrade head        # create or upgrade the schema
uv run python -m seeds.complaints  # load the 30 fixture complaints; safe to re-run
```

The seed is idempotent: ids are UUIDv5 over a fixed namespace and inserts use
`ON CONFLICT (id) DO NOTHING`, so a second run inserts nothing (`AD-022`).

Integration tests run against real PostgreSQL and Redis. They refuse any database whose name
does not end in `_test`, because they downgrade the schema:

```sh
DATABASE_URL=postgresql+asyncpg://<user>@<host>:<port>/civic_test \
REDIS_URL=redis://<host>:<port>/0 \
uv run pytest tests/integration
```

## Frontend API types

`frontend/src/api/types.ts` is generated from the backend's OpenAPI schema and committed; it is
never edited by hand (`FR-FE-012`). After any backend contract change, regenerate it and let
`tsc --noEmit` show what broke:

```sh
cd frontend && npm run gen:types   # exports the schema from the app factory; no server needed
npm run typecheck
```

## Screenshots

Captured from the running app (backend with `TRIAGE_PROVIDER=rules`, seeded database):

| Submit | Dashboard | Stats |
|---|---|---|
| ![Submit](docs/evidence/submit.png) | ![Dashboard](docs/evidence/dashboard.png) | ![Stats](docs/evidence/stats.png) |

The dashboard shows the server's own 409 message after an attempted `resolved → open`; the stats
view shows `HIT` on the second load inside the 30-second TTL.

## Repository checks

```sh
python scripts/check_submission.py   # layer rules and frontend single-source-of-truth; exit 1 on findings
```

Standard library only. It walks the backend's AST for reverse imports, SQL or vendor SDKs outside
their layer, environment reads outside `app/config.py`, concrete triage classes outside
`providers/triage/`, and schema DDL outside migrations; and it scans `frontend/src/` for
hand-written enum lists or transition maps. Triage measurements behind `docs/TRIAGE.md` come from
`scripts/measure_triage.py`.
