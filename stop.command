#!/bin/bash
# TransPlan session stopper — double-click to end a running session

DIR="$(cd "$(dirname "$0")" && pwd)"
SESSION_FILE="$DIR/.transplan-session.json"

if [ ! -f "$SESSION_FILE" ]; then
  echo "No active TransPlan session found."
  echo "(Looking for $SESSION_FILE)"
  exit 0
fi

# Parse PIDs from session file (pure bash, no jq dependency)
BACKEND_PID=$(grep -o '"backendPid": [0-9]*' "$SESSION_FILE" | grep -o '[0-9]*')
FRONTEND_PID=$(grep -o '"frontendPid": [0-9]*' "$SESSION_FILE" | grep -o '[0-9]*')

KILLED=0

if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo "Stopping backend (PID $BACKEND_PID)..."
  kill "$BACKEND_PID" 2>/dev/null
  KILLED=1
fi

if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
  echo "Stopping frontend (PID $FRONTEND_PID)..."
  kill "$FRONTEND_PID" 2>/dev/null
  KILLED=1
fi

rm -f "$SESSION_FILE"

if [ "$KILLED" -eq 1 ]; then
  echo "TransPlan session ended."
else
  echo "Processes already stopped. Cleaned up session file."
fi
