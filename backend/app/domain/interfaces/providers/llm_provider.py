"""Abstract LLM provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LlmIntentResult:
    """Structured result from LLM intent classification."""
    intent: str
    confidence: float
    entities: dict = field(default_factory=dict)
    sentiment: str = "neutral"           # positive | neutral | frustrated | urgent
    response_text: str | None = None
    is_grounded: bool = True              # Whether response is grounded in KB facts


class AbstractLlmProvider(ABC):
    """Contract for LLM-based NLU (intent classification + entity extraction + response generation)."""

    @abstractmethod
    async def classify_intent(
        self,
        transcript: str,
        conversation_history: list[dict],
        intent_definitions: list[dict],
        language: str = "en",
    ) -> LlmIntentResult:
        """Classify the caller's intent and extract entities."""
        ...

    @abstractmethod
    async def generate_response(
        self,
        intent: str,
        entities: dict,
        state: str,
        collected_slots: dict,
        knowledge_context: str | None = None,
    ) -> str:
        """Generate a natural language response for the given dialog state."""
        ...

    @abstractmethod
    async def answer_with_knowledge_base(
        self, question: str, faq_entries: list[dict], organization_name: str
    ) -> str:
        """Answer a question grounded in the provided FAQ entries (RAG)."""
        ...

    @abstractmethod
    async def generate_embedding(self, text: str) -> list[float]:
        """Generate a vector embedding for the given text."""
        ...
