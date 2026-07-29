#!/usr/bin/env bash
# Usage: ./scripts/setup.sh

set -e

echo "=== AI Receptionist — Project Setup ==="

# Backend
echo "Setting up Python virtual environment..."
cd "$(dirname "$0")/../backend"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Backend dependencies installed."

# Copy .env if not present
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ".env file created from .env.example — EDIT IT with your API keys!"
fi

# Frontend
echo "Setting up frontend..."
cd frontend
npm install
echo "Frontend dependencies installed."

echo "=== Setup complete! ==="
echo "Next steps:"
echo "  1. Edit .env with your API keys (Twilio, Deepgram, OpenAI, ElevenLabs)"
echo "  2. Start Docker services: docker compose -f docker/docker-compose.yml up -d postgres redis minio"
echo "  3. Start backend: cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "  4. Start frontend: cd frontend && npm run dev"
