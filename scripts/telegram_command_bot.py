#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path

import requests

ROOT = Path('/Users/adrenaline/trading-bot')
ENV = ROOT / '.env'
OFFSET_FILE = ROOT / 'data' / 'telegram_offset.txt'
LOG_FILE = ROOT / 'logs' / 'telegram-cmd.log'


def log(msg: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open('a', encoding='utf-8') as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")


def load_env():
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if not line or line.strip().startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def tg_api(token, method, params=None):
    params = params or {}
    url = f'https://api.telegram.org/bot{token}/{method}'
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def http_get_json(url):
    return requests.get(url, timeout=8).json()


def send(token, chat_id, text, reply_to=None):
    p = {'chat_id': chat_id, 'text': text}
    if reply_to:
        p['reply_to_message_id'] = reply_to
    tg_api(token, 'sendMessage', p)


def get_offset():
    if OFFSET_FILE.exists():
        try:
            return int(OFFSET_FILE.read_text().strip())
        except Exception:
            return 0
    return 0


def set_offset(v):
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(str(v))


def cmd_response(text):
    t = (text or '').strip().lower()
    if t in ['/help', 'help']:
        return (
            'MindTrade OS Commands\n'
            '/status - bot status\n'
            '/health - raw health json\n'
            '/performance - R metrics\n'
            '/symbols - active symbols\n'
            '/last - latest 5 events\n'
            '/startbot - start engine\n'
            '/stopbot - stop engine'
        )
    if t == '/status':
        h = http_get_json('http://127.0.0.1:8000/health')
        return f"running={h.get('running')} mode={h.get('mode')} live={h.get('allow_live')} symbols={','.join(h.get('symbols',[]))}"
    if t == '/health':
        return json.dumps(http_get_json('http://127.0.0.1:8000/health'), ensure_ascii=False)
    if t == '/performance':
        p = http_get_json('http://127.0.0.1:8000/api/performance')
        return f"realized={p.get('realized_trades')} totalR={p.get('total_r')} avgR={p.get('avg_r')} maxDD={p.get('max_dd_r')}"
    if t == '/symbols':
        h = http_get_json('http://127.0.0.1:8000/health')
        return 'symbols: ' + ', '.join(h.get('symbols', []))
    if t == '/last':
        ev = http_get_json('http://127.0.0.1:8000/api/events?limit=5').get('events', [])
        lines = []
        for e in ev[-5:]:
            lines.append(f"{e.get('time')} {e.get('symbol','-')} {e.get('result')} {e.get('note','')}")
        return '\n'.join(lines) if lines else 'no events'
    if t == '/startbot':
        requests.post('http://127.0.0.1:8000/start', timeout=8)
        return 'start requested ✅'
    if t == '/stopbot':
        requests.post('http://127.0.0.1:8000/stop', timeout=8)
        return 'stop requested ✅'
    return ''


def main():
    load_env()
    token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    target_chat = os.getenv('TELEGRAM_CHAT_ID', '').strip()
    if not token or not target_chat:
        raise SystemExit('Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID')

    offset = get_offset()
    log(f"command-bot start target_chat={target_chat} offset={offset}")
    while True:
        try:
            data = tg_api(token, 'getUpdates', {'offset': offset + 1, 'timeout': 20})
            for upd in data.get('result', []):
                offset = max(offset, upd.get('update_id', offset))
                msg = upd.get('message') or upd.get('channel_post')
                if not isinstance(msg, dict):
                    continue
                chat_id = str(msg.get('chat', {}).get('id', ''))
                text = msg.get('text', '')
                if chat_id != target_chat:
                    continue
                resp = cmd_response(text)
                if resp:
                    send(token, chat_id, resp, msg.get('message_id'))
                    log(f"replied cmd={text} chat={chat_id}")
            set_offset(offset)
        except Exception as e:
            log(f"loop_error: {e}")
            time.sleep(2)
        time.sleep(0.4)


if __name__ == '__main__':
    main()
