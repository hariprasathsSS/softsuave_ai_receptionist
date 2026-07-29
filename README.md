# AI Universal Receptionist

A multi-tenant AI voice agent platform that serves as a fully functional receptionist for any business vertical (hospital, hotel, school, real estate, etc.) — configured, not coded.

## Architecture

This project follows **Clean Architecture**:

```
Domain (entities + interfaces) → Application (use cases) → Infrastructure (adapters) → Presentation (API/WS)
```

- **`backend/app/domain/`** — Pure Python entities and abstract contracts. Zero external dependencies.
- **`backend/app/application/`** — Use cases that orchestrate domain objects. Depends only on domain.
- **`backend/app/infrastructure/`** — Adapters: PostgreSQL, Redis, Twilio, Deepgram, OpenAI, ElevenLabs, Google Calendar, MinIO.
- **`backend/app/presentation/`** — FastAPI REST routes and WebSocket handlers.

Full technical plan: [`docs/Technical_Implementation_Plan.md`](docs/Technical_Implementation_Plan.md)

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Node.js 20+ (for frontend)

### Setup

```bash
# Clone and enter the project
cd ai-receptionist

# Copy environment config
cp .env.example .env
# Edit .env with your API keys

# Start infrastructure
docker compose -f docker/docker-compose.yml up -d postgres redis minio

# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Phase 1 (Core Voice Agent)

1. Set `TWILIO_*`, `DEEPGRAM_API_KEY`, `LLM_API_KEY`, `ELEVENLABS_API_KEY` in `.env`
2. Start all services: `docker compose -f docker/docker-compose.yml up -d`
3. Expose your local server (ngrok or similar): `ngrok http 8000`
4. Configure your Twilio number's voice webhook to `https://<ngrok>.ngrok.io/voice/inbound`
5. Dial the number — the AI answers

## Project Structure

See [`docs/architecture.md`](docs/architecture.md) for layer details.

## License

Proprietary — POC phase.
