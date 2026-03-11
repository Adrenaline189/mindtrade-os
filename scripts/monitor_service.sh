#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_NAME="${SERVICE_NAME:-mindtrade.service}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/health}"
ALERT_SCRIPT="$ROOT/scripts/send_alert.sh"
STATE_FILE="$ROOT/tmp/monitor_state.txt"
mkdir -p "$ROOT/tmp"

alert() {
  local msg="$1"
  echo "$msg"
  if [[ -x "$ALERT_SCRIPT" ]]; then
    "$ALERT_SCRIPT" "$msg" || true
  fi
}

set_state_if_changed() {
  local next="$1"
  local msg="$2"
  local prev=""
  [[ -f "$STATE_FILE" ]] && prev="$(cat "$STATE_FILE" 2>/dev/null || true)"
  if [[ "$prev" != "$next" ]]; then
    echo "$next" > "$STATE_FILE"
    [[ -n "$msg" ]] && alert "$msg"
  fi
}

if command -v systemctl >/dev/null 2>&1; then
  if ! systemctl is-active --quiet "$SERVICE_NAME"; then
    set_state_if_changed "DOWN" "🚨 $SERVICE_NAME is NOT active on $(hostname)"
    exit 2
  fi
fi

HEALTH_JSON="$(curl -fsS "$HEALTH_URL" 2>/dev/null || true)"
if [[ -z "$HEALTH_JSON" ]]; then
  set_state_if_changed "DOWN" "🚨 health endpoint unreachable: $HEALTH_URL"
  exit 3
fi

python3 - "$HEALTH_JSON" <<'PY'
import json, sys
raw=sys.argv[1]
j=json.loads(raw)
ok=bool(j.get("ok"))
workers=j.get("workers") or []
running=any(w.get("running") for w in workers)
if not ok:
    print("HEALTH_NOT_OK")
    raise SystemExit(4)
if not running:
    print("NO_WORKER_RUNNING")
    raise SystemExit(5)
print("HEALTH_OK")
PY
rc=$?
if [[ $rc -ne 0 ]]; then
  reason="service unhealthy rc=$rc"
  [[ $rc -eq 4 ]] && reason="health ok=false"
  [[ $rc -eq 5 ]] && reason="no tenant worker running"
  set_state_if_changed "DOWN" "🚨 MindTrade unhealthy: $reason"
  exit $rc
fi

set_state_if_changed "UP" "✅ MindTrade healthy again"
echo "monitor_ok"
