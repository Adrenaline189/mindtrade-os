import json
import os
import platform
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'licenses' / 'licenses.json'


def _device_id():
    return f"{platform.node()}::{platform.system()}::{platform.machine()}"


def _load():
    if not DB.exists():
        return {"licenses": []}
    return json.loads(DB.read_text())


def _save(d):
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.write_text(json.dumps(d, indent=2, ensure_ascii=False))


def license_ok() -> tuple[bool, str]:
    required = os.getenv('REQUIRED_LICENSE_TOKEN', '').strip()
    provided = os.getenv('LICENSE_TOKEN', '').strip()

    if not required and not provided:
        return True, 'dev_mode'

    token = provided or required
    if not token:
        return False, 'missing_token'

    db = _load()
    rec = next((x for x in db.get('licenses', []) if x.get('license_token') == token), None)
    if not rec:
        if required and provided == required:
            return True, 'env_token_match'
        return False, 'token_not_found'

    if rec.get('active') is False:
        return False, 'suspended'

    exp = rec.get('expires_at')
    if exp and datetime.utcnow() > datetime.fromisoformat(exp):
        return False, 'expired'

    dev = _device_id()
    devices = rec.setdefault('devices', [])
    if dev not in devices:
        if len(devices) >= int(rec.get('max_devices', 1)):
            return False, 'device_limit'
        devices.append(dev)
        _save(db)

    return True, 'valid'
