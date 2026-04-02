"""
FIX 3: Add license data backup script

CREATE a new file: scripts/backup_licenses.py

#!/usr/bin/env python3
"""
Backup license and tenant data with timestamped snapshots.
Run via cron or manually: python scripts/backup_licenses.py
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSE_FILE = ROOT / "licenses" / "licenses.json"
TENANT_FILE = ROOT / "licenses" / "tenants.json"
BACKUP_DIR = ROOT / "licenses" / "backups"

def backup_file(src: Path, backup_dir: Path) -> Path | None:
    if not src.exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = backup_dir / f"{src.stem}_{timestamp}{src.suffix}"
    shutil.copy2(src, dst)
    return dst

def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] Starting license backup...")

    license_dst = backup_file(LICENSE_FILE, BACKUP_DIR)
    tenant_dst = backup_file(TENANT_FILE, BACKUP_DIR)

    if license_dst:
        print(f"  ✓ License backed up: {license_dst.name}")
    if tenant_dst:
        print(f"  ✓ Tenants backed up: {tenant_dst.name}")

    # Cleanup old backups (keep last 30)
    backups = sorted(BACKUP_DIR.glob("licenses_*.json"))
    for old in backups[:-30]:
        old.unlink()
        print(f"  🗑 Removed old backup: {old.name}")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Backup complete.")

if __name__ == "__main__":
    main()


TO AUTOMATE: Add to crontab (crontab -e):
0 2 * * * cd /path/to/mindtrade-os && ./venv/bin/python scripts/backup_licenses.py >> logs/backup.log 2>&1
"""
