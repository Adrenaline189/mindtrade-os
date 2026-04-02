#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_FILE="${1:-}"
OUT_DIR="${2:-$ROOT/tmp/restore_drill}"

if [[ -z "$BACKUP_FILE" ]]; then
  echo "usage: $0 <backup.tgz> [out_dir]" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"
rm -rf "$OUT_DIR"/*

tar -xzf "$BACKUP_FILE" -C "$OUT_DIR"
latest_dir="$(find "$OUT_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
[[ -n "$latest_dir" ]] || { echo "restore_failed=no_extracted_dir"; exit 1; }

[[ -d "$latest_dir/data/tenants" ]] || { echo "restore_failed=missing_data_tenants"; exit 1; }
[[ -d "$latest_dir/licenses" ]] || { echo "restore_failed=missing_licenses"; exit 1; }

python3 - <<PY
from pathlib import Path
import json
root = Path("$latest_dir")
lic_file = root / "licenses" / "licenses.json"
if lic_file.exists():
    data = json.loads(lic_file.read_text())
    print({"licenses": len(data.get("licenses", [])), "payments": len(data.get("payments", []))})
else:
    print({"licenses": 0, "payments": 0, "note": "licenses.json_missing"})
print({"tenant_dirs": len(list((root / "data" / "tenants").glob("*")))})
PY

echo "restore_drill=PASS out=$latest_dir"
