#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f ".env" ]]; then
  echo "Missing .env. Copy .env.example to .env and configure it before starting."
  exit 1
fi

if [[ ! -d "venv" ]]; then
  echo "Missing venv. Create it with: python3 -m venv venv"
  exit 1
fi

if [[ ! -x "venv/bin/uvicorn" ]]; then
  echo "Missing venv/bin/uvicorn. Install dependencies with: ./venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

if [[ ! -x "venv/bin/streamlit" ]]; then
  echo "Missing venv/bin/streamlit. Install dependencies with: ./venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

api_pid=""
streamlit_pid=""

cleanup() {
  echo
  echo "Stopping local services..."

  if [[ -n "${api_pid}" ]] && kill -0 "${api_pid}" 2>/dev/null; then
    kill "${api_pid}" 2>/dev/null || true
  fi

  if [[ -n "${streamlit_pid}" ]] && kill -0 "${streamlit_pid}" 2>/dev/null; then
    kill "${streamlit_pid}" 2>/dev/null || true
  fi

  wait "${api_pid}" 2>/dev/null || true
  wait "${streamlit_pid}" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

echo "Starting FastAPI on http://127.0.0.1:8000"
./venv/bin/uvicorn api:app --host 127.0.0.1 --port 8000 &
api_pid=$!

echo "Starting Streamlit on http://127.0.0.1:8501"
./venv/bin/streamlit run streamlit_app.py \
  --server.address 127.0.0.1 \
  --server.port 8501 &
streamlit_pid=$!

echo
echo "Local services are running."
echo "FastAPI:   http://127.0.0.1:8000"
echo "Streamlit: http://127.0.0.1:8501"
echo "Press Ctrl+C to stop both services."

wait -n "${api_pid}" "${streamlit_pid}"
