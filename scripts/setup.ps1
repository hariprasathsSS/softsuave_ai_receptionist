# Windows PowerShell setup script
# Usage: .\scripts\setup.ps1

$ErrorActionPreference = "Stop"
Write-Host "=== AI Receptionist - Project Setup ===" -ForegroundColor Cyan

# Copy .env if not present
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env file created from .env.example - EDIT IT with your API keys!" -ForegroundColor Magenta
}
else {
    Write-Host ".env already exists - skipping." -ForegroundColor Green
}

# Backend
Write-Host "Setting up Python virtual environment..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\..\backend"

if (Test-Path ".venv") {
    Write-Host "Virtual environment already exists - skipping creation." -ForegroundColor Green
}
else {
    python -m venv .venv
    Write-Host "Virtual environment created." -ForegroundColor Green
}

& .\.venv\Scripts\Activate.ps1
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
Write-Host "Backend dependencies installed." -ForegroundColor Green

# Frontend
Write-Host "Setting up frontend..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\..\frontend"

if (-not (Test-Path "node_modules")) {
    npm install
    Write-Host "Frontend dependencies installed." -ForegroundColor Green
}
else {
    Write-Host "node_modules already exists - run 'npm install' manually to update." -ForegroundColor Yellow
}

# Done
Set-Location "$PSScriptRoot\.."
Write-Host ""
Write-Host "=== Setup complete! ===" -ForegroundColor Cyan
Write-Host "Next steps:"
Write-Host "  1. Edit .env with your API keys:"
Write-Host "     - TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN + TWILIO_DEFAULT_FROM_NUMBER"
Write-Host "     - DEEPGRAM_API_KEY (used for both STT + TTS)"
Write-Host "     - LLM_API_KEY (OpenAI)"
Write-Host "  2. Start Redis: docker compose -f docker-compose.yml up -d redis"
Write-Host "  3. Start backend: cd backend && .venv\Scripts\Activate.ps1 && uvicorn app.main:app --reload"
Write-Host "  4. Expose locally: ngrok http 8000"
Write-Host "  5. Configure Twilio webhook to https://<ngrok>.ngrok.io/voice/inbound"
Write-Host "  6. Dial your Twilio number - AI answers!"
