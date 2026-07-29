"""Groq LLM adapter — implements AbstractLlmProvider.

Uses Groq's OpenAI-compatible API for fast, cheap inference.
For 8B models: uses text-only chat (no native tool calling).
For 70B+ models: uses native tool calling with text fallback.
"""

import json
import logging

from openai import AsyncOpenAI

from domain.interfaces.providers import AbstractLlmProvider, LlmIntentResult
from infrastructure.llm.prompts import FAQ_ANSWERING_SYSTEM

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Groq 8B models can't reliably do native tool calling — use text mode
_TEXT_ONLY_MODELS = {"llama-3.1-8b-instant", "llama3-8b-8192", "gemma2-9b-it"}


class GroqLlm(AbstractLlmProvider):
    """Groq LLM provider — OpenAI-compatible API."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self._client = AsyncOpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
        self._model = model
        self._text_only = any(m in model.lower() for m in _TEXT_ONLY_MODELS)
        logger.info(f"Groq: model={model}, tool_calling={'text' if self._text_only else 'native'}")

    # ── Chat (primary Phase 1 method) ────────────────────────────────────

    async def chat_with_tools(
        self,
        messages: list[dict],
        tool_schemas: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 256,
    ) -> dict:
        """Send chat. For 8B models: text-only. For 70B+: native tools + fallback."""

        if self._text_only:
            return await self._text_chat(messages, tool_schemas, temperature, max_tokens)

        # 70B+: try native tool calling first
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=tool_schemas,
                tool_choice="auto",
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=10.0,
            )
            choice = response.choices[0]
            msg = choice.message
            return {
                "content": msg.content or "",
                "tool_calls": [
                    {"id": tc.id, "name": tc.function.name, "arguments": json.loads(tc.function.arguments)}
                    for tc in (msg.tool_calls or [])
                ],
                "finish_reason": choice.finish_reason,
            }
        except Exception:
            logger.warning("Groq native tool call failed, using text fallback")
            return await self._text_chat(messages, tool_schemas, temperature, max_tokens)

    async def _text_chat(
        self, messages: list[dict], tool_schemas: list[dict], temperature: float, max_tokens: int
    ) -> dict:
        """Pure text chat — no tool calling. Used for 8B models or fallback."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=10.0,
        )
        return {
            "content": response.choices[0].message.content or "",
            "tool_calls": [],
            "finish_reason": response.choices[0].finish_reason,
        }

    # ── Intent Classification ────────────────────────────────────────────

    async def classify_intent(
        self,
        transcript: str,
        conversation_history: list[dict],
        intent_definitions: list[dict],
        language: str = "en",
    ) -> LlmIntentResult:
        intent_desc = "\n".join(
            f'- {d.get("name","")}: {d.get("description","")}'
            for d in intent_definitions
        )
        system_prompt = (
            "Classify the caller's message into ONE intent.\n"
            f"{intent_desc}\n\n"
            'Return ONLY JSON: {"intent":"...","confidence":0.9,"sentiment":"neutral","entities":{}}'
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f'Caller: "{transcript}"'},
            ],
            temperature=0.1,
            max_tokens=200,
            timeout=8.0,
        )
        raw = response.choices[0].message.content or "{}"
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"intent": "unknown", "confidence": 0.5}
        return LlmIntentResult(
            intent=data.get("intent", "unknown"),
            confidence=float(data.get("confidence", 0.5)),
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
        prompt = (
            f"Generate a brief conversational phone response.\n"
            f"Intent: {intent} | State: {state}\n"
        )
        if knowledge_context:
            prompt += f"Knowledge: {knowledge_context}\n"
        prompt += "Keep it under 2 sentences. Be natural."
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
            timeout=8.0,
        )
        return response.choices[0].message.content or "How can I help?"

    # ── FAQ ──────────────────────────────────────────────────────────────

    async def answer_with_knowledge_base(
        self, question: str, faq_entries: list[dict], organization_name: str
    ) -> str:
        faq_text = "\n\n".join(
            f"Q: {e.get('question','')}\nA: {e.get('answer','')}" for e in faq_entries
        )
        prompt = FAQ_ANSWERING_SYSTEM.format(
            organization_name=organization_name, faq_context=faq_text, question=question
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
            timeout=8.0,
        )
        return response.choices[0].message.content or "I'll connect you with someone."

    async def generate_embedding(self, text: str) -> list[float]:
        raise NotImplementedError("Groq has no embeddings.")

    def build_messages(
        self, system_prompt: str, conversation_history: list[dict], latest_transcript: str
    ) -> list[dict]:
        msgs = [{"role": "system", "content": system_prompt}]
        msgs.extend(conversation_history)
        msgs.append({"role": "user", "content": latest_transcript})
        return msgs
