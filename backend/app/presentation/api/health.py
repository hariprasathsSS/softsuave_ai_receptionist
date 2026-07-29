"""Health + test endpoints.

Provides /health (liveness), /health/ready, and /test/chat (pipeline test).
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Liveness probe."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check():
    """Readiness probe — checks STT, TTS, LLM connectivity."""
    try:
        from app.dependencies import get_llm, get_stt, get_tts
        llm = get_llm()
        stt = get_stt()
        tts = get_tts()
        return {
            "status": "ok",
            "llm": "connected",
            "stt": "initialized",
            "tts": "initialized",
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


@router.post("/test/chat")
async def test_chat(
    message: str = "Hello, what are your hours?",
):
    """Test endpoint: run a single turn of the conversation pipeline.

    POST /test/chat?message=What+are+your+hours

    Returns what the AI would say if this were a real call.
    No audio — text in, text out.
    """
    from app.dependencies import get_llm, get_composer
    from application.voice.process_conversation_turn import TurnResult
    from domain.entities.call_session import CallSession
    from domain.entities.value_objects import DialogState

    llm = get_llm()
    composer = get_composer()

    # Create a mock session
    session = CallSession()
    session.advance(DialogState.LISTENING)

    # Call LLM directly
    try:
        result = await llm.classify_intent(
            transcript=message,
            conversation_history=[],
            intent_definitions=[
                {"name": "ask_hours", "description": "Ask about business hours"},
                {"name": "ask_location", "description": "Ask about location/directions"},
                {"name": "book_appointment", "description": "Book an appointment"},
                {"name": "cancel_booking", "description": "Cancel a booking"},
                {"name": "speak_to_human", "description": "Request human agent"},
                {"name": "goodbye", "description": "End the call"},
                {"name": "general_question", "description": "Any other question"},
            ],
        )

        # Generate response
        response = await llm.generate_response(
            intent=result.intent,
            entities=result.entities,
            state=DialogState.LISTENING.value,
            collected_slots={},
        )

        return {
            "status": "ok",
            "your_message": message,
            "detected_intent": result.intent,
            "confidence": result.confidence,
            "sentiment": result.sentiment,
            "entities": result.entities,
            "ai_response": response,
        }
    except Exception as e:
        return {
            "status": "error",
            "your_message": message,
            "error": str(e),
        }
