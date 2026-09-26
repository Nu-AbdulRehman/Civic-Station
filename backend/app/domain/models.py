"""Wire and domain models. One Pydantic vocabulary for HTTP input, HTTP output and model output."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Category, ConfiguredProvider, ErrorClass, Priority, Status, TriagedBy

SUMMARY_MAX_LENGTH = 140


class ComplaintCreate(BaseModel):
    """POST /api/complaints body. No category/priority/status field (BR-VAL-005)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=10, max_length=2000)
    location: str = Field(min_length=3, max_length=200)
    reporter_contact: str | None = Field(default=None, max_length=200)


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Status


class TriageResult(BaseModel):
    """Validates provider output before any of it is used (BR-TRIAGE-002/003)."""

    model_config = ConfigDict(extra="forbid")

    category: Category
    priority: Priority
    summary: str = Field(min_length=1, max_length=SUMMARY_MAX_LENGTH)
    confidence: float = Field(ge=0.0, le=1.0)


class Complaint(BaseModel):
    """The resource returned by create, get and list (01-api-contract §1)."""

    id: UUID
    text: str
    location: str
    reporter_contact: str | None
    category: Category
    priority: Priority
    status: Status
    ai_summary: str = Field(max_length=SUMMARY_MAX_LENGTH)
    triaged_by: TriagedBy
    triage_confidence: float = Field(ge=0.0, le=1.0)
    triage_latency_ms: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class ComplaintPage(BaseModel):
    items: list[Complaint]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class Stats(BaseModel):
    """Every enum key always present with an explicit zero (AD-025)."""

    total: int = Field(ge=0)
    by_category: dict[Category, int]
    by_priority: dict[Priority, int]
    by_status: dict[Status, int]
    generated_at: datetime


class ProviderOutcome(BaseModel):
    complaint_id: UUID
    provider: TriagedBy
    latency_ms: int = Field(ge=0)
    fallback: bool
    error_class: ErrorClass | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    at: datetime


class ProvidersMeta(BaseModel):
    active_provider: TriagedBy
    configured: ConfiguredProvider
    recent: list[ProviderOutcome]


class VersionInfo(BaseModel):
    version: str
    provider: TriagedBy


class HealthStatus(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyStatus(BaseModel):
    status: Literal["ready"] = "ready"
    checks: dict[Literal["database", "cache"], Literal["ok", "fail"]]
