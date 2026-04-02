#!/usr/bin/env python3
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / '.env'
if ENV.exists():
    for line in ENV.read_text().splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k,v=line.split('=',1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

sys.path.insert(0, str(ROOT))
from bot.alerts import send_telegram_alert  # noqa

msg = os.getenv('TEST_ALERT_MESSAGE', '✅ Trading bot test alert from น้องมายด์')
ok = send_telegram_alert(msg)
print('ALERT_SENT' if ok else 'ALERT_FAILED (check TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID)')
