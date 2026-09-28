"""Seed: exactly 30 rows, the required distribution, idempotent (FR-DATA-004, BR-DATA-004)."""

from collections import Counter

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from seeds.complaints import seed, seed_rows


async def test_seed_twice_changes_nothing(engine: AsyncEngine, database_url: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE complaints"))

    async def snapshot() -> list[tuple[object, ...]]:
        async with engine.connect() as conn:
            query = text("SELECT id, status, updated_at FROM complaints ORDER BY id")
            return [tuple(r) for r in await conn.execute(query)]

    assert await seed(database_url) == 30
    first = await snapshot()
    assert await seed(database_url) == 0
    assert await snapshot() == first and len(first) == 30


def test_seed_distribution() -> None:
    rows = seed_rows()
    assert len(rows) == 30
    assert len({r["id"] for r in rows}) == 30
    categories = Counter(r["category"] for r in rows)
    priorities = Counter(r["priority"] for r in rows)
    assert len(categories) == 6 and min(categories.values()) >= 4
    assert len(priorities) == 3 and min(priorities.values()) >= 8
    assert Counter(r["status"] for r in rows) == {
        "open": 12,
        "in_progress": 8,
        "resolved": 6,
        "rejected": 4,
    }
    assert all(r["triaged_by"] == "rules" and len(r["ai_summary"]) <= 140 for r in rows)
    assert any("0300-1234567" in r["text"] for r in rows)  # redaction fixture (ADR-0004)


def test_seed_ids_are_reproducible() -> None:
    assert [r["id"] for r in seed_rows()] == [r["id"] for r in seed_rows()]
    assert str(seed_rows()[0]["id"]) == "ceade3ca-f5f8-5cd6-9625-e27c2b0cdb1f"
