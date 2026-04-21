#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION_NAME="${BURN_RATE_TMUX_SESSION:-burn-rate-dev}"
BACKEND_PORT="${BURN_RATE_BACKEND_PORT:-8001}"
FRONTEND_PORT="${BURN_RATE_FRONTEND_PORT:-5173}"
STOP_DB="${BURN_RATE_STOP_DB:-false}"

usage() {
  cat <<USAGE
Usage: scripts/dev-services.sh start|restart|stop|status

Starts Burn Rate dev services in tmux:
  db       docker compose db service
  backend  Django on http://localhost:${BACKEND_PORT}
  frontend Vite on http://localhost:${FRONTEND_PORT}

Optional env:
  BURN_RATE_TMUX_SESSION=${SESSION_NAME}
  BURN_RATE_BACKEND_PORT=${BACKEND_PORT}
  BURN_RATE_FRONTEND_PORT=${FRONTEND_PORT}
  BURN_RATE_STOP_DB=true   also stops docker compose db on stop/restart
USAGE
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

load_env_snippet='if [ -f .env ]; then set -a; . ./.env; set +a; fi'

tmux_has_session() {
  tmux has-session -t "$SESSION_NAME" 2>/dev/null
}

stop_repo_listener_on_port() {
  local port="$1"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -z "$pids" ]; then
    return 0
  fi

  while IFS= read -r pid; do
    [ -n "$pid" ] || continue
    local command_line
    command_line="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    if [[ "$command_line" == *"$ROOT_DIR"* || "$command_line" == *"manage.py runserver"* || "$command_line" == *"vite"* ]]; then
      echo "Stopping repo dev listener on port ${port}: pid ${pid}"
      kill "$pid" 2>/dev/null || true
    else
      echo "Port ${port} is in use by an unrelated process: ${pid} ${command_line}" >&2
      exit 1
    fi
  done <<< "$pids"
}

ensure_port_available() {
  local port="$1"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "Port ${port} is already in use. Run: scripts/dev-services.sh restart" >&2
    exit 1
  fi
}

run_in_tmux() {
  local window_name="$1"
  local command="$2"
  if tmux_has_session; then
    tmux new-window -t "$SESSION_NAME" -n "$window_name" -c "$ROOT_DIR" "bash -lc $(printf '%q' "$command")"
  else
    tmux new-session -d -s "$SESSION_NAME" -n "$window_name" -c "$ROOT_DIR" "bash -lc $(printf '%q' "$command")"
  fi
}

start_services() {
  require_command tmux
  require_command docker
  require_command uv
  require_command pnpm

  if tmux_has_session; then
    echo "Session ${SESSION_NAME} already exists."
    status_services
    return 0
  fi

  ensure_port_available "$BACKEND_PORT"
  ensure_port_available "$FRONTEND_PORT"

  local db_cmd="${load_env_snippet}; docker compose up -d db; until docker compose exec -T db pg_isready -U \"\${DB_USER:-burn_rate}\" -d \"\${DB_NAME:-burn_rate}\"; do sleep 1; done; docker compose logs -f db"
  local backend_cmd="${load_env_snippet}; docker compose up -d db; until docker compose exec -T db pg_isready -U \"\${DB_USER:-burn_rate}\" -d \"\${DB_NAME:-burn_rate}\"; do sleep 1; done; cd backend; uv sync; uv run python manage.py migrate; uv run python manage.py runserver 0.0.0.0:${BACKEND_PORT}"
  local frontend_cmd="cd frontend; pnpm install; pnpm exec vite --host 0.0.0.0 --port ${FRONTEND_PORT}"

  run_in_tmux db "$db_cmd"
  run_in_tmux backend "$backend_cmd"
  run_in_tmux frontend "$frontend_cmd"

  echo "Started ${SESSION_NAME}."
  echo "Frontend: http://localhost:${FRONTEND_PORT}"
  echo "Backend:  http://localhost:${BACKEND_PORT}"
  echo "Attach:   tmux attach -t ${SESSION_NAME}"
}

stop_services() {
  require_command tmux
  if tmux_has_session; then
    tmux kill-session -t "$SESSION_NAME"
    echo "Stopped tmux session ${SESSION_NAME}."
  fi

  stop_repo_listener_on_port "$FRONTEND_PORT"
  stop_repo_listener_on_port "$BACKEND_PORT"

  if [ "$STOP_DB" = "true" ]; then
    (cd "$ROOT_DIR" && docker compose stop db)
  fi
}

status_services() {
  if command -v tmux >/dev/null 2>&1 && tmux_has_session; then
    tmux list-windows -t "$SESSION_NAME"
  else
    echo "No tmux session named ${SESSION_NAME}."
  fi
  echo
  lsof -nP -iTCP:"$FRONTEND_PORT" -sTCP:LISTEN 2>/dev/null || true
  lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN 2>/dev/null || true
  echo
  echo "Frontend: http://localhost:${FRONTEND_PORT}"
  echo "Backend:  http://localhost:${BACKEND_PORT}"
}

case "${1:-}" in
  start)
    start_services
    ;;
  restart)
    stop_services
    start_services
    ;;
  stop)
    stop_services
    ;;
  status)
    status_services
    ;;
  *)
    usage
    exit 1
    ;;
esac
