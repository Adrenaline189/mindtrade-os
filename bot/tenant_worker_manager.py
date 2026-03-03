import threading
import time
from dataclasses import dataclass

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
    start_nonce: float


class TenantWorkerManager:
    """
    Phase 2.1 worker manager hardening.

    Safety additions:
    - stale worker cleanup (dead thread records purged)
    - start idempotency (`already_running` state marker)
    - stop timeout observability (`stop_timed_out` marker)
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._engine_isolation_lock = threading.Lock()
        self._workers: dict[str, TenantWorker] = {}
        self._runner = None

    def _normalize_tenant(self, tenant_id: str | None) -> str:
        return (tenant_id or default_tenant_id()).strip() or default_tenant_id()

    def _license_gate(self, tenant_id: str) -> tuple[bool, str]:
        email = get_primary_email_for_tenant(tenant_id)
        if not email and tenant_id == default_tenant_id():
            return True, 'default_tenant'
        if not email:
            return False, 'tenant_email_not_found'
        ok, reason, _ = license_state_for_email(email)
        return ok, reason

    def _cleanup_stale_locked(self):
        stale_ids = []
        for tid, worker in self._workers.items():
            if not worker.thread.is_alive() and worker.stop_event.is_set():
                stale_ids.append(tid)
            elif not worker.thread.is_alive() and not worker.state.get("running", False):
                stale_ids.append(tid)
        for tid in stale_ids:
            self._workers.pop(tid, None)

    def start(self, tenant_id: str | None) -> bool:
        tid = self._normalize_tenant(tenant_id)
        lic_ok, lic_reason = self._license_gate(tid)
        if not lic_ok:
            return False
        with self._lock:
            self._cleanup_stale_locked()
            existing = self._workers.get(tid)
            if existing and existing.thread.is_alive() and not existing.stop_event.is_set():
                existing.state["already_running"] = True
                return True

            state = create_bot_state()
            state["running"] = True
            state["license_ok"] = True
            state["license_reason"] = lic_reason
            state["already_running"] = False
            state["stop_timed_out"] = False
            state["stop_timeout_sec"] = 0
            stop_event = threading.Event()
            start_nonce = time.time()
            if self._runner is None:
                from bot.engine import run_engine_for_tenant
                self._runner = run_engine_for_tenant
            thread = threading.Thread(
                target=self._runner,
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
                started_at=start_nonce,
                start_nonce=start_nonce,
            )
            self._workers[tid] = worker
            thread.start()
            return True

    def stop(self, tenant_id: str | None, timeout_sec: float = 10.0) -> bool:
        tid = self._normalize_tenant(tenant_id)
        worker = None
        with self._lock:
            self._cleanup_stale_locked()
            worker = self._workers.get(tid)
            if not worker:
                return False
            worker.state["running"] = False
            worker.state["stop_timeout_sec"] = timeout_sec
            worker.stop_event.set()

        worker.thread.join(timeout=max(0.1, float(timeout_sec)))
        timed_out = worker.thread.is_alive()

        with self._lock:
            fresh = self._workers.get(tid)
            if fresh and fresh.start_nonce == worker.start_nonce:
                fresh.state["stop_timed_out"] = bool(timed_out)
                if not timed_out:
                    self._workers.pop(tid, None)
        return True

    def stop_all(self, timeout_sec: float = 10.0) -> int:
        with self._lock:
            ids = list(self._workers.keys())
        count = 0
        for tid in ids:
            if self.stop(tid, timeout_sec=timeout_sec):
                count += 1
        return count

    def status(self, tenant_id: str | None) -> dict:
        tid = self._normalize_tenant(tenant_id)
        gate_ok, gate_reason = self._license_gate(tid)
        with self._lock:
            self._cleanup_stale_locked()
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
                "already_running": bool(worker.state.get("already_running", False)),
                "stop_timed_out": bool(worker.state.get("stop_timed_out", False)),
                "stop_timeout_sec": float(worker.state.get("stop_timeout_sec", 0)),
            }

    def list_status(self) -> list[dict]:
        with self._lock:
            self._cleanup_stale_locked()
            worker_ids = list(self._workers.keys())
        return [self.status(tid) for tid in worker_ids]


tenant_worker_manager = TenantWorkerManager()
