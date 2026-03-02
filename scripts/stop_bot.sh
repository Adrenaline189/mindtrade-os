#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -f .bot.pid ]]; then
  PID="$(cat .bot.pid)"
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "Stopped bot PID $PID"
  else
    echo "PID not running"
  fi
  rm -f .bot.pid
else
  echo "No .bot.pid found"
fi
