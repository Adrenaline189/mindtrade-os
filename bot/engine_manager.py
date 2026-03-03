import threading

from bot.tenant_context import default_tenant_id
from bot.tenant_worker_manager import tenant_worker_manager


class EngineManager:
    """
    Backward-compatible facade.

    - Existing UI/API still calls EngineManager.start/stop.
    - Underneath, we now route to per-tenant workers.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._active_tenant_id = default_tenant_id()

    @property
    def active_tenant_id(self) -> str:
        return self._active_tenant_id

    def start(self, tenant_id: str) -> bool:
        with self._lock:
            self._active_tenant_id = (tenant_id or self._active_tenant_id).strip() or default_tenant_id()
            return tenant_worker_manager.start(self._active_tenant_id)

    def stop(self, tenant_id: str | None = None):
        with self._lock:
            tid = (tenant_id or self._active_tenant_id).strip() if tenant_id is not None else None
        if tid:
            return tenant_worker_manager.stop(tid)
        return tenant_worker_manager.stop_all() > 0

    def status(self, tenant_id: str | None = None) -> dict:
        tid = tenant_id or self._active_tenant_id
        return tenant_worker_manager.status(tid)

    def list_status(self) -> list[dict]:
        return tenant_worker_manager.list_status()


engine_manager = EngineManager()
