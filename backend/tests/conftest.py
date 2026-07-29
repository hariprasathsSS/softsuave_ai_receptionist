"""Test configuration and shared fixtures."""

import pytest
from unittest.mock import AsyncMock


@pytest.fixture
def mock_stt_provider():
    """Mock STT provider emitting a single canned utterance_end event."""
    async def fake_events():
        yield {"event": "speech_started"}
        yield {"event": "utterance_end", "transcript": "I'd like to book an appointment"}

    provider = AsyncMock()
    provider.events = fake_events
    provider.transcribe_file.return_value = "Full transcript text."
    return provider


@pytest.fixture
def mock_tts_provider():
    """Mock TTS provider returning dummy audio bytes."""
    provider = AsyncMock()
    provider.synthesize_stream.return_value = iter([b"\x00\x00" * 100])
    provider.synthesize_full.return_value = b"\x00\x00" * 1000
    return provider


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider with predefined intent responses."""
    from domain.interfaces.providers.llm_provider import LlmIntentResult

    provider = AsyncMock()
    provider.classify_intent.return_value = LlmIntentResult(
        intent="book_appointment",
        confidence=0.92,
        entities={"date": "2026-07-13"},
    )
    provider.generate_response.return_value = "I'd be happy to help with that."
    provider.answer_with_knowledge_base.return_value = "Our hours are 9 AM to 8 PM."
    return provider


@pytest.fixture
def mock_telephony_provider():
    """Mock telephony provider."""
    provider = AsyncMock()
    provider.answer_call.return_value = None
    provider.make_outbound_call.return_value = "CA_mock_call_sid"
    provider.send_sms.return_value = "SM_mock_message_sid"
    return provider


@pytest.fixture
def mock_booking_repository():
    """Mock booking repository."""
    repo = AsyncMock()
    repo.find_conflicting.return_value = None
    repo.create.return_value = None
    return repo


@pytest.fixture
def call_session():
    """A fresh CallSession for testing."""
    from domain.entities.call_session import CallSession
    from domain.entities.value_objects import PhoneNumber

    return CallSession(
        call_sid="CA_test123",
        caller_number=PhoneNumber(raw="+15551234567"),
        caller_name="Test Caller",
    )
