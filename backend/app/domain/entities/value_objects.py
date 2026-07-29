"""Value objects and enums used across all domain entities.

These are immutable, self-validating primitives with no external dependencies.
"""

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


# ── Enums ────────────────────────────────────────────────────────────────

class DialogState(str, Enum):
    """All possible conversation states in the dialog FSM."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"

    GREETING = "greeting"
    ANSWERING_FAQ = "answering_faq"
    GIVING_HOURS = "giving_hours"
    GIVING_LOCATION = "giving_location"

    COLLECT_BOOKING_RESOURCE = "collect_booking_resource"
    COLLECT_BOOKING_DATE = "collect_booking_date"
    COLLECT_BOOKING_TIME = "collect_booking_time"
    CHECK_AVAILABILITY = "check_availability"
    PROPOSE_SLOTS = "propose_slots"
    COLLECT_BOOKING_NAME = "collect_booking_name"
    COLLECT_BOOKING_PHONE = "collect_booking_phone"
    CONFIRM_BOOKING = "confirm_booking"
    EXECUTE_BOOKING = "execute_booking"

    VERIFY_BOOKING = "verify_booking"
    CONFIRM_CANCELLATION = "confirm_cancellation"
    EXECUTE_CANCELLATION = "execute_cancellation"
    COLLECT_RESCHEDULE_DATE = "collect_reschedule_date"

    INFORM_TRANSFER = "inform_transfer"
    EXECUTE_TRANSFER = "execute_transfer"
    TRANSFER_FAILED = "transfer_failed"
    ESCALATE_URGENT = "escalate_urgent"

    OFFER_WAITLIST = "offer_waitlist"
    COLLECT_WAITLIST_INFO = "collect_waitlist_info"

    OUTBOUND_DELIVER_MESSAGE = "outbound_deliver_message"
    OUTBOUND_COLLECT_RESPONSE = "outbound_collect_response"

    GOODBYE = "goodbye"
    ENDED = "ended"
    ERROR = "error"


class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class CallOutcome(str, Enum):
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    TRANSFERRED_WARM = "transferred_warm"
    TRANSFERRED_COLD = "transferred_cold"
    TRANSFER_FAILED = "transfer_failed"
    ABANDONED = "abandoned"
    ERROR = "error"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    URGENT = "urgent"


class Language(str, Enum):
    EN = "en"
    ES = "es"
    FR = "fr"
    DE = "de"
    ZH = "zh"
    AR = "ar"


# ── Value Objects ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PhoneNumber:
    """Validated, E.164-formatted phone number."""
    raw: str

    def __post_init__(self):
        if not self.raw.startswith("+"):
            raise ValueError(f"Phone number must be E.164 format: {self.raw}")

    @property
    def masked(self) -> str:
        """Return masked version for logging: +1555****4567."""
        if len(self.raw) < 9:
            return self.raw[:5] + "****"
        return self.raw[:5] + "****" + self.raw[-4:]

    @property
    def hash(self) -> str:
        """SHA-256 hash for caller identification."""
        import hashlib
        return hashlib.sha256(self.raw.encode()).hexdigest()


@dataclass(frozen=True)
class TimeRange:
    """A time interval with start and end."""
    start: str  # HH:MM
    end: str    # HH:MM

    def __post_init__(self):
        for t in (self.start, self.end):
            parts = t.split(":")
            if (
                len(parts) != 2
                or not all(p.isdigit() and len(p) == 2 for p in parts)
                or not (0 <= int(parts[0]) <= 23)
                or not (0 <= int(parts[1]) <= 59)
            ):
                raise ValueError(f"Invalid time format: {t}")


@dataclass(frozen=True)
class Slot:
    """A bookable time slot on a specific date."""
    date: str          # YYYY-MM-DD
    time_range: TimeRange
    resource_name: str

    def __str__(self) -> str:
        return f"{self.date} {self.time_range.start}-{self.time_range.end} with {self.resource_name}"


@dataclass(frozen=True)
class IntentResult:
    """Result of NLU intent classification."""
    intent: str
    confidence: float
    entities: dict = field(default_factory=dict)

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0-1: {self.confidence}")


@dataclass(frozen=True)
class ConversationTurn:
    """A single turn in the conversation: speaker → text."""
    speaker: str    # "caller" | "ai"
    text: str
    sentiment: Sentiment = Sentiment.NEUTRAL
    intent: IntentResult | None = None
    timestamp_ms: int = 0
