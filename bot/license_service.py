import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'licenses' / 'licenses.json'

PLAN_CONFIG = {
    'starter': {'days': 30, 'max_devices': 1},
    'pro': {'days': 30, 'max_devices': 2},
    'pro_trial': {'days': 7, 'max_devices': 2},
}


def _utcnow() -> datetime:
    # keep naive datetime for backward-compatible stored format
    return datetime.now()


def _load():
    if not DB.exists():
        return {
            'licenses': [],
            'payments': [],
            'payment_orders': [],
            'processed_events': [],
            'order_actions': [],
        }
    data = json.loads(DB.read_text())
    data.setdefault('licenses', [])
    data.setdefault('payments', [])
    data.setdefault('payment_orders', [])
    data.setdefault('processed_events', [])
    data.setdefault('order_actions', [])
    return data


def _save(data):
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _sign(token, email):
    return hashlib.sha256(f"{token}:{email}:openclaw-bot".encode()).hexdigest()[:24]


def plan_defaults(plan: str) -> dict:
    key = (plan or 'starter').strip().lower()
    return PLAN_CONFIG.get(key, PLAN_CONFIG['starter'])


def issue_license(email: str, plan: str = 'starter', days: int = 30, max_devices: int = 1):
    token = secrets.token_urlsafe(24)
    now = _utcnow()
    rec = {
        'email': email,
        'plan': plan,
        'license_token': token,
        'license_key': _sign(token, email),
        'issued_at': now.isoformat(),
        'expires_at': (now + timedelta(days=days)).isoformat(),
        'max_devices': max_devices,
        'devices': [],
        'active': True,
    }
    db = _load()
    db['licenses'].append(rec)
    _save(db)
    return rec


def list_licenses(limit: int = 200):
    db = _load()
    return list(reversed(db.get('licenses', [])))[:limit]


def record_payment(event: dict):
    db = _load()
    db.setdefault('payments', []).append(event)
    _save(db)


def has_payment_event(event_id: str) -> bool:
    db = _load()
    return any(p.get('event_id') == event_id for p in db.get('payments', []))


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
    db = _load()
    changed = False
    for rec in db.get('licenses', []):
        if rec.get('license_token') == token:
            now = _utcnow()
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
            if _utcnow() > datetime.fromisoformat(exp_raw):
                return False, 'expired', rec
        except Exception:
            return False, 'invalid_expiry', rec

    return True, 'valid', rec


def _new_order_id() -> str:
    return f"ord_{_utcnow().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"


def create_payment_order(email: str, plan: str, amount: float, channel: str, currency: str = 'USDT') -> dict:
    now = _utcnow().isoformat()
    order = {
        'order_id': _new_order_id(),
        'email': (email or '').strip().lower(),
        'plan': (plan or 'starter').strip().lower(),
        'amount': float(amount),
        'currency': (currency or 'USDT').strip().upper(),
        'channel': (channel or 'binance_pay').strip().lower(),
        'status': 'pending',
        'created_at': now,
        'updated_at': now,
        'paid_at': None,
        'failed_at': None,
        'activated_license_token': '',
        'activation_source': '',
        'meta': {},
    }
    db = _load()
    db.setdefault('payment_orders', []).append(order)
    _save(db)
    return order


def get_payment_order(order_id: str) -> dict | None:
    db = _load()
    for o in db.get('payment_orders', []):
        if o.get('order_id') == order_id:
            return o
    return None


def list_payment_orders(status: str | None = None, limit: int = 200, email: str | None = None):
    db = _load()
    rows = list(reversed(db.get('payment_orders', [])))
    out = []
    wanted = (status or '').strip().lower()
    target_email = (email or '').strip().lower()
    for row in rows:
        if wanted and (row.get('status') or '').strip().lower() != wanted:
            continue
        if target_email and (row.get('email') or '').strip().lower() != target_email:
            continue
        out.append(row)
        if len(out) >= limit:
            break
    return out


def update_payment_order_status(order_id: str, status: str, *, reason: str = '', paid_at: str | None = None, meta: dict | None = None) -> dict | None:
    status_norm = (status or '').strip().lower()
    if status_norm not in {'pending', 'paid', 'failed'}:
        raise ValueError('invalid_status')

    db = _load()
    changed = None
    for row in db.get('payment_orders', []):
        if row.get('order_id') != order_id:
            continue
        current = (row.get('status') or '').strip().lower()
        # terminal status idempotency: paid/failed should not be overwritten
        if current in {'paid', 'failed'} and status_norm != current:
            changed = row
            break
        row['status'] = status_norm
        row['updated_at'] = _utcnow().isoformat()
        if status_norm == 'paid':
            row['paid_at'] = paid_at or row.get('paid_at') or _utcnow().isoformat()
        if status_norm == 'failed':
            row['failed_at'] = row.get('failed_at') or _utcnow().isoformat()
        if reason:
            row['failure_reason'] = reason
        if meta:
            merged = row.get('meta') or {}
            merged.update(meta)
            row['meta'] = merged
        changed = row
        break

    if changed is not None:
        _save(db)
    return changed


def _find_latest_license_index(db: dict, email: str) -> int:
    target = (email or '').strip().lower()
    for idx in range(len(db.get('licenses', [])) - 1, -1, -1):
        rec = db['licenses'][idx]
        if (rec.get('email') or '').strip().lower() == target:
            return idx
    return -1


def activate_or_renew_license_by_order(order_id: str, source: str, *, idempotency_key: str = '') -> dict:
    db = _load()
    idem = (idempotency_key or '').strip()
    if idem and any(x.get('key') == idem for x in db.get('order_actions', [])):
        # already applied
        for o in db.get('payment_orders', []):
            if o.get('order_id') == order_id:
                return {'ok': True, 'duplicate': True, 'order': o, 'license': get_license_by_email(o.get('email', ''))}
        return {'ok': False, 'error': 'order_not_found'}

    order = None
    for o in db.get('payment_orders', []):
        if o.get('order_id') == order_id:
            order = o
            break
    if not order:
        return {'ok': False, 'error': 'order_not_found'}

    email = (order.get('email') or '').strip().lower()
    plan = (order.get('plan') or 'starter').strip().lower()
    cfg = plan_defaults(plan)
    days = int(cfg.get('days', 30))
    max_devices = int(cfg.get('max_devices', 1))

    idx = _find_latest_license_index(db, email)
    now = _utcnow()
    if idx >= 0:
        rec = db['licenses'][idx]
        exp_raw = rec.get('expires_at')
        try:
            exp = datetime.fromisoformat(exp_raw) if exp_raw else now
        except Exception:
            exp = now
        base = exp if exp > now else now
        rec['expires_at'] = (base + timedelta(days=days)).isoformat()
        rec['active'] = True
        rec['plan'] = plan
        rec['max_devices'] = max(rec.get('max_devices') or 0, max_devices)
        license_rec = rec
    else:
        token = secrets.token_urlsafe(24)
        license_rec = {
            'email': email,
            'plan': plan,
            'license_token': token,
            'license_key': _sign(token, email),
            'issued_at': now.isoformat(),
            'expires_at': (now + timedelta(days=days)).isoformat(),
            'max_devices': max_devices,
            'devices': [],
            'active': True,
        }
        db['licenses'].append(license_rec)

    # idempotent order mark
    order_status = (order.get('status') or '').strip().lower()
    if order_status != 'paid':
        order['status'] = 'paid'
        order['paid_at'] = order.get('paid_at') or now.isoformat()
    order['updated_at'] = now.isoformat()
    order['activated_license_token'] = license_rec.get('license_token', '')
    order['activation_source'] = source

    if idem:
        db['order_actions'].append({'key': idem, 'order_id': order_id, 'source': source, 'at': now.isoformat()})

    db.setdefault('payments', []).append({
        'event_id': f'order_activation:{order_id}:{source}',
        'status': 'paid',
        'email': email,
        'plan': plan,
        'order_id': order_id,
        'channel': order.get('channel'),
        'source': source,
        'created_at': now.isoformat(),
    })

    _save(db)
    return {'ok': True, 'duplicate': False, 'order': order, 'license': license_rec}


def mark_processed_event(event_id: str, source: str = 'webhook') -> bool:
    eid = (event_id or '').strip()
    if not eid:
        return False
    db = _load()
    if any(x.get('event_id') == eid for x in db.get('processed_events', [])):
        return False
    db['processed_events'].append({'event_id': eid, 'source': source, 'at': _utcnow().isoformat()})
    _save(db)
    return True


def is_processed_event(event_id: str) -> bool:
    eid = (event_id or '').strip()
    if not eid:
        return False
    db = _load()
    return any(x.get('event_id') == eid for x in db.get('processed_events', []))


def verify_binancepay_signature(payload_bytes: bytes, signature: str | None, secret: str) -> bool:
    if not secret:
        # Security fix (Fix #2): If secret is not configured, REJECT all webhooks.
        # Admin MUST set BINANCE_PAY_WEBHOOK_SECRET in production.
        raise ValueError(
            "BINANCE_PAY_WEBHOOK_SECRET is not configured. "
            "Webhook verification is disabled — this is insecure for production."
        )
    got = (signature or '').strip().lower()
    if not got:
        return False
    digest = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest().lower()
    return hmac.compare_digest(digest, got)
