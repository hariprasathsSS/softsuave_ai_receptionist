"""Domain entities — Phase 1 call state + Phase 2 entity dataclasses."""

from .value_objects import (
    PhoneNumber, TimeRange, Slot, Language, Sentiment,
    IntentResult, DialogState, BookingStatus, CallOutcome,
)
from .call_session import CallSession
from .domain_profile import DomainProfile, FaqEntry, IntentDefinition, EscalationRoute, NotificationTemplate, BookingConfig
from .caller import CallerProfile, CallLog

__all__ = [
    "PhoneNumber", "TimeRange", "Slot", "Language", "Sentiment",
    "IntentResult", "DialogState", "BookingStatus", "CallOutcome",
    "CallSession",
    "DomainProfile", "FaqEntry", "IntentDefinition", "EscalationRoute", "NotificationTemplate", "BookingConfig",
    "CallerProfile", "CallLog",
]
