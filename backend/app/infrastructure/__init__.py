"""Infrastructure layer module.

Adapters that implement domain interfaces:
- persistence/ — SQLAlchemy ORM + repository implementations
- telephony/ — Twilio adapter
- stt/ — Deepgram + Whisper adapters
- llm/ — OpenAI + Anthropic adapters
- tts/ — ElevenLabs + Azure adapters
- calendar/ — Google Calendar adapter
- storage/ — MinIO adapter
- cache/ — Redis adapter
- auth/ — JWT + password hashing
"""

