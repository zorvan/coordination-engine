#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/coordination-engine-backend"
FRONTEND_DIR="$ROOT_DIR/coordination-engine-frontend"

POSTGRES_CONTAINER="ce-local-postgres"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="coordination_engine"
DB_USER="cedbuser"
DB_PASSWORD="cedbpasswd"
BACKEND_PORT="3000"
FRONTEND_PORT="5173"

BACKEND_PID=""
FRONTEND_PID=""
CREATED_CONTAINER="false"

cleanup() {
  echo
  echo "Stopping local processes..."

  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi

  if [[ -n "${BACKEND_PID}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi

  sleep 1

  if [[ "$CREATED_CONTAINER" == "true" ]]; then
    echo "Stopping postgres container $POSTGRES_CONTAINER..."
    docker rm -f "$POSTGRES_CONTAINER" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: required command '$1' is not installed."
    exit 1
  fi
}

require_cmd docker
require_cmd npm
require_cmd curl
require_cmd ss
require_cmd ps

pid_listening_on_port() {
  local port="$1"
  ss -ltnp | awk -v p=":${port}" '$4 ~ p { print }' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | head -n 1
}

stop_stale_project_processes() {
  local stale_backend_pids
  stale_backend_pids="$(pgrep -f "$BACKEND_DIR/node_modules/.bin/ts-node src/index.ts" || true)"
  if [[ -n "$stale_backend_pids" ]]; then
    echo "Stopping stale backend process(es): $stale_backend_pids"
    kill $stale_backend_pids 2>/dev/null || true
  fi

  local stale_frontend_pids
  stale_frontend_pids="$(pgrep -f "$FRONTEND_DIR/node_modules/.bin/vite" || true)"
  if [[ -n "$stale_frontend_pids" ]]; then
    echo "Stopping stale frontend process(es): $stale_frontend_pids"
    kill $stale_frontend_pids 2>/dev/null || true
  fi
}

ensure_port_is_available() {
  local port="$1"
  local label="$2"
  local pid
  pid="$(pid_listening_on_port "$port")"
  if [[ -z "$pid" ]]; then
    return
  fi

  local cmd
  cmd="$(ps -p "$pid" -o args= || true)"
  echo "Error: $label port $port is already in use by PID $pid"
  echo "Command: $cmd"
  echo "Stop that process and retry deploy."
  exit 1
}

ensure_postgres() {
  if docker ps --format '{{.Names}}' | grep -qx "$POSTGRES_CONTAINER"; then
    echo "Using existing running postgres container: $POSTGRES_CONTAINER"
    CREATED_CONTAINER="false"
    return
  fi

  if docker ps -a --format '{{.Names}}' | grep -qx "$POSTGRES_CONTAINER"; then
    echo "Starting existing postgres container: $POSTGRES_CONTAINER"
    docker start "$POSTGRES_CONTAINER" >/dev/null
    CREATED_CONTAINER="false"
  else
    echo "Creating postgres container: $POSTGRES_CONTAINER"
    docker run -d \
      --name "$POSTGRES_CONTAINER" \
      -e POSTGRES_DB="$DB_NAME" \
      -e POSTGRES_USER="$DB_USER" \
      -e POSTGRES_PASSWORD="$DB_PASSWORD" \
      -p "$DB_PORT:5432" \
      postgres:16 >/dev/null
    CREATED_CONTAINER="true"
  fi

  echo "Waiting for postgres to become ready..."
  local attempts=0
  until docker exec "$POSTGRES_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if [[ "$attempts" -ge 30 ]]; then
      echo "Error: postgres did not become ready in time."
      exit 1
    fi
    sleep 1
  done

  echo "Postgres is ready on $DB_HOST:$DB_PORT"
}

install_dependencies() {
  if [[ ! -d "$BACKEND_DIR/node_modules" ]]; then
    echo "Installing backend dependencies..."
    (cd "$BACKEND_DIR" && npm install)
  fi

  if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    echo "Installing frontend dependencies..."
    (cd "$FRONTEND_DIR" && npm install)
  fi
}

start_backend() {
  echo "Starting backend on http://localhost:$BACKEND_PORT"
  (
    cd "$BACKEND_DIR"
    DB_HOST="$DB_HOST" \
    DB_PORT="$DB_PORT" \
    DB_NAME="$DB_NAME" \
    DB_USER="$DB_USER" \
    DB_PASSWORD="$DB_PASSWORD" \
    PORT="$BACKEND_PORT" \
    LOG_LEVEL=debug \
    npm run dev
  ) > "$ROOT_DIR/backend.log" 2>&1 &
  BACKEND_PID=$!
}

start_frontend() {
  echo "Starting frontend on http://localhost:$FRONTEND_PORT"
  (
    cd "$FRONTEND_DIR"
    VITE_API_BASE_URL="http://localhost:$BACKEND_PORT" \
    npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT"
  ) > "$ROOT_DIR/frontend.log" 2>&1 &
  FRONTEND_PID=$!
}

wait_for_backend() {
  echo "Waiting for backend to become ready..."
  local attempts=0
  until curl -fsS "http://localhost:$BACKEND_PORT/matches?actorId=healthcheck" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
      echo "Error: backend process exited before becoming ready."
      echo "Last backend log lines:"
      tail -n 40 "$ROOT_DIR/backend.log" || true
      exit 1
    fi
    if [[ "$attempts" -ge 60 ]]; then
      echo "Error: backend did not become ready in time."
      echo "Last backend log lines:"
      tail -n 40 "$ROOT_DIR/backend.log" || true
      exit 1
    fi
    sleep 1
  done
}

ensure_postgres
install_dependencies
stop_stale_project_processes
ensure_port_is_available "$BACKEND_PORT" "Backend"
ensure_port_is_available "$FRONTEND_PORT" "Frontend"
start_backend
wait_for_backend
start_frontend

echo

echo "Local stack is running:"
echo "- Postgres: $DB_HOST:$DB_PORT (db=$DB_NAME, user=$DB_USER)"
echo "- Backend:  http://localhost:$BACKEND_PORT"
echo "- Frontend: http://localhost:$FRONTEND_PORT"
echo
echo "backend pid = $BACKEND_PID"
echo "frontend pid = $FRONTEND_PID"

read -p "Press any key to stop the local stack..."

if [[ "$CREATED_CONTAINER" == "true" ]]; then
  echo "Postgres container will also be removed on exit."
else
  echo "Existing Postgres container is left running on exit."
fi
