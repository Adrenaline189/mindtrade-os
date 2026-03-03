#!/usr/bin/env python3
"""Smoke test: concurrent multi-tenant worker lifecycle + data isolation markers."""

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
    ticks = 0
    while stop_event is not None and not stop_event.is_set() and ticks < 150:
        if isolation_lock is not None:
            isolation_lock.acquire()
        try:
            state.setdefault("ticks", 0)
            state["ticks"] += 1
            state["tenant_tag"] = f"tag:{tenant_id}"
            state["metric_total_r"] = state["ticks"] * (1 if tenant_id.endswith("a") else 2 if tenant_id.endswith("b") else 3)
        finally:
            if isolation_lock is not None:
                isolation_lock.release()
        ticks += 1
        time.sleep(0.01)
    state["running"] = False


def main():
    mgr = twm.TenantWorkerManager()
    mgr._license_gate = lambda tenant_id: (True, "smoke")
    mgr._runner = fake_engine_loop

    tenants = ["tenant_a", "tenant_b", "tenant_c"]
    started = {}

    def starter(tid):
        started[tid] = mgr.start(tid)

    threads = [threading.Thread(target=starter, args=(tid,)) for tid in tenants]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(started.values()), f"failed to start some workers: {started}"

    # start idempotency
    again = mgr.start("tenant_a")
    st_a = mgr.status("tenant_a")
    assert again is True and st_a.get("already_running") is True, "idempotent start failed"

    time.sleep(0.25)

    statuses = {tid: mgr.status(tid) for tid in tenants}
    assert all(st.get("exists") for st in statuses.values()), f"worker missing: {statuses}"

    wa = mgr._workers["tenant_a"].state
    wb = mgr._workers["tenant_b"].state
    wc = mgr._workers["tenant_c"].state

    assert wa.get("tenant_tag") == "tag:tenant_a", "tenant A state leakage"
    assert wb.get("tenant_tag") == "tag:tenant_b", "tenant B state leakage"
    assert wc.get("tenant_tag") == "tag:tenant_c", "tenant C state leakage"

    # isolated metrics markers
    m = {
        "tenant_a": wa.get("metric_total_r"),
        "tenant_b": wb.get("metric_total_r"),
        "tenant_c": wc.get("metric_total_r"),
    }
    assert len(set(m.values())) == 3, f"metrics not isolated: {m}"

    for tid in tenants:
        assert mgr.stop(tid, timeout_sec=2.0) is True
    time.sleep(0.05)

    out = {
        "started": started,
        "statuses": {tid: mgr.status(tid) for tid in tenants},
        "ticks": {
            "tenant_a": wa.get("ticks", 0),
            "tenant_b": wb.get("ticks", 0),
            "tenant_c": wc.get("ticks", 0),
        },
        "metrics": m,
    }
    print(out)


if __name__ == "__main__":
    main()
