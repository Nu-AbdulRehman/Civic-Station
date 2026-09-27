"""ORM model mirroring revision 0001 (AD-032). Schema changes come only from Alembic."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Double,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.enums import Category, Priority, Status, TriagedBy

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _pg_enum(enum: type[Enum], name: str) -> SAEnum:
    # Store the lower-case values, not the Python member names (BR-VOCAB-001…003).
    return SAEnum(enum, name=name, values_callable=lambda e: [m.value for m in e])


TRIAGED_BY_VALUES = ", ".join(f"'{v.value}'" for v in TriagedBy)


class ComplaintRow(Base):
    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint("char_length(text) BETWEEN 10 AND 2000", name="text_length"),
        CheckConstraint("char_length(location) BETWEEN 3 AND 200", name="location_length"),
        CheckConstraint(
            "reporter_contact IS NULL OR char_length(reporter_contact) <= 200",
            name="reporter_contact_length",
        ),
        CheckConstraint("char_length(ai_summary) <= 140", name="ai_summary_length"),
        CheckConstraint(f"triaged_by IN ({TRIAGED_BY_VALUES})", name="triaged_by_allowed"),
        CheckConstraint("triage_confidence BETWEEN 0 AND 1", name="triage_confidence_range"),
        CheckConstraint("triage_latency_ms >= 0", name="triage_latency_non_negative"),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        # AD-049: each index paired with the query it serves (04-M3-data §2.2).
        Index("ix_complaints_created_at_id", text("created_at DESC"), text("id DESC")),
        Index(
            "ix_complaints_status_priority_created",
            "status",
            "priority",
            text("created_at DESC"),
        ),
        Index("ix_complaints_category_created", "category", text("created_at DESC")),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    text: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(Text)
    reporter_contact: Mapped[str | None] = mapped_column(Text)
    category: Mapped[Category] = mapped_column(_pg_enum(Category, "complaint_category"))
    priority: Mapped[Priority] = mapped_column(_pg_enum(Priority, "complaint_priority"))
    status: Mapped[Status] = mapped_column(
        _pg_enum(Status, "complaint_status"), server_default=Status.OPEN.value
    )
    ai_summary: Mapped[str] = mapped_column(Text)
    triaged_by: Mapped[str] = mapped_column(String(32))
    triage_confidence: Mapped[float] = mapped_column(Double)
    triage_latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
