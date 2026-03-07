#!/bin/bash
# TransPlan local launcher — double-click to start, Ctrl+C or "End Session" to stop

# Resolve the directory this script lives in (works when double-clicked from Finder)
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

VENV="$DIR/backend/.venv"
SESSION_FILE="$DIR/.transplan-session.json"
PREFERRED_BACKEND=8002
PREFERRED_FRONTEND=8080

# ── helpers ──────────────────────────────────────────────────────────────────

is_port_free() {
  ! lsof -i tcp:"$1" &>/dev/null
}

find_free_port() {
  local port=$1
  local max=$((port + 20))
  while [ "$port" -lt "$max" ]; do
    if is_port_free "$port"; then
      echo "$port"
      return 0
    fi
    port=$((port + 1))
  done
  return 1
}

# ── cleanup: kill child processes and remove session file ────────────────────
cleanup() {
  echo ""
  echo "Stopping TransPlan..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  rm -f "$SESSION_FILE"
  echo "Session ended."
}
trap cleanup EXIT INT TERM

# ── find available ports ─────────────────────────────────────────────────────
BACKEND_PORT=$(find_free_port $PREFERRED_BACKEND)
if [ -z "$BACKEND_PORT" ]; then
  echo "ERROR: Cannot find a free port for the backend (tried $PREFERRED_BACKEND-$((PREFERRED_BACKEND+20)))."
  echo "Close other services or check 'lsof -i tcp:$PREFERRED_BACKEND'."
  exit 1
fi

FRONTEND_PORT=$(find_free_port $PREFERRED_FRONTEND)
if [ -z "$FRONTEND_PORT" ]; then
  echo "ERROR: Cannot find a free port for the frontend (tried $PREFERRED_FRONTEND-$((PREFERRED_FRONTEND+20)))."
  exit 1
fi

# Make sure the two ports aren't the same (edge case if ranges overlap)
if [ "$BACKEND_PORT" -eq "$FRONTEND_PORT" ]; then
  FRONTEND_PORT=$(find_free_port $((FRONTEND_PORT + 1)))
fi

if [ "$BACKEND_PORT" -ne "$PREFERRED_BACKEND" ] || [ "$FRONTEND_PORT" -ne "$PREFERRED_FRONTEND" ]; then
  echo "Note: preferred ports in use, using alternatives."
fi

# ── start backend ────────────────────────────────────────────────────────────
echo "Starting backend on :$BACKEND_PORT..."
TRANSPLAN_FRONTEND_PORT=$FRONTEND_PORT "$VENV/bin/python" -m uvicorn backend.main:app \
  --host 127.0.0.1 \
  --port "$BACKEND_PORT" \
  --log-level warning \
  &>/tmp/transplan-backend.log &
BACKEND_PID=$!

# Verify backend process started
sleep 0.5
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo "ERROR: Backend failed to start. Check /tmp/transplan-backend.log"
  cat /tmp/transplan-backend.log
  exit 1
fi

# ── start frontend HTTP server ───────────────────────────────────────────────
echo "Starting frontend on :$FRONTEND_PORT..."
"$VENV/bin/python" -m http.server "$FRONTEND_PORT" \
  --directory "$DIR" \
  &>/tmp/transplan-frontend.log &
FRONTEND_PID=$!

sleep 0.3
if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
  echo "ERROR: Frontend server failed to start. Check /tmp/transplan-frontend.log"
  cat /tmp/transplan-frontend.log
  exit 1
fi

# ── write session file (frontend reads this to find backend) ─────────────────
cat > "$SESSION_FILE" <<ENDJSON
{
  "backendPort": $BACKEND_PORT,
  "frontendPort": $FRONTEND_PORT,
  "backendPid": $BACKEND_PID,
  "frontendPid": $FRONTEND_PID,
  "startedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
ENDJSON

# ── wait for backend to be ready ─────────────────────────────────────────────
echo "Waiting for backend..."
for i in $(seq 1 20); do
  if curl -s "http://127.0.0.1:$BACKEND_PORT/health" &>/dev/null; then
    break
  fi
  sleep 0.5
done

# ── open browser ─────────────────────────────────────────────────────────────
echo "Opening browser..."
open "http://localhost:$FRONTEND_PORT"

echo ""
echo "TransPlan is running."
echo "  Frontend: http://localhost:$FRONTEND_PORT"
echo "  Backend:  http://localhost:$BACKEND_PORT"
echo "  Logs:     /tmp/transplan-backend.log"
echo ""
echo "Press Ctrl+C or use the 'End Session' button in the app to stop."

# ── keep running until backend exits (Ctrl+C, /shutdown, or crash) ───────────
wait "$BACKEND_PID" 2>/dev/null
