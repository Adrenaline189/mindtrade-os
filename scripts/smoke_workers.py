#!/usr/bin/env python3
"""Smoke checks for Phase 2 tenant worker manager."""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from bot.engine_manager import engine_manager


def main():
    t1 = "default"
    t2 = "tenant_smoke"

    s1 = engine_manager.start(t1)
    s2 = engine_manager.start(t2)

    st1 = engine_manager.status(t1)
    st2 = engine_manager.status(t2)

    assert st1.get("exists"), "default status missing"
    # tenant_smoke usually has no mapped email/license, so start should be blocked
    assert (s2 is False), "tenant_smoke should be blocked by license gate"
    assert st2.get("license_ok") is False, "tenant_smoke license gate should fail"

    engine_manager.stop(t1)
    engine_manager.stop(t2)

    print({
        "start_default": s1,
        "start_tenant_smoke": s2,
        "status_default": st1,
        "status_tenant_smoke": st2,
    })


if __name__ == "__main__":
    main()
