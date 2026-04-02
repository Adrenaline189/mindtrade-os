#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
MSG="${1:-Trading bot alert}"
export MSG

if [[ -f .env ]]; then
  set -a
  source ./.env
  set +a
fi

if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
  python3 - <<'PY'
import os, urllib.parse, urllib.request
msg=os.environ.get('MSG','Trading bot alert')
token=os.environ.get('TELEGRAM_BOT_TOKEN','')
chat=os.environ.get('TELEGRAM_CHAT_ID','')
url=f"https://api.telegram.org/bot{token}/sendMessage?"+urllib.parse.urlencode({"chat_id":chat,"text":msg})
try:
    urllib.request.urlopen(url, timeout=8).read()
except Exception:
    pass
PY
fi
