#!/usr/bin/env python3
"""Mini load test for tenant workers (3-5 tenants, short runtime)."""

from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

import bot.tenant_worker_manager as twm


def fake_engine_loop(tenant_id: str, stop_event=None, state=None, isolation_lock=None, license_gate=None):
    state = state or {}
    while stop_event is not None and not stop_event.is_set():
        if isolation_lock is not None:
            isolation_lock.acquire()
        try:
            state["tenant_id"] = tenant_id
            state["last_tick_at"] = time.time()
            state["ticks"] = int(state.get("ticks", 0)) + 1
            if int(state["ticks"]) % 17 == 0:
                state["sample_metric"] = f"{tenant_id}:{state['ticks']}"
        finally:
            if isolation_lock is not None:
                isolation_lock.release()
        if stop_event.wait(0.05):
            break


def run(tenants: int, duration_sec: float):
    if tenants < 3 or tenants > 5:
        raise ValueError("tenants must be between 3 and 5")

    mgr = twm.TenantWorkerManager()
    mgr._license_gate = lambda tenant_id: (True, "load_test")
    mgr._runner = fake_engine_loop

    tenant_ids = [f"tenant_load_{i+1}" for i in range(tenants)]
    started = {}

    def starter(tid: str):
        started[tid] = mgr.start(tid)

    threads = [threading.Thread(target=starter, args=(tid,)) for tid in tenant_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    time.sleep(max(0.5, duration_sec))

    before_stop = {tid: mgr.status(tid) for tid in tenant_ids}

    stop_results = {}
    for tid in tenant_ids:
        stop_results[tid] = mgr.stop(tid, timeout_sec=5.0)

    time.sleep(0.1)
    after_stop = {tid: mgr.status(tid) for tid in tenant_ids}

    tick_counts = {tid: int(before_stop[tid].get("ticks", 0) or 0) for tid in tenant_ids}
    tick_age = {tid: before_stop[tid].get("tick_age_sec") for tid in tenant_ids}

    checks = {
        "all_started": all(started.get(tid) for tid in tenant_ids),
        "all_running_before_stop": all(before_stop[tid].get("running") for tid in tenant_ids),
        "all_ticks_positive": all(tick_counts[tid] > 0 for tid in tenant_ids),
        "no_stop_timeout": all(not before_stop[tid].get("stop_timed_out", False) for tid in tenant_ids),
        "all_stop_calls_ok": all(stop_results.values()),
        "all_stopped_after": all(not after_stop[tid].get("running", False) for tid in tenant_ids),
    }
    passed = all(checks.values())

    result = {
        "passed": passed,
        "tenants": tenants,
        "duration_sec": duration_sec,
        "checks": checks,
        "started": started,
        "stop_results": stop_results,
        "tick_counts": tick_counts,
        "tick_age_sec": tick_age,
        "before_stop": before_stop,
        "after_stop": after_stop,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if passed else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenants", type=int, default=3)
    ap.add_argument("--duration", type=float, default=3.0)
    args = ap.parse_args()
    raise SystemExit(run(args.tenants, args.duration))


if __name__ == "__main__":
    main()
