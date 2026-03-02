#!/usr/bin/env bash
set -euo pipefail
DURATION_MIN=${1:-120}
OUT="logs/health-window-$(date +%F-%H%M%S).log"
END=$(( $(date +%s) + DURATION_MIN*60 ))

echo "start=$(date -Iseconds) duration_min=$DURATION_MIN" | tee -a "$OUT"
while [ "$(date +%s)" -lt "$END" ]; do
  TS=$(date -Iseconds)
  STATUS=$(./scripts/status_bot.sh 2>/dev/null | tr '\n' ' ')
  HEALTH=$(./venv/bin/python - <<'PY'
import requests
try:
 r=requests.get('http://127.0.0.1:8000/health',timeout=3)
 print(r.status_code, r.text)
except Exception as e:
 print('ERR',e)
PY
)
  ERRS=$(tail -n 400 logs/bot.out 2>/dev/null | grep -E "error:|⚠️" | tail -n 3 | tr '\n' ' ')
  echo "[$TS] $STATUS | $HEALTH | recent_errs=$ERRS" | tee -a "$OUT"
  sleep 300
done
echo "end=$(date -Iseconds)" | tee -a "$OUT"
