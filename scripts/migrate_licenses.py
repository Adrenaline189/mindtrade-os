#!/usr/bin/env python3
"""
License database migration runner.
Keeps track of applied migrations and runs only new ones.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSE_FILE = ROOT / "licenses" / "licenses.json"
MIGRATION_LOG = ROOT / "licenses" / ".migrations"

MIGRATIONS = [
    (
        "1.0",
        "Initial schema - add 'plan' field if missing",
        lambda db: [
            rec.update({"plan": rec.get("plan", "starter")})
            for rec in db.get("licenses", [])
            if "plan" not in rec
        ]
    ),
    (
        "1.1",
        "Add 'created_at' to licenses missing it",
        lambda db: [
            rec.setdefault("created_at", rec.get("issued_at", ""))
            for rec in db.get("licenses", [])
        ]
    ),
]

def get_applied_migrations():
    if not MIGRATION_LOG.exists():
        return set()
    return set(json.loads(MIGRATION_LOG.read_text()))

def mark_applied(version: str):
    applied = get_applied_migrations()
    applied.add(version)
    MIGRATION_LOG.write_text(json.dumps(list(applied), indent=2))

def run_migrations():
    if not LICENSE_FILE.exists():
        print("No license database found. Skipping migrations.")
        return

    db = json.loads(LICENSE_FILE.read_text())
    applied = get_applied_migrations()

    for version, description, apply_fn in MIGRATIONS:
        if version in applied:
            continue
        print(f"Applying migration {version}: {description}...")
        try:
            apply_fn(db)
            LICENSE_FILE.write_text(json.dumps(db, indent=2, ensure_ascii=False))
            mark_applied(version)
            print(f"  Migration {version} applied.")
        except Exception as e:
            print(f"  Migration {version} failed: {e}")
            sys.exit(1)

    print("All migrations complete.")

if __name__ == "__main__":
    run_migrations()
