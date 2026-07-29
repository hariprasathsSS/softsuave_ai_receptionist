"""Abstract Telephony provider interface."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class AbstractTelephonyProvider(ABC):
    """Contract for telephony operations (PSTN/SIP calls, SMS, WhatsApp)."""

    @abstractmethod
    async def answer_call(self, call_sid: str) -> None:
        """Answer an inbound call."""
        ...

    @abstractmethod
    async def send_audio(self, call_sid: str, audio_chunk: bytes) -> None:
        """Send an audio chunk to the active call."""
        ...

    @abstractmethod
    async def receive_audio(self, call_sid: str) -> AsyncIterator[bytes]:
        """Stream incoming audio from the caller."""
        ...

    @abstractmethod
    async def place_on_hold(self, call_sid: str, music_url: str | None = None) -> None:
        """Place caller on hold with optional music."""
        ...

    @abstractmethod
    async def resume_from_hold(self, call_sid: str) -> None:
        """Resume caller from hold."""
        ...

    @abstractmethod
    async def transfer_call(self, call_sid: str, target_phone: str, transfer_type: str = "cold") -> dict:
        """Transfer the call to another number. Returns transfer result."""
        ...

    @abstractmethod
    async def end_call(self, call_sid: str) -> None:
        """Hang up the call."""
        ...

    @abstractmethod
    async def make_outbound_call(self, to_phone: str, from_phone: str) -> str:
        """Initiate an outbound call. Returns call_sid."""
        ...

    @abstractmethod
    async def send_sms(self, to_phone: str, body: str) -> str:
        """Send an SMS message. Returns message SID."""
        ...

    @abstractmethod
    async def send_whatsapp(self, to_phone: str, body: str) -> str:
        """Send a WhatsApp message. Returns message SID."""
        ...
