"""Voice webhook endpoints — Phase 1.

Handles Twilio webhooks for:
- Inbound voice calls: returns TwiML connecting to Media Streams WebSocket
- Call status callbacks: receives call lifecycle events
"""

import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Request, Form
from fastapi.responses import PlainTextResponse

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_websocket_url() -> str:
    """Build the wss:// URL Twilio uses for the Media Streams WebSocket.

    Extracts the host from BASE_URL and prefixes with wss://.
    Example: BASE_URL=https://abc.ngrok.io → wss://abc.ngrok.io/ws/media-stream
    """
    parsed = urlparse(settings.base_url)
    host = parsed.hostname or "localhost"
    port = parsed.port
    if port and port != 443:
        return f"wss://{host}:{port}/ws/media-stream"
    return f"wss://{host}/ws/media-stream"


@router.post("/inbound")
async def handle_inbound_call(
    request: Request,
    CallSid: str = Form(default=""),
    From: str = Form(default=""),
    To: str = Form(default=""),
    CallStatus: str = Form(default=""),
):
    """Twilio webhook for inbound voice calls.

    Returns TwiML that:
    1. Speaks a brief "connecting" message (fallback audio)
    2. Bridges the call into a Media Streams WebSocket for AI processing

    Twilio POST params:
        CallSid   — "CAxxxxx" unique call identifier
        From      — caller's phone number (E.164, e.g. +1234567890)
        To        — dialed number (E.164)
        CallStatus— ringing | in-progress | completed
    """
    ws_url = _build_websocket_url()

    logger.info(
        f"Inbound call | CallSid={CallSid} | From={From} | To={To} | "
        f"Status={CallStatus} | WS={ws_url}"
    )

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        '    <Say voice="Polly.Joanna">Connecting, please wait.</Say>\n'
        "    <Connect>\n"
        f'        <Stream url="{ws_url}">\n'
        f'            <Parameter name="callSid" value="{CallSid}"/>\n'
        f'            <Parameter name="fromNumber" value="{From}"/>\n'
        f'            <Parameter name="toNumber" value="{To}"/>\n'
        "        </Stream>\n"
        "    </Connect>\n"
        "</Response>"
    )

    return PlainTextResponse(content=twiml, media_type="application/xml")


@router.post("/status")
async def handle_call_status(request: Request):
    """Twilio status callback — called when call state changes.

    Triggers post-call processing: logging, transcription, summary.
    """
    form = await request.form()
    call_sid = form.get("CallSid", "")
    status = form.get("CallStatus", "")
    duration = form.get("CallDuration", "0")

    logger.info(
        f"Call status | CallSid={call_sid} | Status={status} | Duration={duration}s"
    )

    if status in ("completed", "no-answer", "busy", "failed"):
        logger.info(f"Call ended — CallSid={call_sid}, outcome={status}")

    return {"status": "ok"}
