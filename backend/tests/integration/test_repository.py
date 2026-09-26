"""ComplaintRepository against real PostgreSQL (FR-BE-017, T-M2-006)."""

import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.session import make_session_factory
from app.domain.enums import Category, Priority, Status, TriagedBy
from app.domain.errors import ComplaintNotFoundError, InvalidTransitionError
from app.domain.transitions import ensure_transition_allowed
from app.repositories.complaints import ComplaintRepository, NewComplaint


def new(
    category: Category = Category.WATER,
    priority: Priority = Priority.HIGH,
    suffix: str = "",
) -> NewComplaint:
    return NewComplaint(
        text=f"Water pipe burst near Chowk {suffix}".strip(),
        location="Saddar",
        reporter_contact=None,
        category=category,
        priority=priority,
        ai_summary="water: Water pipe burst near Chowk",
        triaged_by=TriagedBy.SIMULATED,
        triage_confidence=0.8,
        triage_latency_ms=12,
    )


@pytest.fixture
async def repo(engine: AsyncEngine) -> AsyncIterator[ComplaintRepository]:
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE complaints"))
    yield ComplaintRepository(make_session_factory(engine))


async def test_create_then_get(repo: ComplaintRepository) -> None:
    created = await repo.create(new())
    assert created.status is Status.OPEN and created.triaged_by is TriagedBy.SIMULATED
    assert await repo.get(created.id) == created
    assert await repo.get(uuid4()) is None


async def test_list_filters_and_counts_the_filtered_total(repo: ComplaintRepository) -> None:
    for i in range(3):
        await repo.create(new(Category.WATER, Priority.HIGH, f"w{i}"))
    await repo.create(new(Category.ROADS, Priority.HIGH, "r"))
    await repo.create(new(Category.WATER, Priority.LOW, "l"))

    items, total = await repo.list_page(
        category=Category.WATER, priority=Priority.HIGH, page_size=2
    )
    assert total == 3 and len(items) == 2
    assert all(c.category is Category.WATER and c.priority is Priority.HIGH for c in items)

    items, total = await repo.list_page(page=99)
    assert items == [] and total == 5


async def test_pagination_is_stable_across_identical_timestamps(
    repo: ComplaintRepository, engine: AsyncEngine
) -> None:
    for i in range(7):
        await repo.create(new(suffix=str(i)))
    async with engine.begin() as conn:  # every row now shares one created_at
        await conn.execute(
            text("UPDATE complaints SET created_at = '2026-09-01', updated_at = '2026-09-01'")
        )

    seen = []
    for page in (1, 2, 3):
        items, _ = await repo.list_page(page=page, page_size=3)
        seen += [c.id for c in items]
    assert len(seen) == 7 and len(set(seen)) == 7
    assert seen == sorted(seen, reverse=True)  # id DESC is the tie-break (AD-016)


async def test_list_query_orders_by_created_at_then_id(
    repo: ComplaintRepository, engine: AsyncEngine
) -> None:
    """The planner may hand back index order by luck on a small table; the SQL must say it."""
    statements: list[str] = []

    def capture(*args: object) -> None:
        statements.append(str(args[2]))

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        await repo.list_page(status=Status.OPEN)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
    page_sql = next(s for s in statements if "LIMIT" in s)
    assert "ORDER BY complaints.created_at DESC, complaints.id DESC" in page_sql


async def test_list_orders_newest_first(repo: ComplaintRepository) -> None:
    first = await repo.create(new(suffix="a"))
    second = await repo.create(new(suffix="b"))
    items, _ = await repo.list_page()
    assert [c.id for c in items] == [second.id, first.id]


async def test_permitted_transition_updates_status_and_updated_at(
    repo: ComplaintRepository,
) -> None:
    created = await repo.create(new())
    changed = await repo.change_status(created.id, Status.IN_PROGRESS, ensure_transition_allowed)
    assert changed.status is Status.IN_PROGRESS
    assert changed.updated_at > created.updated_at
    assert await repo.get(created.id) == changed


async def test_rejected_transition_writes_nothing(repo: ComplaintRepository) -> None:
    created = await repo.create(new())
    with pytest.raises(InvalidTransitionError):
        await repo.change_status(created.id, Status.RESOLVED, ensure_transition_allowed)
    assert await repo.get(created.id) == created  # status and updated_at untouched


async def test_unknown_id_is_not_found_before_the_table_is_consulted(
    repo: ComplaintRepository,
) -> None:
    def must_not_run(current: Status, target: Status) -> None:
        raise AssertionError("transition table consulted for a missing row")

    with pytest.raises(ComplaintNotFoundError):
        await repo.change_status(uuid4(), Status.OPEN, must_not_run)


async def test_status_change_waits_for_a_concurrent_writer(
    repo: ComplaintRepository, engine: AsyncEngine
) -> None:
    """Another transaction moves the row to in_progress and holds its lock. Our open ->
    in_progress must wait, then see the committed value and be rejected. Without FOR UPDATE it
    would read the stale 'open', pass the table check, and overwrite: a lost update."""
    created = await repo.create(new())
    async with engine.connect() as other:
        await other.execute(
            text("UPDATE complaints SET status = 'in_progress' WHERE id = :id"), {"id": created.id}
        )
        task = asyncio.create_task(
            repo.change_status(created.id, Status.IN_PROGRESS, ensure_transition_allowed)
        )
        await _until_a_backend_waits_on_a_lock(engine)
        await other.commit()
    with pytest.raises(InvalidTransitionError):
        await task


async def _until_a_backend_waits_on_a_lock(engine: AsyncEngine) -> None:
    query = text("SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock'")
    async with engine.connect() as conn:
        for _ in range(500):  # each iteration is a round trip, not a sleep
            if await conn.scalar(query):
                return
    raise AssertionError("change_status never blocked on the row lock")


async def test_counts_group_in_sql(repo: ComplaintRepository) -> None:
    await repo.create(new(Category.WATER, Priority.HIGH, "1"))
    await repo.create(new(Category.WATER, Priority.LOW, "2"))
    await repo.create(new(Category.ROADS, Priority.LOW, "3"))
    counts = await repo.counts()
    assert counts.by_category == {Category.WATER: 2, Category.ROADS: 1}
    assert counts.by_priority == {Priority.HIGH: 1, Priority.LOW: 2}
    assert counts.by_status == {Status.OPEN: 3}
