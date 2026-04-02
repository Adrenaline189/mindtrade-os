import hashlib
import json
from datetime import datetime
from pathlib import Path

from bot.paths import get_license_root

from bot.tenant_context import default_tenant_id

ROOT = Path(__file__).resolve().parents[1]
DB = get_license_root() / "tenants.json"


def _load():
    if not DB.exists():
        return {"tenants": [], "user_tenants": []}
    data = json.loads(DB.read_text())
    data.setdefault("tenants", [])
    data.setdefault("user_tenants", [])
    return data


def _save(data):
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def ensure_default_tenant() -> str:
    tenant_id = default_tenant_id()
    data = _load()
    if not any(t.get("tenant_id") == tenant_id for t in data["tenants"]):
        data["tenants"].append(
            {
                "tenant_id": tenant_id,
                "name": "Default Tenant",
                "created_at": datetime.utcnow().isoformat(),
                "is_default": True,
            }
        )
        _save(data)
    return tenant_id


def _tenant_id_for_email(email: str) -> str:
    digest = hashlib.sha1(email.encode()).hexdigest()[:12]
    return f"tenant_{digest}"


def get_tenant_for_user(email: str) -> str:
    email = (email or "").strip().lower()
    if not email:
        return ensure_default_tenant()

    data = _load()
    for m in data.get("user_tenants", []):
        if (m.get("email") or "").strip().lower() == email:
            return m.get("tenant_id") or ensure_default_tenant()

    tenant_id = _tenant_id_for_email(email)
    if not any(t.get("tenant_id") == tenant_id for t in data["tenants"]):
        data["tenants"].append(
            {
                "tenant_id": tenant_id,
                "name": email,
                "created_at": datetime.utcnow().isoformat(),
                "is_default": False,
            }
        )
    data["user_tenants"].append(
        {
            "email": email,
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow().isoformat(),
        }
    )
    _save(data)
    return tenant_id


def list_tenants() -> list[dict]:
    data = _load()
    tenants = list(data.get("tenants", []))
    mappings = data.get("user_tenants", [])

    for t in tenants:
        tid = t.get("tenant_id")
        emails = [
            (m.get("email") or "").strip().lower()
            for m in mappings
            if (m.get("tenant_id") or "") == tid
        ]
        t["emails"] = [e for e in emails if e]
    return tenants


def get_primary_email_for_tenant(tenant_id: str) -> str:
    tid = (tenant_id or "").strip()
    if not tid:
        return ""
    data = _load()
    for m in data.get("user_tenants", []):
        if (m.get("tenant_id") or "") == tid:
            return (m.get("email") or "").strip().lower()
    return ""
