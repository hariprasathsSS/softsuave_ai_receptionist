"""FastAPI application entry point — Phase 1 Voice Agent.

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import sys
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

# Support both `from app.xxx import` and `from xxx import` styles
_app_dir = Path(__file__).resolve().parent
if str(_app_dir) not in sys.path:
    sys.path.insert(0, str(_app_dir))

from app.config import settings

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── FastAPI app ──────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Receptionist",
    version="0.1.0",
    description="AI-powered voice receptionist — Phase 1",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────────────

from presentation.api.health import router as health_router
from presentation.api.voice import router as voice_router

app.include_router(health_router, tags=["health"])
app.include_router(voice_router, prefix="/voice", tags=["voice"])

# ── WebSocket ────────────────────────────────────────────────────────────


@app.websocket("/ws/media-stream")
async def media_stream_websocket(websocket: WebSocket):
    """Twilio Media Streams WebSocket — bidirectional audio streaming."""
    from app.dependencies import get_media_stream_endpoint
    endpoint = get_media_stream_endpoint()
    await endpoint(websocket)


# ── Lifecycle ────────────────────────────────────────────────────────────


@app.on_event("startup")
async def on_startup():
    logger.info("AI Receptionist starting up...")
    logger.info(f"STT: Deepgram Nova-2 | TTS: Deepgram Aura | LLM: {settings.llm_provider}")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("AI Receptionist shutting down...")
