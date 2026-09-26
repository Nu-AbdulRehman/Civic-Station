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
