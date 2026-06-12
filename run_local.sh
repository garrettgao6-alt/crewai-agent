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

port_pids() {
  local port="$1"
  lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
}

stop_old_service_on_port() {
  local port="$1"
  local service_pattern="$2"
  local service_name="$3"
  local command_line
  local pid
  local pids

  pids="$(port_pids "${port}")"
  if [[ -z "${pids}" ]]; then
    return
  fi

  while IFS= read -r pid; do
    [[ -z "${pid}" ]] && continue

    command_line="$(ps -p "${pid}" -o command= 2>/dev/null || true)"
    if [[ "${command_line}" =~ ${service_pattern} ]]; then
      echo "Stopping old ${service_name} process on port ${port}: ${pid}"
      kill "${pid}" 2>/dev/null || true
      wait "${pid}" 2>/dev/null || true
    else
      echo "Port ${port} is already in use by another process:"
      echo "  ${pid} ${command_line}"
      exit 1
    fi
  done <<< "${pids}"

  sleep 1

  pids="$(port_pids "${port}")"
  if [[ -n "${pids}" ]]; then
    echo "Port ${port} is still in use after stopping old ${service_name} process."
    exit 1
  fi
}

stop_old_service_on_port 8000 "uvicorn" "uvicorn"
stop_old_service_on_port 8501 "streamlit" "streamlit"

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
echo "FastAPI started"

echo "Starting Streamlit on http://127.0.0.1:8501"
./venv/bin/streamlit run streamlit_app.py \
  --server.address 127.0.0.1 \
  --server.port 8501 &
streamlit_pid=$!
echo "Streamlit started"

echo
echo "Local services are running."
echo "FastAPI:   http://127.0.0.1:8000"
echo "Streamlit: http://127.0.0.1:8501"
echo "Open http://localhost:8501"
echo "Press Ctrl+C to stop both services."

wait -n "${api_pid}" "${streamlit_pid}"
