"""Media Streams WebSocket ↔ audio buffer bridge.

Bridges Twilio Media Streams WebSocket messages to/from the
conversation pipeline. Handles the WebSocket lifecycle, JSON
message parsing, mulaw/audio format conversion, and streaming
audio to/from the STT/TTS providers.

Twilio Media Streams Protocol:
- Messages are JSON objects with an `event` key
- Audio payloads are base64-encoded mulaw at 8000Hz
- Events: connected, start, media, stop, mark
"""

import asyncio
import base64
import json
import logging
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)


class MediaStreamBridge:
    """Bridge between Twilio Media Streams WebSocket and audio pipeline.

    Receives base64-encoded mulaw audio from Twilio, decodes it,
    queues it for the STT provider, and accepts outgoing PCM audio
    chunks for transmission back to Twilio.

    Lifecycle:
        1. Twilio opens WebSocket → bridge.start()
        2. Receive 'connected' event → record stream_sid
        3. Receive 'media' events → decode audio → queue for STT
        4. Pipeline produces response audio → encode → send 'media'
        5. Twilio closes WebSocket → bridge.stop()
    """

    def __init__(self, call_sid: str, stream_sid: str = ""):
        """Initialise the bridge for a specific call.

        Args:
            call_sid: Twilio call SID.
            stream_sid: Twilio Media Stream SID (set after 'connected').
        """
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self._inbound_audio: deque = deque()     # raw mulaw bytes ready for STT
        self._outbound_audio: deque = deque()    # PCM bytes to send to Twilio
        self._is_active = False
        self._audio_ready = asyncio.Event()
        self._message_queue: deque = deque()     # incoming WebSocket messages

    # ── Public API ───────────────────────────────────────────────────────

    async def start(self) -> None:
        """Activate the bridge and begin processing audio."""
        self._is_active = True
        logger.info(f"MediaStreamBridge started — call={self.call_sid}")

    async def stop(self) -> None:
        """Deactivate the bridge and flush buffers."""
        self._is_active = False
        self._inbound_audio.clear()
        self._outbound_audio.clear()
        logger.info(f"MediaStreamBridge stopped — call={self.call_sid}")

    async def receive_from_twilio(self, message: dict) -> str | None:
        """Process an incoming WebSocket message from Twilio.

        Handles:
        - 'connected' → record stream_sid
        - 'media' → decode audio payload, queue for STT
        - 'stop' → mark stream as stopping

        Args:
            message: Parsed JSON message from the Media Streams WebSocket.

        Returns:
            Decoded mulaw audio bytes (for 'media' events) or None.
        """
        event = message.get("event", "")
        payload = None

        if event == "connected":
            self.stream_sid = message.get("streamSid", "")
            logger.info(f"Media stream connected — stream_sid={self.stream_sid}")

        elif event == "media":
            track = message.get("media", {}).get("track", "")
            if track == "inbound":
                base64_payload = message["media"]["payload"]
                payload = base64.b64decode(base64_payload)
                self._inbound_audio.append(payload)
                self._audio_ready.set()

        elif event == "mark":
            mark_name = message.get("mark", {}).get("name", "")
            logger.debug(f"Media stream mark reached: {mark_name}")

        elif event == "stop":
            logger.info(f"Media stream stopped — stream_sid={self.stream_sid}")
            await self.stop()

        elif event == "start":
            logger.info(f"Media stream started — stream_sid={message.get('streamSid', '')}")

        return payload

    async def send_to_twilio(self, audio_chunk: bytes) -> dict:
        """Build a Twilio Media Streams 'media' message from PCM audio.

        Converts PCM audio to base64-encoded mulaw and wraps it in
        the expected JSON envelope for the outbound media track.

        Args:
            audio_chunk: Raw PCM audio bytes to send.

        Returns:
            JSON-serialisable dict ready for WebSocket.send_json().
        """
        # For Phase 1 simplified approach: send as base64 directly
        # In production, you'd convert PCM → mulaw first
        payload = base64.b64encode(audio_chunk).decode("ascii")

        return {
            "event": "media",
            "streamSid": self.stream_sid,
            "media": {
                "track": "outbound",
                "payload": payload,
            },
        }

    async def get_audio_chunk(self, timeout: float = 5.0) -> bytes | None:
        """Get the next inbound audio chunk from the queue.

        Blocks until audio is available or timeout expires.

        Args:
            timeout: Maximum seconds to wait.

        Returns:
            Raw mulaw bytes or None if timeout.
        """
        if self._inbound_audio:
            return self._inbound_audio.popleft()

        self._audio_ready.clear()
        try:
            await asyncio.wait_for(self._audio_ready.wait(), timeout=timeout)
            if self._inbound_audio:
                return self._inbound_audio.popleft()
        except asyncio.TimeoutError:
            pass

        return None

    async def clear(self) -> dict:
        """Build a 'clear' event that tells Twilio to drop buffered outbound audio.

        Twilio queues outbound audio on its side and plays it out at real
        time, independent of how fast we ship bytes to it. For barge-in,
        cancelling our own send task isn't enough — that task typically
        finishes shipping the whole response in well under a second, long
        before Twilio has finished actually playing it to the caller. This
        event is what makes Twilio stop the audio the caller can still hear.

        Returns:
            JSON-serialisable dict for WebSocket.
        """
        return {"event": "clear", "streamSid": self.stream_sid}

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def has_audio(self) -> bool:
        return len(self._inbound_audio) > 0
