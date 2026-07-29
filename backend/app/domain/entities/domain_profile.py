"""DomainProfile aggregate root — configuration that transforms the generic engine into a domain-specific receptionist."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class FaqEntry:
    """A single FAQ question-answer pair with optional embedding."""
    id: UUID = field(default_factory=uuid4)
    domain_profile_id: UUID | None = None
    question: str = ""
    answer: str = ""
    category: str | None = None
    priority: int = 0
    is_active: bool = True


@dataclass
class IntentDefinition:
    """A domain-specific intent with training examples and required slots."""
    id: UUID = field(default_factory=uuid4)
    domain_profile_id: UUID | None = None
    intent_name: str = ""                 # "book_appointment", "ask_faq"
    display_label: str = ""
    training_examples: list[str] = field(default_factory=list)
    required_slots: list[dict] = field(default_factory=list)
    response_template: str | None = None
    priority: int = 0


@dataclass
class EscalationRoute:
    """A route for transferring calls to a human/department."""
    id: UUID = field(default_factory=uuid4)
    domain_profile_id: UUID | None = None
    target_name: str = ""
    phone_number: str = ""
    intent_triggers: list[str] = field(default_factory=list)
    urgency_threshold: str = "urgent"
    fallback_behavior: str = "voicemail"   # voicemail | callback | message


@dataclass
class NotificationTemplate:
    """A template for SMS/WhatsApp notifications."""
    id: UUID = field(default_factory=uuid4)
    domain_profile_id: UUID | None = None
    event_type: str = ""                   # booking_confirmation | booking_reminder | booking_cancellation
    channel: str = "sms"                   # sms | whatsapp
    template_body: str = ""                # "Hi {caller_name}, your booking is confirmed..."
    reminder_lead_minutes: int | None = None
    is_active: bool = True


@dataclass
class BookingConfig:
    """Domain-specific booking workflow configuration."""
    id: UUID = field(default_factory=uuid4)
    domain_profile_id: UUID | None = None
    resource_type: str = ""                # "doctor", "room", "stylist"
    slot_duration_minutes: int = 30
    buffer_minutes: int = 5
    confirmation_template: str | None = None


@dataclass
class DomainProfile:
    """The complete configuration that shapes AI behavior for a specific vertical."""
    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID | None = None
    name: str = ""
    organization_name: str = ""
    greeting_template: str = "Hello, thank you for calling {organization}. How can I help you today?"
    voice_style: str = "conversational"    # formal | conversational
    operating_hours: dict = field(default_factory=dict)
    timezone: str = "UTC"
    is_active: bool = True

    # Sub-collections
    faq_entries: list[FaqEntry] = field(default_factory=list)
    intent_definitions: list[IntentDefinition] = field(default_factory=list)
    escalation_routes: list[EscalationRoute] = field(default_factory=list)
    notification_templates: list[NotificationTemplate] = field(default_factory=list)
    booking_config: BookingConfig | None = None

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def get_greeting(self) -> str:
        """Render the greeting with organization name substituted."""
        return self.greeting_template.replace("{organization}", self.organization_name)

    def is_within_operating_hours(self, dt: datetime) -> bool:
        """Check if a datetime falls within configured operating hours."""
        day_name = dt.strftime("%a").lower()[:3]
        day_hours = self.operating_hours.get(day_name)
        if not day_hours:
            return False
        current_time = dt.strftime("%H:%M")
        return day_hours.get("open", "00:00") <= current_time <= day_hours.get("close", "23:59")
