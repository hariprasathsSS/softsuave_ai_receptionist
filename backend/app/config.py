"""Application configuration via Pydantic Settings.

All environment variables are read here with validation.
Sensitive values must be set in .env (never committed).

Phase 1 config — Supabase (Postgres), Redis, Twilio, Deepgram, OpenAI.
Deepgram handles BOTH STT (Nova-2) and TTS (Aura) — single API key.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ───────────────────────────────────
    app_env: str = "development"
    app_secret_key: str = "change-me"
    base_url: str = "http://localhost:8000"
    debug: bool = False

    # ── Supabase (PostgreSQL) ─────────────────
    database_url: str = "postgresql+asyncpg://postgres.postgres:password@localhost:5432/postgres"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # ── Redis ─────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Twilio ────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_default_from_number: str = ""

    # ── Deepgram (STT + TTS) ──────────────────
    deepgram_api_key: str = ""
    deepgram_stt_model: str = "nova-2"
    deepgram_tts_voice: str = "aura-luna-en"

    # ── LLM ───────────────────────────────────
    llm_provider: str = "openai"          # openai | groq
    llm_api_key: str = ""                  # OpenAI API key
    llm_model: str = "gpt-4o"              # OpenAI model
    openai_api_key: str = ""               # fallback for embeddings
    groq_api_key: str = ""                 # Groq API key (gsk_...)
    groq_model: str = "llama-3.3-70b-versatile"  # Groq model

    # ── Google Calendar ───────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""
    encryption_key: str = ""

    # ── MinIO ─────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio_admin"
    minio_secret_key: str = "changeme"
    minio_bucket: str = "recordings"
    minio_secure: bool = False

    # ── JWT ───────────────────────────────────
    jwt_secret_key: str = "change-me"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    # ── Celery ────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Voice Pipeline (Phase 1) ──────────────
    max_tool_turns: int = 5
    max_conversation_turns: int = 30
    silence_timeout_ms: int = 30_000
    max_call_duration_seconds: int = 600
    # Deepgram's own VAD-based endpointing: how long the caller must stop
    # talking before Deepgram emits UtteranceEnd and we send the turn to
    # the LLM. Distinct from silence_timeout_ms, which aborts the whole
    # call on prolonged dead air (no WS activity at all).
    utterance_end_ms: int = 1000


settings = Settings()
