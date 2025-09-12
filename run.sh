#!/usr/bin/env bash
set -euo pipefail

# 1) Python venv + deps
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt

# 2) Ensure data dirs
mkdir -p project_docs .chroma

# 3) Quick OCR check
if command -v tesseract >/dev/null 2>&1; then
  echo "[OK] Tesseract found"
else
  echo "[INFO] Tesseract not found (OCR will be disabled)."
fi

# 4) Launch API + UI
# API on :8000 (background)
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload > .api.log 2>&1 &
API_PID=$!

# Wait a moment for API to boot
sleep 2

# UI on :8501 (foreground)
streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0
kill $API_PID || true
