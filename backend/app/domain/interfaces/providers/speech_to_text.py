"""Abstract Speech-to-Text provider interface."""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class AbstractSttProvider(ABC):
    """Contract for real-time streaming and batch speech-to-text transcription.

    Real-time transcription is event-driven rather than request/response:
    callers push audio via send_audio() as it arrives, and the provider's
    own voice-activity detection decides when to emit transcript/speech
    events via events() — notably "utterance_end", which signals the
    caller has actually stopped talking.
    """

    @abstractmethod
    async def start_stream(self) -> None:
        """Open a streaming session."""
        ...

    @abstractmethod
    async def send_audio(self, audio_chunk: bytes) -> None:
        """Forward a raw audio chunk to the live transcription stream."""
        ...

    @abstractmethod
    def events(self) -> AsyncIterator[dict]:
        """Yield provider events as they arrive.

        Event shapes:
            {"event": "transcript", "text": str, "is_final": bool}
            {"event": "speech_started"}
            {"event": "utterance_end", "transcript": str}
        """
        ...

    @abstractmethod
    async def end_stream(self) -> None:
        """Close the streaming session."""
        ...

    @abstractmethod
    async def transcribe_file(self, audio_url: str) -> str:
        """Post-call batch transcription of a recording file."""
        ...
