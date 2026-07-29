"""Deepgram STT adapter — implements AbstractSttProvider.

Streams caller audio to Deepgram's live transcription WebSocket
(Nova-2) in real time. Deepgram runs its own voice-activity detection
on the audio and tells us — via an "UtteranceEnd" event — exactly when
the caller has stopped talking. There is no local buffering or
silence-guessing: the transcript for a turn is only assembled and
handed off once Deepgram itself signals the utterance is complete.
"""

import logging
from typing import AsyncIterator, Optional

import httpx
from deepgram import AsyncDeepgramClient

from domain.interfaces.providers import AbstractSttProvider

logger = logging.getLogger(__name__)

STT_FILE_URL = "https://api.deepgram.com/v1/listen"


class DeepgramStt(AbstractSttProvider):
    """Deepgram Nova-2 live speech-to-text provider.

    One instance per call — holds a persistent WebSocket connection to
    Deepgram and accumulates finalized transcript segments for the
    current utterance until Deepgram emits UtteranceEnd.
    """

    def __init__(self, api_key: str, utterance_end_ms: int = 1000):
        self._api_key = api_key
        self._utterance_end_ms = utterance_end_ms
        self._client = AsyncDeepgramClient(api_key=api_key)
        self._socket_cm = None
        self._socket = None
        self._segments: list[str] = []
        self._file_client: Optional[httpx.AsyncClient] = None

    # ── Public API ───────────────────────────────────────────────────────

    async def start_stream(self) -> None:
        self._socket_cm = self._client.listen.v1.connect(
            model="nova-2",
            encoding="mulaw",
            sample_rate=8000,
            channels=1,
            smart_format="true",
            punctuate="true",
            interim_results="true",
            vad_events="true",
            utterance_end_ms=self._utterance_end_ms,
        )
        self._socket = await self._socket_cm.__aenter__()
        self._segments = []
        logger.info("Deepgram live STT stream started")

    async def send_audio(self, audio_chunk: bytes) -> None:
        await self._socket.send_media(audio_chunk)

    async def events(self) -> AsyncIterator[dict]:
        async for message in self._socket:
            msg_type = getattr(message, "type", None)

            if msg_type == "Results":
                alternatives = message.channel.alternatives if message.channel else []
                transcript = (alternatives[0].transcript if alternatives else "") or ""
                transcript = transcript.strip()
                if not transcript:
                    continue
                if message.is_final:
                    self._segments.append(transcript)
                yield {"event": "transcript", "text": transcript, "is_final": bool(message.is_final)}

            elif msg_type == "SpeechStarted":
                yield {"event": "speech_started"}

            elif msg_type == "UtteranceEnd":
                full_text = " ".join(self._segments).strip()
                self._segments = []
                yield {"event": "utterance_end", "transcript": full_text}

    async def end_stream(self) -> None:
        if self._socket_cm is not None:
            try:
                await self._socket.send_close_stream()
            except Exception:
                pass
            try:
                await self._socket_cm.__aexit__(None, None, None)
            except Exception:
                pass
        self._socket = None
        self._socket_cm = None
        if self._file_client:
            await self._file_client.aclose()
            self._file_client = None
        logger.info("Deepgram live STT stream ended")

    async def transcribe_file(self, audio_url: str) -> str:
        """Post-call batch transcription of a recording file (REST API)."""
        if self._file_client is None:
            self._file_client = httpx.AsyncClient(
                headers={"Authorization": f"Token {self._api_key}"},
                timeout=httpx.Timeout(15.0, connect=10.0),
            )
        params = {"model": "nova-2", "smart_format": "true", "punctuate": "true"}
        response = await self._file_client.post(STT_FILE_URL, params=params, json={"url": audio_url})
        if response.status_code != 200:
            raise RuntimeError(f"Deepgram transcription failed: {response.status_code}")
        data = response.json()
        channels = data.get("results", {}).get("channels", [])
        if channels:
            return channels[0].get("alternatives", [{}])[0].get("transcript", "")
        return ""
