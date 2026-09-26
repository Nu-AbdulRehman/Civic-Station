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

Integration tests run against real PostgreSQL and refuse any database whose name does not end
in `_test`, because they downgrade the schema:

```sh
DATABASE_URL=postgresql+asyncpg://<user>@<host>:<port>/civic_test uv run pytest tests/integration
```
