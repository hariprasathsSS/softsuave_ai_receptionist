"""Deepgram TTS adapter — implements AbstractTtsProvider.

Text-to-speech using Deepgram Aura (real-time streaming TTS).
Single provider for both STT + TTS reduces latency and simplifies
credential management.

Deepgram Aura voice models:
    aura-asteria-en  — female, professional
    aura-luna-en     — female, warm
    aura-stella-en   — female, bright
    aura-orion-en    — male, professional
    aura-hera-en     — female, calm
    aura-zeus-en     — male, authoritative
"""

import io
import logging
from typing import AsyncIterator

import httpx

from domain.interfaces.providers import AbstractTtsProvider

logger = logging.getLogger(__name__)

# Deepgram TTS endpoint
TTS_URL = "https://api.deepgram.com/v1/speak"

# Voice model mapping (our voice_style → Deepgram Aura model)
VOICE_MODEL_MAP = {
    "conversational": "aura-luna-en",
    "professional":   "aura-asteria-en",
    "cheerful":       "aura-stella-en",
    "calm":           "aura-hera-en",
    "male":           "aura-orion-en",
}


class DeepgramTts(AbstractTtsProvider):
    """Deepgram Aura text-to-speech provider.

    Uses Deepgram's streaming TTS endpoint. Returns PCM audio
    chunks that can be streamed to the caller in real-time.

    Same API key is used for both STT (Deepgram Nova-2) and
    TTS (Deepgram Aura) — single credential.
    """

    def __init__(self, api_key: str, voice_model: str = "aura-luna-en"):
        """Initialise with Deepgram credentials.

        Args:
            api_key: Deepgram API key (same as STT key).
            voice_model: Default Aura voice model name.
        """
        self._api_key = api_key
        self._voice_model = voice_model
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Lazily create and cache the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Token {self._api_key}",
                    "Accept": "audio/pcm",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    # ── Public API ───────────────────────────────────────────────────────

    async def synthesize_stream(
        self,
        text: str,
        voice_style: str = "conversational",
    ) -> AsyncIterator[bytes]:
        """Stream mulaw audio chunks as they are synthesised.

        Uses Deepgram TTS REST endpoint with streaming response.
        Yields mulaw audio chunks at 8kHz (Twilio-compatible).

        Args:
            text: Text to synthesise.
            voice_style: conversational | professional | cheerful | calm | male.

        Yields:
            Audio chunks (PCM16 bytes at 24kHz) as they arrive.
        """
        client = await self._ensure_client()
        model = VOICE_MODEL_MAP.get(voice_style, self._voice_model)

        payload = {"text": text}

        async with client.stream(
            "POST",
            f"{TTS_URL}?model={model}&encoding=mulaw&sample_rate=8000",
            json=payload,
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                logger.error(f"Deepgram TTS error {response.status_code}: {body}")
                raise RuntimeError(f"Deepgram TTS failed: {response.status_code}")

            async for chunk in response.aiter_bytes(chunk_size=4096):
                if chunk:
                    yield chunk

    async def synthesize_full(
        self,
        text: str,
        voice_style: str = "conversational",
    ) -> bytes:
        """Synthesise the full audio and return as a single buffer.

        Used for pre-recorded messages like greetings and voicemails.

        Args:
            text: Text to synthesise.
            voice_style: Voice style preset.

        Returns:
            Complete mulaw audio buffer at 8kHz.
        """
        buffer = io.BytesIO()
        async for chunk in self.synthesize_stream(text, voice_style):
            buffer.write(chunk)
        return buffer.getvalue()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
