"""Unit tests for CallSession entity."""

import pytest

from domain.entities.call_session import CallSession
from domain.entities.value_objects import (
    PhoneNumber,
    DialogState,
    IntentResult,
    Sentiment,
)


class TestCallSession:
    def test_initial_state_is_idle(self):
        session = CallSession(call_sid="CA_test")
        assert session.state == DialogState.IDLE

    def test_advance_changes_state(self):
        session = CallSession(call_sid="CA_test")
        session.advance(DialogState.GREETING, IntentResult(intent="greeting", confidence=0.99))
        assert session.state == DialogState.GREETING
        assert len(session.intent_history) == 1

    def test_end_sets_ended_state_and_timestamp(self):
        session = CallSession(call_sid="CA_test")
        session.end()
        assert session.state == DialogState.ENDED
        assert session.ended_at is not None

    def test_duration_returns_seconds(self):
        session = CallSession(call_sid="CA_test")
        session.end()
        assert session.duration_seconds >= 0

    def test_low_confidence_count(self):
        session = CallSession(call_sid="CA_test")
        session.intent_history = [
            IntentResult(intent="unknown", confidence=0.4),
            IntentResult(intent="unknown", confidence=0.3),
        ]
        assert session.low_confidence_count == 2

    def test_set_slot_stores_value(self):
        session = CallSession(call_sid="CA_test")
        session.set_slot("date", "2026-07-13")
        assert session.collected_slots["date"] == "2026-07-13"
