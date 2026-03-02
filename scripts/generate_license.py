#!/usr/bin/env python3
import argparse
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'licenses' / 'licenses.json'


def load_db():
    if DB.exists():
        return json.loads(DB.read_text())
    return {"licenses": []}


def save_db(data):
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def sign(token, email):
    raw = f"{token}:{email}:openclaw-bot"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--email', required=True)
    p.add_argument('--plan', default='starter', choices=['starter','pro'])
    p.add_argument('--days', type=int, default=30)
    p.add_argument('--max-devices', type=int, default=1)
    args = p.parse_args()

    token = secrets.token_urlsafe(24)
    key = sign(token, args.email)
    now = datetime.utcnow()
    exp = now + timedelta(days=args.days)

    rec = {
        'email': args.email,
        'plan': args.plan,
        'license_token': token,
        'license_key': key,
        'issued_at': now.isoformat(),
        'expires_at': exp.isoformat(),
        'max_devices': args.max_devices,
        'devices': []
    }

    db = load_db()
    db['licenses'].append(rec)
    save_db(db)

    print('LICENSE_TOKEN=', token)
    print('LICENSE_KEY=', key)
    print('EXPIRES_AT=', exp.isoformat())


if __name__ == '__main__':
    main()
