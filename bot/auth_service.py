import json
import hashlib
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'licenses' / 'users.json'


def _load():
    if not DB.exists():
        return {"users": []}
    data = json.loads(DB.read_text())
    data.setdefault("users", [])
    return data


def _save(data):
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(email: str, password: str) -> tuple[bool, str]:
    email = (email or '').strip().lower()
    if not email or not password or len(password) < 6:
        return False, 'invalid_input'
    db = _load()
    if any(u.get('email') == email for u in db.get('users', [])):
        return False, 'email_exists'
    db['users'].append({
        'email': email,
        'password_hash': _hash_password(password),
        'created_at': datetime.utcnow().isoformat(),
        'active': True,
    })
    _save(db)
    return True, 'ok'


def verify_user(email: str, password: str) -> bool:
    email = (email or '').strip().lower()
    db = _load()
    target = next((u for u in db.get('users', []) if u.get('email') == email), None)
    if not target or target.get('active') is False:
        return False
    return target.get('password_hash') == _hash_password(password)
