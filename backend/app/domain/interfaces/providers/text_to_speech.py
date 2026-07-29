"""Abstract Text-to-Speech provider interface."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class AbstractTtsProvider(ABC):
    """Contract for streaming text-to-speech synthesis."""

    @abstractmethod
    async def synthesize_stream(self, text: str, voice_style: str = "conversational") -> AsyncIterator[bytes]:
        """Convert text to streaming PCM audio chunks."""
        ...

    @abstractmethod
    async def synthesize_full(self, text: str, voice_style: str = "conversational") -> bytes:
        """Convert text to a single complete audio buffer (for pre-recorded messages)."""
        ...
