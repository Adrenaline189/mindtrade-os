#!/usr/bin/env python3
"""Smoke test billing enforcement loop: auto-stop on gate fail + clean restart on renew."""

from __future__ import annotations

import threading
import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

import bot.tenant_worker_manager as twm


def fake_engine_loop(tenant_id: str, stop_event=None, state=None, isolation_lock=None, license_gate=None):
    state = state or {}
    state["running"] = True
    while stop_event is not None and not stop_event.is_set():
        if isolation_lock is not None:
            isolation_lock.acquire()
        try:
            state["ticks"] = int(state.get("ticks", 0)) + 1
            state["last_tick_at"] = time.time()
        finally:
            if isolation_lock is not None:
                isolation_lock.release()
        time.sleep(0.05)
    state["running"] = False


def main():
    mgr = twm.TenantWorkerManager()
    mgr._runner = fake_engine_loop

    gate = {"ok": True, "reason": "valid"}

    def license_gate(_tenant_id: str):
        return gate["ok"], gate["reason"]

    mgr._license_gate = license_gate

    tid = "tenant_billing_smoke"
    assert mgr.start(tid) is True, "initial start must pass"
    time.sleep(0.3)
    assert mgr.status(tid).get("running") is True, "worker should be running"

    gate["ok"] = False
    gate["reason"] = "suspended"

    deadline = time.time() + 2.5
    while time.time() < deadline:
        mgr._reconcile_once()
        st = mgr.status(tid)
        if not st.get("running"):
            break
        time.sleep(0.1)
    st = mgr.status(tid)
    assert st.get("running") is False, f"worker should auto-stop: {st}"
    assert st.get("license_ok") is False and st.get("license_reason") == "suspended", f"bad gate state: {st}"

    gate["ok"] = True
    gate["reason"] = "valid"
    assert mgr.start(tid) is True, "restart after renew/activate must work"
    time.sleep(0.25)
    st2 = mgr.status(tid)
    assert st2.get("running") is True, f"restart failed: {st2}"

    mgr.stop(tid, timeout_sec=1.0)
    print({"ok": True, "auto_stop_reason": st.get("license_reason"), "restarted": st2.get("running")})


if __name__ == "__main__":
    main()
