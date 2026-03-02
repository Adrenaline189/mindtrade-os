import os
import urllib.parse
import urllib.request


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
