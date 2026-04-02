#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

ALERT_SCRIPT="./scripts/send_alert.sh"

a_alert() {
  local msg="$1"
  echo "$msg"
  if [[ -x "$ALERT_SCRIPT" ]]; then
    "$ALERT_SCRIPT" "$msg" || true
  fi
}

if ./scripts/status_bot.sh | grep -q RUNNING; then
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "OK: bot running + health reachable"
    exit 0
  else
    a_alert "⚠️ Watchdog: process running but health unreachable -> restart"
    ./scripts/stop_bot.sh || true
    ./scripts/start_bot.sh
    a_alert "✅ Watchdog: bot restarted"
    exit 0
  fi
else
  a_alert "⚠️ Watchdog: bot not running -> start"
  ./scripts/start_bot.sh
  a_alert "✅ Watchdog: bot started"
fi
