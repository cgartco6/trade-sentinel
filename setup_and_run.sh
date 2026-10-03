#!/usr/bin/env bash
set -e

echo "==================================================================="
echo "         TRADE SENTINEL OS -- BASH SETUP & LAUNCHER               "
echo "==================================================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 1. Package Manager Auto-Detection & Dependencies
if ! command -v python3 &> /dev/null; then
    echo "[!] Python3 missing. Installing..."
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y python3 python3-venv python3-pip git
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3 python3-pip git
    fi
fi

# 2. Virtual Environment Setup
VENV_DIR="$PROJECT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# 3. Install Python Dependencies
echo "[*] Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt uvicorn fastapi jinja2 --quiet

# 4. Environment Bootstrapping
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        cat <<EOT > .env
ALPACA_API_KEY=your_alpaca_paper_api_key
ALPACA_SECRET_KEY=your_alpaca_paper_secret_key
ALPACA_PAPER=true
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
MAX_RISK_PER_TRADE_PCT=0.015
MIN_RR_RATIO=1.5
SCAN_INTERVAL_SECONDS=60
DATABASE_URL=sqlite:///./data/sentinel.db
EOT
    fi
fi

# 5. Initialize DB
python -c "from src.storage.models import init_db; init_db()"

# 6. Launch Web Server & Agent Pipeline
echo "[*] Starting Web UI at http://localhost:8000"
uvicorn src.web.app:app --host 0.0.0.0 --port 8000 &
WEB_PID=$!

trap "kill $WEB_PID" EXIT

sleep 2
python -m src.main
