"""M3 schema: reversible migration, model/migration agreement, DB-level rules, index use."""

import asyncio
from typing import Any

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.models import Base

VALID: dict[str, Any] = {
    "text": "Water pipe burst near Chowk",
    "location": "G-9 Markaz",
    "reporter_contact": None,
    "category": "water",
    "priority": "high",
    "ai_summary": "water: Water pipe burst near Chowk",
    "triaged_by": "rules",
    "triage_confidence": 0.35,
    "triage_latency_ms": 3,
}
INSERT = text(
    "INSERT INTO complaints (text, location, reporter_contact, category, priority, ai_summary,"
    " triaged_by, triage_confidence, triage_latency_ms) VALUES (:text, :location,"
    " :reporter_contact, :category, :priority, :ai_summary, :triaged_by, :triage_confidence,"
    " :triage_latency_ms) RETURNING id, status, created_at, updated_at"
)
INDEXES = {
    "ix_complaints_created_at_id",
    "ix_complaints_status_priority_created",
    "ix_complaints_category_created",
}


async def _enum_types(engine: AsyncEngine) -> set[str]:
    query = text("SELECT typname FROM pg_type WHERE typtype = 'e' AND typname LIKE 'complaint%'")
    async with engine.connect() as conn:
        return set((await conn.execute(query)).scalars())


async def test_up_down_up_cycle(alembic_config: Config, engine: AsyncEngine) -> None:
    # Alembic's env runs its own event loop, so the sync commands go to a worker thread.
    await asyncio.to_thread(command.downgrade, alembic_config, "base")
    assert await _enum_types(engine) == set()  # downgrade dropped every type it created
    await asyncio.to_thread(command.upgrade, alembic_config, "head")
    await asyncio.to_thread(command.downgrade, alembic_config, "base")
    await asyncio.to_thread(command.upgrade, alembic_config, "head")
    assert await _enum_types(engine) == {
        "complaint_category",
        "complaint_priority",
        "complaint_status",
    }


async def test_model_matches_migration(engine: AsyncEngine) -> None:
    def diff(sync_conn: Any) -> list[Any]:
        return list(compare_metadata(MigrationContext.configure(sync_conn), Base.metadata))

    async with engine.connect() as conn:
        assert await conn.run_sync(diff) == []


async def test_valid_row_gets_server_defaults(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        row = (await conn.execute(INSERT, VALID)).one()
        await conn.rollback()
    assert row.id is not None and row.status == "open"
    assert row.created_at.utcoffset() is not None and row.updated_at == row.created_at


@pytest.mark.parametrize(
    "override",
    [
        {"text": "123456789"},
        {"text": "x" * 2001},
        {"location": "ab"},
        {"reporter_contact": "x" * 201},
        {"ai_summary": "x" * 141},
        {"ai_summary": None},
        {"triage_confidence": 1.5},
        {"triage_confidence": None},
        {"triage_latency_ms": -1},
        {"triaged_by": "llm:openai"},
        {"category": "Water"},
        {"priority": "urgent"},
    ],
)
async def test_database_rejects_what_the_domain_forbids(
    engine: AsyncEngine, override: dict[str, Any]
) -> None:
    """Rejected by the database itself, with no Python validation in front (BR-DATA-002)."""
    async with engine.connect() as conn:
        with pytest.raises(DBAPIError):
            await conn.execute(INSERT, VALID | override)
        await conn.rollback()


async def test_updated_at_cannot_precede_created_at(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        row = (await conn.execute(INSERT, VALID)).one()
        with pytest.raises(DBAPIError):
            await conn.execute(
                text("UPDATE complaints SET updated_at = created_at - interval '1 second'"
                     " WHERE id = :id"),
                {"id": row.id},
            )  # fmt: skip
        await conn.rollback()


@pytest.mark.parametrize(
    ("query", "index"),
    [
        (
            "SELECT id FROM complaints ORDER BY created_at DESC, id DESC LIMIT 20 OFFSET 0",
            "ix_complaints_created_at_id",
        ),
        (
            "SELECT id FROM complaints WHERE status = 'open' AND priority = 'high'"
            " ORDER BY created_at DESC LIMIT 20",
            "ix_complaints_status_priority_created",
        ),
        (
            "SELECT id FROM complaints WHERE category = 'water' ORDER BY created_at DESC LIMIT 20",
            "ix_complaints_category_created",
        ),
    ],
)
async def test_named_query_uses_its_index_without_a_sort(
    engine: AsyncEngine, query: str, index: str
) -> None:
    """04-M3-data §2.2 acceptance. Seq scan disabled: the table is too small to prefer an index."""
    async with engine.connect() as conn:
        await conn.execute(text("SET LOCAL enable_seqscan = off"))
        plan = "\n".join((await conn.execute(text(f"EXPLAIN {query}"))).scalars())
        await conn.rollback()
    assert index in plan, plan
    assert "Sort" not in plan, plan


async def test_indexes_exist_by_name(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        names: set[str] = set(
            (
                await conn.execute(
                    text("SELECT indexname FROM pg_indexes WHERE tablename = 'complaints'")
                )
            ).scalars()
        )
    assert names >= INDEXES
