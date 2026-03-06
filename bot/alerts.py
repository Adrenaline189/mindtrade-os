import os
import time
import urllib.parse
import urllib.request


_ALERT_LAST_SENT_AT: dict[str, float] = {}


def send_telegram_alert(text: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False

    base = f"https://api.telegram.org/bot{token}/sendMessage"
    params = urllib.parse.urlencode({"chat_id": chat_id, "text": text})
    url = f"{base}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            return resp.status == 200
    except Exception:
        return False


def send_telegram_alert_throttled(text: str, *, dedupe_key: str, cooldown_sec: float = 600.0) -> bool:
    now = time.time()
    last = float(_ALERT_LAST_SENT_AT.get(dedupe_key, 0.0) or 0.0)
    if now - last < max(1.0, float(cooldown_sec or 0.0)):
        return False
    ok = send_telegram_alert(text)
    if ok:
        _ALERT_LAST_SENT_AT[dedupe_key] = now
    return ok
