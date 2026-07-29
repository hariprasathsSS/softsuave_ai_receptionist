"""Dependency injection container — Phase 1.

Wires together all providers, use cases, and adapters for the
voice conversation pipeline. Uses the FastAPI request-scoped
dependency pattern.

All singletons/services are created once at startup and stored
as module-level variables (simple DI — no framework needed for now).
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)

# ── Module-level singletons (initialised lazily) ────────────────────────────

_stt = None
_tts = None
_llm = None
_telephony = None
_fsm = None
_composer = None
_tool_dispatcher = None
_process_turn = None


# ── Provider factories ─────────────────────────────────────────────────────

def _create_stt():
    """Create or return the singleton Deepgram STT provider."""
    global _stt
    if _stt is None:
        from infrastructure.stt.deepgram_stt import DeepgramStt
        _stt = DeepgramStt(api_key=settings.deepgram_api_key)
        logger.info("STT provider initialised — Deepgram Nova-2")
    return _stt


def _create_tts():
    """Create or return the singleton Deepgram TTS provider."""
    global _tts
    if _tts is None:
        from infrastructure.tts.deepgram_tts import DeepgramTts
        _tts = DeepgramTts(
            api_key=settings.deepgram_api_key,
            voice_model=settings.deepgram_tts_voice,
        )
        logger.info("TTS provider initialised — Deepgram Aura")
    return _tts


def _create_llm():
    """Create or return the singleton LLM provider.

    Switches based on LLM_PROVIDER setting: openai (default) or groq.
    """
    global _llm
    if _llm is None:
        provider = settings.llm_provider
        if provider == "groq":
            from infrastructure.llm.groq_llm import GroqLlm
            _llm = GroqLlm(
                api_key=settings.groq_api_key,
                model=settings.groq_model,
            )
            logger.info(f"LLM provider initialised — Groq ({settings.groq_model})")
        else:
            from infrastructure.llm.openai_llm import OpenAiLlm
            api_key = settings.llm_api_key or settings.openai_api_key
            model = settings.llm_model
            _llm = OpenAiLlm(api_key=api_key, model=model)
            logger.info(f"LLM provider initialised — OpenAI ({model})")
    return _llm


def _create_telephony():
    """Create or return the singleton Twilio telephony provider."""
    global _telephony
    if _telephony is None:
        from infrastructure.telephony.twilio_telephony import TwilioTelephony
        _telephony = TwilioTelephony(
            account_sid=settings.twilio_account_sid,
            auth_token=settings.twilio_auth_token,
            default_from_number=settings.twilio_default_from_number,
        )
        logger.info("Telephony provider initialised — Twilio")
    return _telephony


# ── Application services ───────────────────────────────────────────────────

def _create_fsm():
    global _fsm
    if _fsm is None:
        from application.voice.dialog_state_machine import DialogStateMachine
        _fsm = DialogStateMachine()
    return _fsm


def _create_composer():
    global _composer
    if _composer is None:
        from application.voice.response_composer import ResponseComposer
        _composer = ResponseComposer()
    return _composer


def _create_tool_dispatcher():
    global _tool_dispatcher
    if _tool_dispatcher is None:
        from application.voice.tool_dispatcher import ToolDispatcher
        _tool_dispatcher = ToolDispatcher()
        # Phase 1 tools are pre-registered in tool_dispatcher.__init__
    return _tool_dispatcher


def _create_process_turn():
    global _process_turn
    if _process_turn is None:
        from application.voice.process_conversation_turn import ProcessConversationTurn
        _process_turn = ProcessConversationTurn(
            llm=_create_llm(),
            tool_dispatcher=_create_tool_dispatcher(),
            fsm=_create_fsm(),
            composer=_create_composer(),
            max_tool_turns=settings.max_tool_turns,
        )
        logger.info("ProcessConversationTurn initialised")
    return _process_turn


# ── FastAPI dependency functions ────────────────────────────────────────────

def get_stt():
    """FastAPI dependency: get the STT provider."""
    return _create_stt()


def get_tts():
    """FastAPI dependency: get the TTS provider."""
    return _create_tts()


def get_llm():
    """FastAPI dependency: get the LLM provider."""
    return _create_llm()


def get_telephony():
    """FastAPI dependency: get the telephony provider."""
    return _create_telephony()


def get_fsm():
    """FastAPI dependency: get the dialog state machine."""
    return _create_fsm()


def get_composer():
    """FastAPI dependency: get the response composer."""
    return _create_composer()


def get_process_turn():
    """FastAPI dependency: get the conversation turn processor."""
    return _create_process_turn()


def get_media_stream_endpoint():
    """FastAPI dependency: get the WebSocket endpoint factory.

    Each call gets its own DeepgramStt instance — DeepgramStt keeps
    per-call mutable state (audio buffer, last transcript), so sharing
    the module-level singleton across concurrent calls would corrupt it.
    """
    def stt_factory():
        from infrastructure.stt.deepgram_stt import DeepgramStt
        return DeepgramStt(
            api_key=settings.deepgram_api_key,
            utterance_end_ms=settings.utterance_end_ms,
        )

    from presentation.websockets.call_media_stream import create_media_stream_endpoint
    return create_media_stream_endpoint(
        stt_factory=stt_factory,
        tts=_create_tts(),
        process_turn=_create_process_turn(),
        fsm=_create_fsm(),
        composer=_create_composer(),
        max_turns=settings.max_conversation_turns,
        silence_ms=settings.silence_timeout_ms,
    )
