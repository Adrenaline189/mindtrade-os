#!/usr/bin/env python3
"""Repeated start/stop loop to detect stop_timed_out false positives."""

import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bot.tenant_worker_manager as twm


def fake_engine_loop(tenant_id: str, stop_event=None, state=None, isolation_lock=None, license_gate=None):
    while not stop_event.is_set():
        if state is not None:
            state["ticks"] = int(state.get("ticks", 0)) + 1
            state["last_tick_at"] = time.time()
        time.sleep(0.02)

    # mimic cleanup jitter close to timeout boundaries
    time.sleep(random.uniform(0.005, 0.08))


def run(loops: int = 50, stop_timeout: float = 0.05):
    mgr = twm.TenantWorkerManager()
    mgr._runner = fake_engine_loop
    mgr._license_gate = lambda tenant_id: (True, "verify")

    tenant_ids = ["tenant_loop_a", "tenant_loop_b", "tenant_loop_c"]
    failures = []

    for i in range(loops):
        for tid in tenant_ids:
            ok = mgr.start(tid)
            if not ok:
                failures.append({"loop": i, "tenant": tid, "phase": "start_failed"})
        time.sleep(0.08)
        for tid in tenant_ids:
            mgr.stop(tid, timeout_sec=stop_timeout)
            st = mgr.status(tid)
            if st.get("stop_timed_out"):
                failures.append({"loop": i, "tenant": tid, "phase": "stop_timed_out_true"})

    result = {
        "loops": loops,
        "tenants": tenant_ids,
        "stop_timeout": stop_timeout,
        "failures": failures,
        "passed": len(failures) == 0,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(run())
