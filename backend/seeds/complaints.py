"""Idempotent seed: `python -m seeds.complaints` from backend/ (FR-DATA-004, AD-022).

Exempt from BR-VAL-006, BR-STATUS-001 and BR-DATA-003: an administrative fixture loader that
runs before the system serves anyone, not a client. Rows represent history, so they carry a
spread of statuses. Attribution is `rules`, because no model ever saw them (BR-VOCAB-004).
"""

import asyncio
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import DatabaseSettings
from app.db.models import ComplaintRow
from app.domain.enums import Category, Priority, Status
from app.observability.logging import configure_logging, get_logger

# Fixed literal, never per machine, so ids are reproducible everywhere (AD-022).
SEED_UUID_NAMESPACE = UUID("6f2a1c94-3e5b-4d80-9a17-c0b8e4f21d63")
BASE_TIME = datetime(2026, 9, 1, 6, 0, tzinfo=UTC)

# (text, location, category, priority, status, reporter_contact)
SEED: list[tuple[str, str, str, str, str, str | None]] = [
    ("Burst water main flooding Street 12 since fajr, water entering ground floors. Please send KWSC team urgently.", "Gulshan-e-Iqbal Block 13-D", "water", "high", "in_progress", None),
    ("No water supply in our lane for four days, tanker mafia charging 5000 rupees. Old people suffering.", "North Nazimabad Block H", "water", "high", "open", None),
    ("Water coming very dirty and smelly from nalka since last week, bachay beemar ho rahay hain.", "Lyari, Chakiwara Road", "water", "high", "resolved", None),
    ("Small leakage from pipe near house number 45, water wasting whole day.", "PECHS Block 2", "water", "low", "open", None),
    ("Water pressure very low in morning timing, motor not pulling water to tanki upstairs.", "Gulistan-e-Jauhar Block 15", "water", "normal", "rejected", None),
    ("Live wire hanging from pole near masjid after last night storm, very dangerous for namazi.", "Korangi Sector 33-A", "electricity", "high", "in_progress", None),
    ("Load shedding 10 hours daily in our area even though everyone paying bills. K-Electric not listening.", "Orangi Town Sector 11-1/2", "electricity", "normal", "open", None),
    ("Transformer making loud noise and sparks since Tuesday, whole street scared it will blast.", "Malir Colony", "electricity", "high", "open", None),
    ("Electric meter reading wrong, bill came three times more than last month.", "Nazimabad No. 3", "electricity", "low", "resolved", None),
    # The redaction fixture (ADR-0004): a phone number inside the complaint text itself.
    ("Voltage fluctuation daily at maghrib time, fridge and UPS got damaged. Call me on 0300-1234567 for details.", "Federal B Area Block 10", "electricity", "normal", "open", "Imran, 0300-1234567"),
    ("Gutter overflow on main road for one week, sewage water standing in front of school.", "Shah Faisal Colony No. 2", "sanitation", "high", "in_progress", None),
    ("Manhole cover missing near Chowrangi, children playing there, very dangerous.", "Landhi No. 4", "sanitation", "high", "open", None),
    ("Kachra not picked up for ten days, garbage heap near park, mosquitoes and bad smell everywhere.", "Clifton Block 5", "sanitation", "normal", "in_progress", None),
    ("Sweeper not coming in our gali since Eid, litter everywhere.", "Saddar, near Empress Market", "sanitation", "low", "resolved", None),
    # Deliberately ambiguous: a choked drain that will flood homes (sanitation or water).
    ("Nala behind our houses is choked with plastic, when rain comes water will enter homes.", "Liaquatabad No. 10", "sanitation", "normal", "rejected", None),
    ("Big pothole on main Rashid Minhas Road, two motorcycle accidents this week already.", "Gulshan-e-Iqbal Block 6", "roads", "high", "in_progress", None),
    ("Road dug for gas line three months ago and never repaired, rickshaws getting stuck.", "Model Colony", "roads", "normal", "open", None),
    ("Speed breaker paint gone, cars jumping on it at night without seeing.", "DHA Phase 6", "roads", "low", "rejected", None),
    ("Footpath broken and tiles missing outside the hospital gate, patients falling.", "Karimabad", "roads", "normal", "in_progress", "ahmed.k@example.com"),
    ("Single pothole near bus stop filling with water whenever it rains.", "Bahadurabad", "roads", "low", "resolved", None),
    ("Streetlight not working for two weeks, street completely dark at night, chori ka dar hai.", "North Karachi Sector 5-C", "streetlights", "normal", "open", None),
    ("Bulb flickering on and off every night on pole number 17.", "Gulshan-e-Maymar", "streetlights", "low", "open", None),
    ("All lights on the service road are off, women scared to walk after isha.", "Gulistan-e-Jauhar Block 7", "streetlights", "high", "in_progress", None),
    ("Streetlight stays on in daytime also, electricity wasting.", "Defence View Phase 2", "streetlights", "low", "rejected", None),
    # Deliberately ambiguous: a fallen light pole with exposed wires (streetlights or electricity).
    ("Pole light fallen down after truck hit it, wires lying on footpath.", "Korangi Industrial Area", "streetlights", "high", "resolved", None),
    ("Stray dogs in big group near primary school, bachon ko kaat liya yesterday.", "Surjani Town Sector 4", "other", "high", "open", None),
    ("Wedding hall playing loud music till 3 am every night, nobody can sleep.", "Gulshan-e-Hadeed", "other", "normal", "open", None),
    ("Illegal parking of water tankers blocking whole lane in morning, ambulance could not enter.", "Federal B Area Block 16", "other", "normal", "in_progress", None),
    ("Park ki boundary wall broken, drug addicts sitting inside at night.", "Nazimabad No. 2", "other", "normal", "resolved", None),
    ("Signboard of our street fallen, delivery riders cannot find address.", "Mehmoodabad", "other", "low", "open", None),
]  # fmt: skip


def summarise(category: str, text: str) -> str:
    """AD-023's rules-path summary, so seeded rows look like what the rules path produces."""
    end = re.search(r"[.!?\n]", text)
    first = (text[: end.start()] if end else text)[:120]
    summary = f"{category}: {' '.join(first.split())}"
    return summary if len(summary) <= 140 else summary[:140].rsplit(" ", 1)[0]


def seed_rows() -> list[dict[str, Any]]:
    rows = []
    for i, (text, location, category, priority, status, contact) in enumerate(SEED):
        # The third and fourth rows share a timestamp on purpose: the AD-016 id tie-break
        # needs a real case to paginate across.
        created = BASE_TIME + timedelta(hours=7 * (i if i != 3 else 2))
        rows.append(
            {
                "id": uuid5(SEED_UUID_NAMESPACE, text),
                "text": text,
                "location": location,
                "reporter_contact": contact,
                "category": Category(category),
                "priority": Priority(priority),
                "status": Status(status),
                "ai_summary": summarise(category, text),
                "triaged_by": "rules",
                "triage_confidence": 0.35,
                "triage_latency_ms": 2 + i % 5,
                "created_at": created,
                "updated_at": created if status == "open" else created + timedelta(days=1),
            }
        )
    return rows


async def seed(database_url: str) -> int:
    """Insert the fixture set; returns how many rows were new. A second run returns 0."""
    engine = create_async_engine(database_url)
    try:
        statement = (
            insert(ComplaintRow).values(seed_rows()).on_conflict_do_nothing(index_elements=["id"])
        )
        async with engine.begin() as conn:
            result = await conn.execute(statement)
        return result.rowcount
    finally:
        await engine.dispose()


def main() -> None:
    configure_logging("INFO")
    inserted = asyncio.run(seed(DatabaseSettings().database_url))
    get_logger(__name__).info("seed.completed", inserted=inserted, fixture_rows=len(SEED))


if __name__ == "__main__":
    main()
