"""Caller and CallLog entities."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class CallerProfile:
    """Recognized caller with interaction history."""
    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID | None = None
    phone_number_hash: str = ""
    name: str = ""
    preferred_language: str = "en"
    is_vip: bool = False
    last_interaction_at: datetime | None = None
    total_calls: int = 0
    total_bookings: int = 0
    notes: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CallLog:
    """Structured log of a completed call."""
    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID | None = None
    domain_profile_id: UUID | None = None
    call_sid: str = ""
    caller_number_hash: str = ""
    caller_name: str | None = None
    language: str = "en"
    intents_detected: list[dict] = field(default_factory=list)
    actions_taken: list[dict] = field(default_factory=list)
    outcome: str = "in_progress"
    sentiment_summary: dict = field(default_factory=dict)
    duration_seconds: int = 0
    recording_url: str | None = None
    transcript_text: str | None = None
    transcript_json: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
