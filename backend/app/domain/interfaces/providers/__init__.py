"""Abstract provider interfaces (ports for external services)."""

from .speech_to_text import AbstractSttProvider
from .text_to_speech import AbstractTtsProvider
from .llm_provider import AbstractLlmProvider, LlmIntentResult
from .telephony_provider import AbstractTelephonyProvider

__all__ = [
    "AbstractSttProvider",
    "AbstractTtsProvider",
    "AbstractLlmProvider", "LlmIntentResult",
    "AbstractTelephonyProvider",
]
