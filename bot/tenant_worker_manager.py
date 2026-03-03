import threading
import time
from dataclasses import dataclass

from bot.engine import run_engine_for_tenant
from bot.license_service import license_state_for_email
from bot.state import create_bot_state
from bot.tenant_context import default_tenant_id
from bot.tenant_store import get_primary_email_for_tenant


@dataclass
class TenantWorker:
    tenant_id: str
    thread: threading.Thread
    stop_event: threading.Event
    state: dict
    started_at: float


class TenantWorkerManager:
    """
    Phase 2 foundation: one worker thread per tenant.

    Safety design (current):
    - Workers are per-tenant threads.
    - Engine internals still rely on shared globals, so workers enter a global
      isolation lock before each tick to strictly isolate tenant context.
    - This is intentionally conservative and backward-compatible.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._engine_isolation_lock = threading.Lock()
        self._workers: dict[str, TenantWorker] = {}

    def _normalize_tenant(self, tenant_id: str | None) -> str:
        return (tenant_id or default_tenant_id()).strip() or default_tenant_id()

    def _license_gate(self, tenant_id: str) -> tuple[bool, str]:
        email = get_primary_email_for_tenant(tenant_id)
        if not email and tenant_id == default_tenant_id():
            # default/system tenant can run without customer license binding
            return True, 'default_tenant'
        if not email:
            return False, 'tenant_email_not_found'
        ok, reason, _ = license_state_for_email(email)
        return ok, reason

    def start(self, tenant_id: str | None) -> bool:
        tid = self._normalize_tenant(tenant_id)
        lic_ok, lic_reason = self._license_gate(tid)
        if not lic_ok:
            return False
        with self._lock:
            existing = self._workers.get(tid)
            if existing and existing.thread.is_alive():
                return False

            state = create_bot_state()
            state["running"] = True
            state["license_ok"] = True
            state["license_reason"] = lic_reason
            stop_event = threading.Event()
            thread = threading.Thread(
                target=run_engine_for_tenant,
                kwargs={
                    "tenant_id": tid,
                    "stop_event": stop_event,
                    "state": state,
                    "isolation_lock": self._engine_isolation_lock,
                    "license_gate": self._license_gate,
                },
                daemon=True,
                name=f"tenant-worker-{tid}",
            )
            worker = TenantWorker(
                tenant_id=tid,
                thread=thread,
                stop_event=stop_event,
                state=state,
                started_at=time.time(),
            )
            self._workers[tid] = worker
            thread.start()
            return True

    def stop(self, tenant_id: str | None) -> bool:
        tid = self._normalize_tenant(tenant_id)
        with self._lock:
            worker = self._workers.get(tid)
            if not worker:
                return False
            worker.state["running"] = False
            worker.stop_event.set()
            return True

    def stop_all(self) -> int:
        with self._lock:
            ids = list(self._workers.keys())
        count = 0
        for tid in ids:
            if self.stop(tid):
                count += 1
        return count

    def status(self, tenant_id: str | None) -> dict:
        tid = self._normalize_tenant(tenant_id)
        gate_ok, gate_reason = self._license_gate(tid)
        with self._lock:
            worker = self._workers.get(tid)
            if not worker:
                return {
                    "tenant_id": tid,
                    "running": False,
                    "exists": False,
                    "license_ok": gate_ok,
                    "license_reason": gate_reason,
                }
            alive = worker.thread.is_alive()
            return {
                "tenant_id": tid,
                "running": alive and not worker.stop_event.is_set(),
                "exists": True,
                "thread_name": worker.thread.name,
                "started_at": worker.started_at,
                "license_ok": bool(worker.state.get('license_ok', gate_ok)),
                "license_reason": worker.state.get('license_reason', gate_reason),
            }

    def list_status(self) -> list[dict]:
        with self._lock:
            workers = list(self._workers.values())
        return [self.status(w.tenant_id) for w in workers]


tenant_worker_manager = TenantWorkerManager()
