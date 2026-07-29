"""OpenAI LLM adapter — implements AbstractLlmProvider.

Uses GPT-4o (or configurable model) for:
- Intent classification with function/tool calling
- Context-aware response generation
- RAG-grounded FAQ answering
- Text embedding generation

Phase 1: full implementation for real-time voice conversations.
"""

import json
import logging

from openai import AsyncOpenAI

from domain.interfaces.providers import AbstractLlmProvider, LlmIntentResult
from infrastructure.llm.prompts import (
    RECEPTIONIST_SYSTEM_PROMPT,
    FAQ_ANSWERING_SYSTEM,
)

logger = logging.getLogger(__name__)


class OpenAiLlm(AbstractLlmProvider):
    """OpenAI GPT-4o implementation of the LLM provider interface.

    Handles intent classification with function calling, context-aware
    response generation, RAG answer synthesis, and text embeddings.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """Initialise with OpenAI credentials.

        Args:
            api_key: OpenAI API key.
            model: Model name (default gpt-4o).
        """
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    # ── Chat Completions with Tool Calling (primary Phase 1 method) ──────

    async def chat_with_tools(
        self,
        messages: list[dict],
        tool_schemas: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 256,
    ) -> dict:
        """Send a chat completion request with tool/function schemas.

        This is the primary method for Phase 1. The LLM receives the
        conversation context + available tools and decides whether to
        respond with text or invoke a tool.

        Args:
            messages: Chat message history (system, user, assistant, tool roles).
            tool_schemas: OpenAI function-calling tool definitions.
            temperature: Response randomness (0.0–2.0).
            max_tokens: Maximum completion tokens.

        Returns:
            OpenAI chat completion response dict with:
                - content: str | None (text response)
                - tool_calls: list[dict] | None (function calls)
                - finish_reason: str
        """
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tool_schemas,
            tool_choice="auto",
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        message = choice.message

        return {
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                }
                for tc in (message.tool_calls or [])
            ],
            "finish_reason": choice.finish_reason,
        }

    # ── Intent Classification (legacy / Phase 1 fallback) ─────────────────

    async def classify_intent(
        self,
        transcript: str,
        conversation_history: list[dict],
        intent_definitions: list[dict],
        language: str = "en",
    ) -> LlmIntentResult:
        """Classify the caller's intent from the transcript.

        For Phase 1, intent classification is handled by the full
        chat_with_tools() flow. This method provides a lightweight
        fallback when tools are not needed.

        Args:
            transcript: The caller's transcribed utterance.
            conversation_history: Previous turns as dicts.
            intent_definitions: IntentDefinition entities serialised as dicts.
            language: Language code.

        Returns:
            LlmIntentResult with intent, confidence, entities, sentiment.
        """
        intent_names = [d.get("name", d.get("intent_name", "")) for d in intent_definitions]
        intent_desc = "\n".join(
            f"- {d.get('name', d.get('intent_name', ''))}: {d.get('description', d.get('display_label', ''))}"
            for d in intent_definitions
        )

        system_prompt = (
            "You are an intent classifier for a phone receptionist. "
            "Classify the caller's latest message into ONE of these intents:\n"
            f"{intent_desc}\n\n"
            "Return a JSON object with: intent, confidence (0-1), sentiment "
            "(positive/neutral/frustrated/urgent), entities (dict of extracted "
            "names/dates/times/resources). Only use JSON."
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Latest caller message: \"{transcript}\""},
            ],
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        try:
            data = json.loads(response.choices[0].message.content or "{}")
        except json.JSONDecodeError:
            data = {}

        return LlmIntentResult(
            intent=data.get("intent", "unknown"),
            confidence=float(data.get("confidence", 0.0)),
            entities=data.get("entities", {}),
            sentiment=data.get("sentiment", "neutral"),
        )

    # ── Response Generation ──────────────────────────────────────────────

    async def generate_response(
        self,
        intent: str,
        entities: dict,
        state: str,
        collected_slots: dict,
        knowledge_context: str | None = None,
    ) -> str:
        """Generate a natural language response for the given dialog state.

        Args:
            intent: The classified intent.
            entities: Extracted entities (dates, names, etc.).
            state: Current dialog state name.
            collected_slots: Slots collected so far.
            knowledge_context: Optional KB/FAQ context.

        Returns:
            Natural response text.
        """
        prompt = (
            f"Generate a brief, conversational phone response.\n"
            f"State: {state} | Intent: {intent}\n"
            f"Collected info: {collected_slots}\n"
            f"Extracted: {entities}\n"
        )
        if knowledge_context:
            prompt += f"\nKnowledge: {knowledge_context}"

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
        )
        return response.choices[0].message.content or "I'm sorry, could you repeat that?"

    # ── RAG FAQ Answering ────────────────────────────────────────────────

    async def answer_with_knowledge_base(
        self, question: str, faq_entries: list[dict], organization_name: str
    ) -> str:
        """Answer a question grounded in the provided FAQ entries (RAG).

        Args:
            question: The caller's question.
            faq_entries: FAQ entries with 'question' and 'answer' keys.
            organization_name: Organization name for context.

        Returns:
            Grounded answer string.
        """
        faq_text = "\n\n".join(
            f"Q: {e.get('question', '')}\nA: {e.get('answer', '')}"
            for e in faq_entries
        )
        prompt = FAQ_ANSWERING_SYSTEM.format(
            organization_name=organization_name,
            faq_context=faq_text,
            question=question,
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )
        return response.choices[0].message.content or "I'll connect you with someone who can help."

    # ── Embeddings ───────────────────────────────────────────────────────

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate a vector embedding for the given text.

        Used for FAQ semantic search / RAG retrieval.

        Args:
            text: Text to embed.

        Returns:
            1536-dimensional embedding vector (text-embedding-3-small).
        """
        response = await self._client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return response.data[0].embedding

    # ── Utility ──────────────────────────────────────────────────────────

    def build_messages(
        self,
        system_prompt: str,
        conversation_history: list[dict],
        latest_transcript: str,
    ) -> list[dict]:
        """Build the message list for a chat completion call.

        Args:
            system_prompt: The rendered system prompt.
            conversation_history: Previous user/assistant/tool messages.
            latest_transcript: The caller's latest utterance.

        Returns:
            Full message list for OpenAI chat completion.
        """
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": latest_transcript})
        return messages
