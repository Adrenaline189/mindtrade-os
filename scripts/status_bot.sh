#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -f .bot.pid ]] && kill -0 "$(cat .bot.pid)" 2>/dev/null; then
  echo "RUNNING PID $(cat .bot.pid)"
else
  echo "STOPPED"
fi
