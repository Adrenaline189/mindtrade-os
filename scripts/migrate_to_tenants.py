#!/usr/bin/env python3
"""
Phase 1 migration: move legacy global files into default tenant scope.

Legacy:
- data/paper_trades.csv
- data/trading_bot.db
- data/runtime_config.json
- licenses/user_api_keys.json

Target:
- data/tenants/default/*
"""

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "data" / "tenants" / "default"

MAPPINGS = [
    (ROOT / "data" / "paper_trades.csv", DEFAULT_DIR / "paper_trades.csv"),
    (ROOT / "data" / "trading_bot.db", DEFAULT_DIR / "trading_bot.db"),
    (ROOT / "data" / "runtime_config.json", DEFAULT_DIR / "runtime_config.json"),
    (ROOT / "licenses" / "user_api_keys.json", DEFAULT_DIR / "user_api_keys.json"),
]


def migrate():
    DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
    for src, dst in MAPPINGS:
        if not src.exists():
            print(f"SKIP {src} (not found)")
            continue
        if dst.exists():
            print(f"SKIP {dst} (already exists)")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"OK {src} -> {dst}")


if __name__ == "__main__":
    migrate()
