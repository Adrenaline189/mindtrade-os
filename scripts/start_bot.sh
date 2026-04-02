#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs
if [[ -f .bot.pid ]] && kill -0 "$(cat .bot.pid)" 2>/dev/null; then
  echo "Bot already running: PID $(cat .bot.pid)"
  exit 0
fi
nohup ./venv/bin/python main.py > logs/bot.out 2>&1 &
echo $! > .bot.pid
echo "Started bot: PID $(cat .bot.pid)"
