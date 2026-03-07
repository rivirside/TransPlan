#!/bin/bash
# TransPlan local launcher — double-click to start, "End Session" button to stop
# Single process: FastAPI serves both API and static frontend.

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

VENV="$DIR/backend/.venv"
PREFERRED_PORT=8002
PID_FILE="$DIR/.transplan.pid"

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

# ── cleanup ──────────────────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo "Stopping TransPlan..."
  kill "$SERVER_PID" 2>/dev/null
  wait "$SERVER_PID" 2>/dev/null
  rm -f "$PID_FILE"
  echo "Session ended."
}
trap cleanup EXIT INT TERM

# ── find a free port ─────────────────────────────────────────────────────────
PORT=$(find_free_port $PREFERRED_PORT)
if [ -z "$PORT" ]; then
  echo "ERROR: Cannot find a free port (tried $PREFERRED_PORT-$((PREFERRED_PORT+20)))."
  echo "Close other services or check 'lsof -i tcp:$PREFERRED_PORT'."
  exit 1
fi

if [ "$PORT" -ne "$PREFERRED_PORT" ]; then
  echo "Note: port $PREFERRED_PORT in use, using $PORT instead."
fi

# ── start single server (FastAPI serves API + static files) ──────────────────
echo "Starting TransPlan on :$PORT..."
"$VENV/bin/python" -m uvicorn backend.main:app \
  --host 127.0.0.1 \
  --port "$PORT" \
  --log-level warning \
  &>/tmp/transplan.log &
SERVER_PID=$!

# Verify it started
sleep 1
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "ERROR: Server failed to start. Check /tmp/transplan.log"
  cat /tmp/transplan.log
  exit 1
fi

# Write PID file (for stop.command and /shutdown cleanup)
echo "$SERVER_PID" > "$PID_FILE"

# ── wait for server to be ready ──────────────────────────────────────────────
echo "Waiting for server..."
for i in $(seq 1 20); do
  if curl -s "http://127.0.0.1:$PORT/health" &>/dev/null; then
    break
  fi
  sleep 0.5
done

# ── open browser ─────────────────────────────────────────────────────────────
echo "Opening browser..."
open "http://localhost:$PORT"

echo ""
echo "TransPlan is running at http://localhost:$PORT"
echo "Log: /tmp/transplan.log"
echo ""
echo "Press Ctrl+C or use the 'End Session' button to stop."

# ── keep running until server exits ──────────────────────────────────────────
wait "$SERVER_PID" 2>/dev/null
