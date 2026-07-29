"""Call Media Streams WebSocket handler — Phase 1 with barge-in.

Bidirectional audio streaming: Twilio <-> Deepgram STT <-> LLM <-> Deepgram TTS.

Two tasks run concurrently for the lifetime of the call:
  - _twilio_reader: relays inbound Twilio audio straight to Deepgram and
    watches for call-end / prolonged dead air.
  - _deepgram_reader: reacts to Deepgram's own voice-activity events —
    a transcribed "transcript" event triggers barge-in (raw VAD
    "speech_started" alone is too noise-prone), "utterance_end" (real
    silence after speech, detected by Deepgram) triggers the LLM turn.
"""

import asyncio
import json
import logging
import traceback
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from infrastructure.telephony.media_stream_bridge import MediaStreamBridge
from domain.entities.call_session import CallSession
from domain.entities.value_objects import DialogState

logger = logging.getLogger(__name__)


class MediaStreamHandler:

    def __init__(
        self, websocket, stt_factory, tts, process_turn, fsm, composer,
        max_turns=30, silence_ms=30_000,
    ):
        self._ws = websocket
        self._stt = stt_factory()
        self._tts = tts
        self._process_turn = process_turn
        self._fsm = fsm
        self._composer = composer
        self._max_turns = max_turns
        self._silence_ms = silence_ms

        self._bridge: Optional[MediaStreamBridge] = None
        self._session: Optional[CallSession] = None
        self._stream_sid = ""
        self._call_sid = ""
        self._tts_task: Optional[asyncio.Task] = None  # for barge-in cancellation
        self._ai_speaking = False
        self._turn_count = 0
        self._stop_event = asyncio.Event()

    async def handle(self) -> None:
        await self._ws.accept()
        logger.info("WebSocket accepted for media stream")

        try:
            raw = await asyncio.wait_for(self._ws.receive_text(), timeout=15.0)
            msg = json.loads(raw)
            if msg.get("event") != "connected":
                logger.error(f"Expected 'connected', got: {msg.get('event')}")
                return

            raw = await asyncio.wait_for(self._ws.receive_text(), timeout=10.0)
            msg = json.loads(raw)
            if msg.get("event") == "start":
                self._stream_sid = msg.get("streamSid", "")
                custom = msg.get("start", {}).get("customParameters", {})
                self._call_sid = custom.get("callSid", "")
                from_number = custom.get("fromNumber", "")
                logger.info(f"Call {self._call_sid} — stream={self._stream_sid}, from={from_number}")

            self._bridge = MediaStreamBridge(call_sid=self._call_sid, stream_sid=self._stream_sid)
            await self._bridge.start()
            self._session = CallSession(call_sid=self._call_sid)
            await self._stt.start_stream()

            greeting = self._composer.get_greeting()
            self._session.advance(DialogState.GREETING)
            await self._play_audio(greeting)
            self._session.advance(DialogState.LISTENING)

            await self._run_readers()

        except WebSocketDisconnect:
            logger.info(f"WS disconnect — call={self._call_sid}")
        except Exception:
            logger.error(f"FATAL — call={self._call_sid}\n{traceback.format_exc()}")
        finally:
            if self._tts_task and not self._tts_task.done():
                self._tts_task.cancel()
            await self._cleanup()

    # ── Reader tasks ─────────────────────────────────────────────────────

    async def _run_readers(self) -> None:
        """Run the Twilio and Deepgram readers concurrently until either ends."""
        twilio_task = asyncio.create_task(self._twilio_reader())
        deepgram_task = asyncio.create_task(self._deepgram_reader())

        done, pending = await asyncio.wait(
            {twilio_task, deepgram_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            exc = task.exception()
            if exc:
                raise exc

    async def _twilio_reader(self) -> None:
        """Relay inbound Twilio audio to Deepgram; watch for call end / dead air."""
        while not self._stop_event.is_set():
            if self._fsm.is_terminal(self._session.state) or self._turn_count >= self._max_turns:
                break

            try:
                raw = await asyncio.wait_for(
                    self._ws.receive_text(),
                    timeout=self._silence_ms / 1000.0,
                )
            except asyncio.TimeoutError:
                logger.info(f"[{self._call_sid}] No activity for {self._silence_ms}ms — ending call")
                break

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event = msg.get("event", "")

            if event == "media":
                audio_data = await self._bridge.receive_from_twilio(msg)
                if audio_data:
                    await self._stt.send_audio(audio_data)

            elif event == "stop":
                break

            # mark/clear/connected/start: nothing to do

        self._stop_event.set()

    async def _deepgram_reader(self) -> None:
        """React to Deepgram's own speech/silence signals."""
        async for evt in self._stt.events():
            if self._stop_event.is_set():
                break

            if evt["event"] == "transcript":
                # ═══ BARGE-IN: caller is actually saying something while
                # the AI is playing. Gated on transcribed text, not the raw
                # "speech_started" VAD blip — that fires on background
                # noise/breath with no real speech and was cutting the AI
                # off almost as soon as it started talking.
                text = evt["text"]
                if len(text) >= 3 and self._ai_speaking:
                    logger.info(f"[{self._call_sid}] Barge-in — caller interrupted AI: '{text}'")
                    await self._stop_ai_audio()

            elif evt["event"] == "utterance_end":
                full_text = evt["transcript"].strip()
                if full_text:
                    await self._flush(full_text)
                    self._turn_count += 1
                    if self._fsm.is_terminal(self._session.state) or self._turn_count >= self._max_turns:
                        break

        self._stop_event.set()

    # ── Process + respond ───────────────────────────────────────────────

    async def _flush(self, full_text: str) -> None:
        """Process one caller utterance (Deepgram already decided it's complete) and respond."""
        # Skip noise: single words, numbers-only, very short
        if len(full_text.split()) <= 1 and len(full_text) < 6:
            logger.debug(f"[{self._call_sid}] Skipping short: {full_text}")
            return

        logger.info(f"[{self._call_sid}] Caller: {full_text}")

        # Safety net: stop any leftover audio from the previous turn before
        # starting this one (normally already handled by barge-in above).
        if self._ai_speaking:
            await self._stop_ai_audio()

        result = await self._process_turn.execute(transcript=full_text, session=self._session)

        if result.is_terminal:
            await self._play_audio(result.response_text)
        else:
            # Fire-and-forget — caller can barge in
            self._tts_task = asyncio.create_task(self._play_audio(result.response_text))

    # ── Audio playback ──────────────────────────────────────────────────

    async def _stop_ai_audio(self) -> None:
        """Stop the AI's speech immediately, on this call and on Twilio's end.

        Cancelling our own send task is not enough: Twilio buffers outbound
        audio and plays it out at real time, while our send loop typically
        finishes shipping the whole response in well under a second. The
        'clear' event is what actually tells Twilio to drop that buffered
        audio so the caller stops hearing it.
        """
        self._ai_speaking = False
        if self._tts_task and not self._tts_task.done():
            self._tts_task.cancel()
        self._tts_task = None
        await self._safe_send(await self._bridge.clear())

    async def _play_audio(self, text: str) -> None:
        """Stream TTS audio to Twilio. Cancellable by barge-in."""
        if not text:
            return
        self._ai_speaking = True
        try:
            logger.info(f"[{self._call_sid}] AI: {text}")
            async for audio_chunk in self._tts.synthesize_stream(text):
                msg = await self._bridge.send_to_twilio(audio_chunk)
                await self._safe_send(msg)
                # Yield control — allows barge-in detection between chunks
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            logger.debug(f"[{self._call_sid}] TTS playback cancelled (barge-in)")
            raise
        except Exception:
            logger.exception("TTS send failed")
        finally:
            self._ai_speaking = False

    async def _safe_send(self, msg: dict) -> bool:
        try:
            await self._ws.send_json(msg)
            return True
        except RuntimeError as e:
            if "after sending 'websocket.close'" in str(e):
                return False
            raise

    async def _cleanup(self) -> None:
        logger.info(f"Cleanup — call={self._call_sid}")
        for obj, method in [(self._bridge, 'stop'), (self._session, 'end')]:
            try:
                if obj:
                    await getattr(obj, method)()
            except Exception:
                pass
        try:
            await self._stt.end_stream()
        except Exception:
            pass


def create_media_stream_endpoint(stt_factory, tts, process_turn, fsm, composer, max_turns=30, silence_ms=30_000):
    async def endpoint(websocket: WebSocket):
        handler = MediaStreamHandler(
            websocket=websocket, stt_factory=stt_factory, tts=tts,
            process_turn=process_turn, fsm=fsm, composer=composer,
            max_turns=max_turns, silence_ms=silence_ms,
        )
        await handler.handle()
    return endpoint
