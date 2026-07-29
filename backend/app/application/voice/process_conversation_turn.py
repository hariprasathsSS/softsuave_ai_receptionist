"""Process a single conversation turn — Phase 1 core pipeline.

This is the heart of the AI receptionist: every time the caller speaks,
this use case processes their transcript through the full pipeline:
    1. LLM with tool calling → intent + entities + optional tool calls
    2. Tool dispatcher → execute tool if LLM chose one
    3. FSM guard → validate state transition
    4. Response composer → generate spoken response

Audio synthesis is NOT done here — the WebSocket handler
(presentation/websockets/call_media_stream.py) owns TTS streaming so it
can stream chunks to Twilio and cancel mid-flight on barge-in; synthesizing
here too would just be a second, discarded TTS call on every turn.

Architecture:
    ProcessConversationTurn
      ├── OpenAiLlm.chat_with_tools()   — decide intent/tool
      ├── ToolDispatcher.dispatch()     — execute tool if needed
      ├── DialogStateMachine.transition() — validate next state
      └── ResponseComposer.compose()    — render response text
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from domain.entities.call_session import CallSession
from domain.entities.domain_profile import DomainProfile
from domain.entities.value_objects import DialogState, IntentResult, ConversationTurn, Sentiment

from application.voice.dialog_state_machine import DialogStateMachine
from application.voice.response_composer import ResponseComposer
from application.voice.tool_dispatcher import ToolDispatcher, ToolCall, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class TurnResult:
    """Output of processing one conversation turn."""
    response_text: str
    next_state: DialogState
    intent: Optional[IntentResult] = None
    tool_results: list[ToolResult] = field(default_factory=list)
    is_terminal: bool = False


class ProcessConversationTurn:
    """Process a single caller utterance through the full AI pipeline.

    Dependencies:
        - llm: OpenAiLlm instance (for chat_with_tools)
        - tool_dispatcher: ToolDispatcher instance
        - fsm: DialogStateMachine
        - composer: ResponseComposer
    """

    def __init__(
        self,
        llm,                       # OpenAiLlm
        tool_dispatcher,           # ToolDispatcher
        fsm: DialogStateMachine,
        composer: ResponseComposer,
        max_tool_turns: int = 5,
    ):
        self._llm = llm
        self._tool_dispatcher = tool_dispatcher
        self._fsm = fsm
        self._composer = composer
        self._max_tool_turns = max_tool_turns

    async def execute(
        self,
        transcript: str,
        session: CallSession,
        domain_profile: Optional[DomainProfile] = None,
    ) -> TurnResult:
        """Process one caller utterance through the complete pipeline.

        The "ReAct loop" with tools:
        1. Send transcript + history to LLM with tool schemas
        2. If LLM returns a tool call → dispatch → feed result back → repeat
        3. If LLM returns content → that's the response
        4. Validate state transition via FSM
        5. Compose response text

        Args:
            transcript: The caller's transcribed utterance.
            session: The active CallSession entity (state, history, slots).
            domain_profile: The resolved domain profile (optional in Phase 1).

        Returns:
            TurnResult with response text and next state.
        """
        # ── 1. Build conversation history ────────────────────────────────
        messages = self._build_messages(session)
        # Add the latest transcript as user message
        messages.append({"role": "user", "content": transcript})

        # ── 2. LLM call ──────────────────────────────────────────────────
        # Phase 1: use simple text chat (no tool calling).
        # Phase 2+: ReAct loop with tools.
        tool_schemas = self._tool_dispatcher.get_schemas()
        tool_results: list[ToolResult] = []

        llm_result = await self._llm.chat_with_tools(
            messages=messages,
            tool_schemas=tool_schemas,
        )

        response_text = llm_result.get("content") or "I'm sorry, how can I help?"

        # Record the turn in session
        session.add_turn(ConversationTurn(
            speaker="caller",
            text=transcript,
            sentiment=Sentiment.NEUTRAL,
        ))

        # ── 3. Determine next state ──────────────────────────────────────
        next_state = self._determine_next_state(session, tool_results)

        # ── 4. Validate via FSM ──────────────────────────────────────────
        validated_state = self._fsm.transition(session.state, next_state)
        session.advance(validated_state)

        # ── 5. Compose response ──────────────────────────────────────────
        if response_text:
            composed = response_text
        else:
            composed = self._composer.state_response(
                state=validated_state,
                domain_profile=domain_profile,
                context=session.collected_slots,
            )

        # Record AI turn
        session.add_turn(ConversationTurn(
            speaker="ai",
            text=composed,
            sentiment=Sentiment.NEUTRAL,
        ))

        return TurnResult(
            response_text=composed,
            next_state=validated_state,
            tool_results=tool_results,
            is_terminal=self._fsm.is_terminal(validated_state),
        )

    # ── Private helpers ──────────────────────────────────────────────────

    def _build_messages(self, session: CallSession) -> list[dict]:
        """Build message list from recent conversation history."""
        from infrastructure.llm.prompts import RECEPTIONIST_SYSTEM_PROMPT

        system_prompt = RECEPTIONIST_SYSTEM_PROMPT.format(
            organization_name=session.organization_name or "our company",
            caller_name=session.caller_name or "guest",
            caller_phone=str(session.caller_number.raw) if hasattr(session.caller_number, 'raw') else str(session.caller_number or "unknown"),
            is_returning="yes" if session.is_returning else "no",
            conversation_history=self._format_history(session) or "(first message)",
        )
        messages = [{"role": "system", "content": system_prompt}]

        # Include last 3 turns only — prevents stale "I'll connect you" repetition
        for turn in session.turns[-3:]:
            role = "user" if turn.speaker == "caller" else "assistant"
            messages.append({"role": role, "content": turn.text})

        return messages

    def _format_history(self, session: CallSession) -> str:
        """Format conversation history for the LLM prompt."""
        if not session.turns:
            return "(no previous turns)"
        lines = []
        for t in session.turns[-3:]:
            speaker = "Caller" if t.speaker == "caller" else "AI"
            lines.append(f"{speaker}: {t.text}")
        return "\n".join(lines)

    def _determine_next_state(
        self,
        session: CallSession,
        tool_results: list[ToolResult],
    ) -> DialogState:
        """Determine the next dialog state from tool results or FSM rules."""
        # tool_dispatcher route results already include next_state suggestions
        for tr in tool_results:
            if tr.success and isinstance(tr.result, dict) and "next_state" in tr.result:
                try:
                    return DialogState(tr.result["next_state"])
                except ValueError:
                    pass

        # Default: fall back to LISTENING (LLM didn't call any state-changing tools)
        return DialogState.LISTENING
