import base64
import json
import os
from cryptography.fernet import Fernet

from bot.paths import get_tenant_paths
from bot.tenant_context import get_current_tenant
from bot.tenant_store import get_tenant_for_user


def _db_path(tenant_id: str | None = None):
    tid = tenant_id or get_current_tenant()
    return get_tenant_paths(tid)["api_key_db"]


def _fernet():
    raw = os.getenv('API_VAULT_SECRET', 'mindtrade-api-vault-secret-v1').encode()
    key = base64.urlsafe_b64encode(raw.ljust(32, b'_')[:32])
    return Fernet(key)


def _load(tenant_id: str | None = None):
    db_path = _db_path(tenant_id)
    if not db_path.exists():
        return {'items': []}
    data = json.loads(db_path.read_text())
    data.setdefault('items', [])
    return data


def _save(data, tenant_id: str | None = None):
    db_path = _db_path(tenant_id)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def tenant_api_scope_for_email(email: str) -> str:
    return get_tenant_for_user((email or '').strip().lower())


def set_user_api(email: str, api_key: str, api_secret: str, tenant_id: str | None = None):
    email = (email or '').strip().lower()
    tenant_id = tenant_id or tenant_api_scope_for_email(email)
    f = _fernet()
    db = _load(tenant_id)
    enc_key = f.encrypt((api_key or '').encode()).decode()
    enc_sec = f.encrypt((api_secret or '').encode()).decode()
    found = False
    for it in db['items']:
        if (it.get('email') or '').lower() == email:
            it['api_key_enc'] = enc_key
            it['api_secret_enc'] = enc_sec
            found = True
            break
    if not found:
        db['items'].append({'email': email, 'api_key_enc': enc_key, 'api_secret_enc': enc_sec})
    _save(db, tenant_id)


def get_user_api(email: str, tenant_id: str | None = None):
    email = (email or '').strip().lower()
    tenant_id = tenant_id or tenant_api_scope_for_email(email)
    f = _fernet()
    db = _load(tenant_id)
    for it in db.get('items', []):
        if (it.get('email') or '').lower() == email:
            try:
                k = f.decrypt(it['api_key_enc'].encode()).decode()
                s = f.decrypt(it['api_secret_enc'].encode()).decode()
                return k, s
            except Exception:
                return '', ''
    return '', ''


def has_user_api(email: str, tenant_id: str | None = None) -> bool:
    k, s = get_user_api(email, tenant_id=tenant_id)
    return bool(k and s)
