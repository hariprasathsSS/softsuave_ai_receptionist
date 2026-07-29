"""Unit tests for value objects."""

import pytest

from domain.entities.value_objects import (
    PhoneNumber,
    TimeRange,
    Slot,
    IntentResult,
)


class TestPhoneNumber:
    def test_e164_format_accepted(self):
        pn = PhoneNumber(raw="+15551234567")
        assert pn.raw == "+15551234567"

    def test_non_e164_rejected(self):
        with pytest.raises(ValueError):
            PhoneNumber(raw="5551234567")

    def test_masked_shows_partial(self):
        pn = PhoneNumber(raw="+15551234567")
        masked = pn.masked
        assert "****" in masked
        assert "567" in masked[-4:]
        assert "+1555" in masked[:5]


class TestTimeRange:
    def test_valid_time_range(self):
        tr = TimeRange(start="09:00", end="17:00")
        assert tr.start == "09:00"
        assert tr.end == "17:00"

    def test_invalid_format_rejected(self):
        with pytest.raises(ValueError):
            TimeRange(start="9:00", end="17:00")

    def test_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            TimeRange(start="25:00", end="26:00")


class TestIntentResult:
    def test_confidence_in_range(self):
        result = IntentResult(intent="booking", confidence=0.85)
        assert result.confidence == 0.85

    def test_confidence_out_of_range(self):
        with pytest.raises(ValueError):
            IntentResult(intent="booking", confidence=1.5)

    def test_entities_default_empty(self):
        result = IntentResult(intent="greeting", confidence=0.99)
        assert result.entities == {}
