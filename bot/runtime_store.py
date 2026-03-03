import json

from bot.config_runtime import RUNTIME_CONFIG
from bot.paths import get_tenant_paths
from bot.tenant_context import get_current_tenant


def _runtime_file(tenant_id: str | None = None):
    tid = tenant_id or get_current_tenant()
    return get_tenant_paths(tid)["runtime_config"]


def save_runtime_config(tenant_id: str | None = None) -> None:
    runtime_file = _runtime_file(tenant_id)
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_file.write_text(json.dumps(RUNTIME_CONFIG, indent=2, ensure_ascii=False))


def load_runtime_config(tenant_id: str | None = None) -> None:
    runtime_file = _runtime_file(tenant_id)
    if not runtime_file.exists():
        return
    try:
        data = json.loads(runtime_file.read_text())
    except Exception:
        return
    if not isinstance(data, dict):
        return
    for k in list(RUNTIME_CONFIG.keys()):
        if k in data:
            RUNTIME_CONFIG[k] = data[k]
