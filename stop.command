#!/bin/bash
# TransPlan session stopper — double-click to end a running session

DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$DIR/.transplan.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "No active TransPlan session found."
  exit 0
fi

PID=$(cat "$PID_FILE")

if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  echo "Stopping TransPlan (PID $PID)..."
  kill "$PID" 2>/dev/null
  echo "Session ended."
else
  echo "Process already stopped."
fi

rm -f "$PID_FILE"
