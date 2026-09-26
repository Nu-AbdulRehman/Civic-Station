"""Create the complaint enums, the complaints table, its constraints and its three indexes.

Revision ID: 0001
Revises:
Create Date: 2026-09-26

Enum values are written out literally, not imported from app.domain: a revision is a frozen
record of the schema at one point in time and must not change when the application does.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

category = postgresql.ENUM(
    "water", "electricity", "sanitation", "roads", "streetlights", "other",
    name="complaint_category", create_type=False,
)  # fmt: skip
priority = postgresql.ENUM("high", "normal", "low", name="complaint_priority", create_type=False)
status = postgresql.ENUM(
    "open", "in_progress", "resolved", "rejected", name="complaint_status", create_type=False
)
ENUMS = (category, priority, status)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in ENUMS:
        enum.create(bind, checkfirst=False)  # a leftover type must fail loudly

    op.create_table(
        "complaints",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("location", sa.Text(), nullable=False),
        sa.Column("reporter_contact", sa.Text(), nullable=True),
        sa.Column("category", category, nullable=False),
        sa.Column("priority", priority, nullable=False),
        sa.Column("status", status, server_default="open", nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=False),
        sa.Column("triaged_by", sa.String(32), nullable=False),
        sa.Column("triage_confidence", sa.Double(), nullable=False),
        sa.Column("triage_latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_complaints"),
        sa.CheckConstraint(
            "char_length(text) BETWEEN 10 AND 2000", name="ck_complaints_text_length"
        ),
        sa.CheckConstraint(
            "char_length(location) BETWEEN 3 AND 200", name="ck_complaints_location_length"
        ),
        sa.CheckConstraint(
            "reporter_contact IS NULL OR char_length(reporter_contact) <= 200",
            name="ck_complaints_reporter_contact_length",
        ),
        sa.CheckConstraint(
            "char_length(ai_summary) <= 140", name="ck_complaints_ai_summary_length"
        ),
        sa.CheckConstraint(
            "triaged_by IN ('llm:groq', 'llm:ollama', 'rules', 'rules:fallback', 'simulated')",
            name="ck_complaints_triaged_by_allowed",
        ),
        sa.CheckConstraint(
            "triage_confidence BETWEEN 0 AND 1", name="ck_complaints_triage_confidence_range"
        ),
        sa.CheckConstraint(
            "triage_latency_ms >= 0", name="ck_complaints_triage_latency_non_negative"
        ),
        sa.CheckConstraint("updated_at >= created_at", name="ck_complaints_updated_after_created"),
    )

    # AD-049 / 04-M3-data §2.2: each index serves one named query.
    # Default listing: ORDER BY created_at DESC, id DESC (AD-016 tie-break).
    op.create_index(
        "ix_complaints_created_at_id",
        "complaints",
        [sa.text("created_at DESC"), sa.text("id DESC")],
    )
    # Operations filter: WHERE status = :s AND priority = :p ORDER BY created_at DESC.
    op.create_index(
        "ix_complaints_status_priority_created",
        "complaints",
        ["status", "priority", sa.text("created_at DESC")],
    )
    # Category filter: WHERE category = :c ORDER BY created_at DESC.
    op.create_index(
        "ix_complaints_category_created",
        "complaints",
        ["category", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_table("complaints")  # drops its indexes and constraints with it
    bind = op.get_bind()
    # Explicit: autogenerate does not always emit DROP TYPE, and a leftover type breaks the
    # next upgrade (04-M3-data §2.3).
    for enum in reversed(ENUMS):
        enum.drop(bind, checkfirst=False)
