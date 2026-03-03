import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from bot.license_service import license_state_for_email
from bot.state import create_bot_state
from bot.tenant_context import default_tenant_id
from bot.tenant_store import get_primary_email_for_tenant, list_tenants


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
    Phase 3 worker manager hardening.

    Safety additions:
    - stale worker cleanup (dead thread records purged)
    - start idempotency (`already_running` state marker)
    - stop timeout observability (`stop_timed_out` marker)
    - per-tenant isolation lock (no global lock serialization)
    - crash containment metadata per worker
    - periodic reconciler to enforce license gates for running workers
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._tenant_locks: dict[str, threading.Lock] = {}
        self._workers: dict[str, TenantWorker] = {}
        self._runner = None

        self._reconciler_interval_sec = 10.0
        self._reconciler_stop = threading.Event()
        self._reconciler_thread = threading.Thread(
            target=self._reconcile_loop,
            daemon=True,
            name="tenant-worker-reconciler",
        )
        self._reconciler_thread.start()

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

    def _should_force_stop(self, tenant_id: str) -> tuple[bool, str]:
        ok, reason = self._license_gate(tenant_id)
        if ok:
            return False, reason
        enforced_reasons = {
            "suspended",
            "expired",
            "license_not_found",
            "invalid_expiry",
            "tenant_email_not_found",
        }
        return reason in enforced_reasons, reason

    def _reconcile_once(self):
        with self._lock:
            self._cleanup_stale_locked()
            running_ids = [tid for tid, w in self._workers.items() if w.thread.is_alive() and not w.stop_event.is_set()]

        known_tenants = {t.get("tenant_id") for t in list_tenants() if t.get("tenant_id")}
        known_tenants.update(running_ids)

        for tid in sorted(known_tenants):
            should_stop, reason = self._should_force_stop(tid)
            if not should_stop:
                continue
            with self._lock:
                worker = self._workers.get(tid)
                if worker and worker.thread.is_alive() and not worker.stop_event.is_set():
                    worker.state["license_ok"] = False
                    worker.state["license_reason"] = reason
                    worker.state["enforcement_reason"] = f"license_gate:{reason}"
                    worker.state["running"] = False
                    worker.stop_event.set()

    def _reconcile_loop(self):
        while not self._reconciler_stop.is_set():
            try:
                self._reconcile_once()
            except Exception:
                pass
            if self._reconciler_stop.wait(self._reconciler_interval_sec):
                break

    def _tenant_lock(self, tenant_id: str) -> threading.Lock:
        with self._lock:
            lock = self._tenant_locks.get(tenant_id)
            if lock is None:
                lock = threading.Lock()
                self._tenant_locks[tenant_id] = lock
            return lock

    def _run_worker(self, tenant_id: str, stop_event: threading.Event, state: dict):
        state["running"] = True
        try:
            self._runner(
                tenant_id=tenant_id,
                stop_event=stop_event,
                state=state,
                isolation_lock=self._tenant_lock(tenant_id),
                license_gate=self._license_gate,
            )
        except Exception as e:
            state["last_error"] = str(e)
            state["crashed"] = True
        finally:
            state["running"] = False

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
            state["last_stop_latency_sec"] = 0.0
            state["stop_requested_at"] = 0.0
            state["last_stopped_at"] = 0.0
            state["last_error"] = ""
            state["crashed"] = False
            state["last_tick_at"] = 0.0
            state["enforcement_reason"] = ""
            stop_event = threading.Event()
            start_nonce = time.time()
            if self._runner is None:
                from bot.engine import run_engine_for_tenant
                self._runner = run_engine_for_tenant
            thread = threading.Thread(
                target=self._run_worker,
                kwargs={
                    "tenant_id": tid,
                    "stop_event": stop_event,
                    "state": state,
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

    def stop(self, tenant_id: str | None, timeout_sec: float = 20.0) -> bool:
        tid = self._normalize_tenant(tenant_id)
        worker = None
        started_wait = time.monotonic()
        with self._lock:
            self._cleanup_stale_locked()
            worker = self._workers.get(tid)
            if not worker:
                return False
            worker.state["running"] = False
            worker.state["stop_timeout_sec"] = float(timeout_sec)
            worker.state["stop_requested_at"] = time.time()
            worker.stop_event.set()

        worker.thread.join(timeout=max(0.1, float(timeout_sec)))
        timed_out = worker.thread.is_alive()
        if timed_out:
            # Avoid near-boundary false positives when the thread exits right
            # after join() timeout returns.
            worker.thread.join(timeout=0.25)
            timed_out = worker.thread.is_alive()
        stop_latency = max(0.0, time.monotonic() - started_wait)

        with self._lock:
            fresh = self._workers.get(tid)
            if fresh and fresh.start_nonce == worker.start_nonce:
                fresh.state["stop_timed_out"] = bool(timed_out)
                fresh.state["last_stop_latency_sec"] = stop_latency
                fresh.state["last_stopped_at"] = time.time()
                if not timed_out:
                    self._workers.pop(tid, None)
        return True

    def stop_all(self, timeout_sec: float = 20.0) -> int:
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
                    "last_error": "",
                    "stop_timed_out": False,
                    "last_stop_latency_sec": 0.0,
                    "crashed": False,
                    "enforcement_reason": "",
                    "last_tick_at": 0.0,
                    "tick_age_sec": None,
                }
            alive = worker.thread.is_alive()
            last_tick_at = float(worker.state.get("last_tick_at", 0.0) or 0.0)
            tick_age_sec = max(0.0, time.time() - last_tick_at) if last_tick_at > 0 else None
            return {
                "tenant_id": tid,
                "running": alive and not worker.stop_event.is_set(),
                "exists": True,
                "thread_name": worker.thread.name,
                "started_at": worker.started_at,
                "started_at_iso": datetime.fromtimestamp(worker.started_at, timezone.utc).isoformat(),
                "license_ok": bool(worker.state.get('license_ok', gate_ok)),
                "license_reason": worker.state.get('license_reason', gate_reason),
                "already_running": bool(worker.state.get("already_running", False)),
                "stop_timed_out": bool(worker.state.get("stop_timed_out", False)),
                "stop_timeout_sec": float(worker.state.get("stop_timeout_sec", 0)),
                "last_stop_latency_sec": float(worker.state.get("last_stop_latency_sec", 0.0) or 0.0),
                "last_error": worker.state.get("last_error", ""),
                "crashed": bool(worker.state.get("crashed", False)),
                "enforcement_reason": worker.state.get("enforcement_reason", ""),
                "ticks": int(worker.state.get("ticks", 0)),
                "last_tick_at": last_tick_at,
                "tick_age_sec": tick_age_sec,
            }

    def list_status(self) -> list[dict]:
        with self._lock:
            self._cleanup_stale_locked()
            worker_ids = list(self._workers.keys())
        return [self.status(tid) for tid in worker_ids]


tenant_worker_manager = TenantWorkerManager()
