#!/usr/bin/env python3
"""
Backup license and tenant data with timestamped snapshots.
Run: python scripts/backup_licenses.py
"""
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSE_FILE = ROOT / "licenses" / "licenses.json"
TENANT_FILE = ROOT / "licenses" / "tenants.json"
BACKUP_DIR = ROOT / "licenses" / "backups"

def backup_file(src, backup_dir):
    if not src.exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    dst = backup_dir / f"{src.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{src.suffix}"
    shutil.copy2(src, dst)
    return dst

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting license backup...")
    l = backup_file(LICENSE_FILE, BACKUP_DIR)
    t = backup_file(TENANT_FILE, BACKUP_DIR)
    if l: print(f"  License backed up: {l.name}")
    if t: print(f"  Tenants backed up: {t.name}")
    backups = sorted(BACKUP_DIR.glob("licenses_*.json"))
    for b in backups[:-30]: b.unlink(); print(f"  Removed: {b.name}")
    print(f"Backup complete.")

if __name__ == "__main__":
    main()
