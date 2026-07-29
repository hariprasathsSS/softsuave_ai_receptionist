"""CallSession entity — the core in-call mutable state object.

Represents everything the system knows about a single active phone call.
Lives in Redis during the call; persisted to call_logs table post-call.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from domain.entities.value_objects import (
    DialogState,
    IntentResult,
    ConversationTurn,
    PhoneNumber,
    Sentiment,
    Language,
)


@dataclass
class CallSession:
    """Mutable state for an active phone call."""

    id: UUID = field(default_factory=uuid4)
    call_sid: str = ""                            # Twilio Call SID

    # Resolved at call start (Phase 2+)
    tenant_id: UUID | None = None
    domain_profile_id: UUID | None = None
    organization_name: str = ""

    # Caller identity
    caller_number: PhoneNumber | None = None
    caller_name: str | None = None
    is_returning: bool = False
    is_vip: bool = False

    # Language
    language: Language = Language.EN

    # Dialog state
    state: DialogState = DialogState.IDLE
    intent_history: list[IntentResult] = field(default_factory=list)
    collected_slots: dict = field(default_factory=dict)  # e.g., {"date":"2026-07-13", "name":"John"}

    # Conversation transcript
    turns: list[ConversationTurn] = field(default_factory=list)
    sentiment_scores: dict[str, int] = field(default_factory=lambda: {
        Sentiment.POSITIVE: 0,
        Sentiment.NEUTRAL: 0,
        Sentiment.FRUSTRATED: 0,
        Sentiment.URGENT: 0,
    })

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None

    def advance(self, new_state: DialogState, intent: IntentResult | None = None):
        """Advance the dialog state and record the intent."""
        self.state = new_state
        if intent:
            self.intent_history.append(intent)

    def add_turn(self, turn: ConversationTurn):
        """Record a conversation turn and update sentiment counts."""
        self.turns.append(turn)
        self.sentiment_scores[turn.sentiment] += 1

    def set_slot(self, key: str, value: str):
        """Set a collected slot value."""
        self.collected_slots[key] = value

    def end(self):
        """Mark call as ended."""
        self.state = DialogState.ENDED
        self.ended_at = datetime.now(timezone.utc)

    @property
    def duration_seconds(self) -> float:
        end = self.ended_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()

    @property
    def low_confidence_count(self) -> int:
        """Number of consecutive low-confidence intents (for escalation trigger)."""
        count = 0
        for intent in reversed(self.intent_history):
            if intent.confidence < 0.6:
                count += 1
            else:
                break
        return count
