"""Twilio telephony adapter — implements AbstractTelephonyProvider.

Wraps the Twilio REST API for voice call control. Handles answering,
audio streaming (via Media Streams), hold/resume, transfer, and
outbound calling.

Phase 1 scope:
- answer_call, send_audio, receive_audio, end_call
- make_outbound_call, send_sms (Phase 2+)
- transfer, hold (Phase 4+)
"""

import asyncio
import logging
from typing import AsyncIterator

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from domain.interfaces.providers import AbstractTelephonyProvider

logger = logging.getLogger(__name__)


class TwilioTelephony(AbstractTelephonyProvider):
    """Twilio implementation of the telephony provider interface.

    Uses Twilio's REST API for call control. Media Streams audio
    I/O is handled by MediaStreamBridge + WebSocket handler.
    """

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        default_from_number: str,
    ):
        """Initialise with Twilio credentials.

        Args:
            account_sid: Twilio Account SID.
            auth_token: Twilio Auth Token.
            default_from_number: Default outgoing caller ID (E.164).
        """
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._default_from_number = default_from_number
        self._client: Client | None = None

    async def _get_client(self) -> Client:
        """Lazily create the Twilio REST client (sync — wrapped in thread)."""
        if self._client is None:
            self._client = await asyncio.to_thread(
                lambda: Client(self._account_sid, self._auth_token)
            )
        return self._client

    # ── Core call control ────────────────────────────────────────────────

    async def answer_call(self, call_sid: str) -> None:
        """Answer an incoming call.

        Args:
            call_sid: Twilio Call SID.
        """
        client = await self._get_client()
        try:
            await asyncio.to_thread(
                lambda: client.calls(call_sid).update(status="in-progress")
            )
            logger.info(f"Call answered — call_sid={call_sid}")
        except TwilioRestException as e:
            logger.error(f"Failed to answer call {call_sid}: {e}")
            raise

    async def send_audio(self, call_sid: str, audio_chunk: bytes) -> None:
        """Send audio to a call via Media Streams (WebSocket).

        Note: This is handled by the WebSocket bridge, not REST API.
        This method is a thin wrapper for the orchestrator's interface.

        Args:
            call_sid: Twilio Call SID.
            audio_chunk: Audio bytes to send.
        """
        # Audio is sent via MediaStreamBridge, not via this method.
        # The orchestrator iterates TTS output and sends via WebSocket.
        raise NotImplementedError(
            "Audio is sent via MediaStreamBridge/WebSocket, not REST API."
            " Use the WebSocket handler for audio streaming."
        )

    async def receive_audio(self, call_sid: str) -> AsyncIterator[bytes]:
        """Receive audio from the caller via Media Streams (WebSocket).

        Note: Audio flows through MediaStreamBridge, not REST API.
        The WebSocket handler feeds audio into the STT pipeline.

        Args:
            call_sid: Twilio Call SID.

        Yields:
            Audio chunks from the caller.
        """
        # Audio is received via MediaStreamBridge, not via this method.
        # WebSocket handler calls bridge.get_audio_chunk() directly.
        raise NotImplementedError(
            "Audio is received via MediaStreamBridge/WebSocket, not REST API."
            " Use the WebSocket handler for audio streaming."
        )

    async def end_call(self, call_sid: str) -> None:
        """Hang up the call.

        Args:
            call_sid: Twilio Call SID.
        """
        client = await self._get_client()
        try:
            await asyncio.to_thread(
                lambda: client.calls(call_sid).update(status="completed")
            )
            logger.info(f"Call ended — call_sid={call_sid}")
        except TwilioRestException as e:
            logger.error(f"Failed to end call {call_sid}: {e}")
            raise

    # ── Hold / Resume (Phase 4) ──────────────────────────────────────────

    async def place_on_hold(self, call_sid: str, music_url: str | None = None) -> None:
        """Place a call on hold with optional music (Phase 4)."""
        raise NotImplementedError("Phase 4 implementation pending")

    async def resume_from_hold(self, call_sid: str) -> None:
        """Resume a call from hold (Phase 4)."""
        raise NotImplementedError("Phase 4 implementation pending")

    # ── Transfer (Phase 4) ───────────────────────────────────────────────

    async def transfer_call(self, call_sid: str, target_phone: str, transfer_type: str = "cold") -> dict:
        """Transfer call to another number (Phase 4)."""
        raise NotImplementedError("Phase 4 implementation pending")

    # ── Outbound calling (Phase 2) ───────────────────────────────────────

    async def make_outbound_call(self, to_phone: str, from_phone: str) -> str:
        """Initiate an outbound call (Phase 2).

        Args:
            to_phone: Destination number (E.164).
            from_phone: Caller ID to display (E.164).

        Returns:
            Call SID.
        """
        raise NotImplementedError("Phase 2 implementation pending")

    # ── Messaging (Phase 2) ──────────────────────────────────────────────

    async def send_sms(self, to_phone: str, body: str) -> str:
        """Send an SMS message (Phase 2).

        Args:
            to_phone: Destination number (E.164).
            body: SMS body text.

        Returns:
            Message SID.
        """
        raise NotImplementedError("Phase 2 implementation pending")

    async def send_whatsapp(self, to_phone: str, body: str) -> str:
        """Send a WhatsApp message (Phase 2+).

        Args:
            to_phone: Destination number.
            body: Message body text.

        Returns:
            Message SID.
        """
        raise NotImplementedError("Phase 3 implementation pending")
