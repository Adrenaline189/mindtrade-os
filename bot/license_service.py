import json
import secrets
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'licenses' / 'licenses.json'


def _load():
    if not DB.exists():
        return {"licenses": [], "payments": []}
    data = json.loads(DB.read_text())
    data.setdefault("licenses", [])
    data.setdefault("payments", [])
    return data


def _save(data):
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _sign(token, email):
    return hashlib.sha256(f"{token}:{email}:openclaw-bot".encode()).hexdigest()[:24]


def issue_license(email: str, plan: str = "starter", days: int = 30, max_devices: int = 1):
    token = secrets.token_urlsafe(24)
    now = datetime.utcnow()
    rec = {
        "email": email,
        "plan": plan,
        "license_token": token,
        "license_key": _sign(token, email),
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(days=days)).isoformat(),
        "max_devices": max_devices,
        "devices": [],
        "active": True,
    }
    db = _load()
    db["licenses"].append(rec)
    _save(db)
    return rec


def list_licenses(limit: int = 200):
    db = _load()
    return list(reversed(db.get("licenses", [])))[:limit]


def record_payment(event: dict):
    db = _load()
    db.setdefault("payments", []).append(event)
    _save(db)


def has_payment_event(event_id: str) -> bool:
    db = _load()
    return any(p.get("event_id") == event_id for p in db.get("payments", []))


def set_license_active(token: str, active: bool) -> bool:
    db = _load()
    changed = False
    for rec in db.get('licenses', []):
        if rec.get('license_token') == token:
            rec['active'] = bool(active)
            changed = True
            break
    if changed:
        _save(db)
    return changed


def delete_license(token: str) -> bool:
    db = _load()
    before = len(db.get('licenses', []))
    db['licenses'] = [r for r in db.get('licenses', []) if r.get('license_token') != token]
    changed = len(db['licenses']) != before
    if changed:
        _save(db)
    return changed


def renew_license(token: str, days: int = 30) -> bool:
    from datetime import datetime, timedelta
    db = _load()
    changed = False
    for rec in db.get('licenses', []):
        if rec.get('license_token') == token:
            now = datetime.utcnow()
            exp_raw = rec.get('expires_at')
            try:
                exp = datetime.fromisoformat(exp_raw) if exp_raw else now
            except Exception:
                exp = now
            base = exp if exp > now else now
            rec['expires_at'] = (base + timedelta(days=days)).isoformat()
            rec['active'] = True
            changed = True
            break
    if changed:
        _save(db)
    return changed


def find_licenses(query: str, limit: int = 200):
    q = (query or '').lower().strip()
    rows = list_licenses(limit=2000)
    if not q:
        return rows[:limit]
    out = []
    for r in rows:
        blob = f"{r.get('email','')} {r.get('plan','')} {r.get('license_token','')}"
        if q in blob.lower():
            out.append(r)
    return out[:limit]


def list_payments_for_license(token: str, limit: int = 20):
    db = _load()
    # resolve email from token
    email = None
    for r in db.get('licenses', []):
        if r.get('license_token') == token:
            email = (r.get('email') or '').strip().lower()
            break
    if not email:
        return []

    out = []
    for p in reversed(db.get('payments', [])):
        p_email = str(p.get('email') or '').strip().lower()
        if p_email == email:
            out.append(p)
        if len(out) >= limit:
            break
    return out


def get_license_by_email(email: str):
    target = (email or '').strip().lower()
    if not target:
        return None
    db = _load()
    for rec in reversed(db.get('licenses', [])):
        if (rec.get('email') or '').strip().lower() == target:
            return rec
    return None


def license_state_for_email(email: str) -> tuple[bool, str, dict | None]:
    rec = get_license_by_email(email)
    if not rec:
        return False, 'license_not_found', None
    if rec.get('active') is False:
        return False, 'suspended', rec

    exp_raw = rec.get('expires_at')
    if exp_raw:
        try:
            if datetime.utcnow() > datetime.fromisoformat(exp_raw):
                return False, 'expired', rec
        except Exception:
            return False, 'invalid_expiry', rec

    return True, 'valid', rec
