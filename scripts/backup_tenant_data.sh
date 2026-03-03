#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_ROOT="${BACKUP_ROOT:-$ROOT/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
STAMP="$(date +%F_%H%M%S)"
OUT_DIR="$BACKUP_ROOT/$STAMP"

mkdir -p "$OUT_DIR"

copy_if_exists() {
  local src="$1"
  local dst="$2"
  if [[ -e "$src" ]]; then
    mkdir -p "$(dirname "$dst")"
    cp -a "$src" "$dst"
  fi
}

# Core tenant + license data
copy_if_exists "$ROOT/data/tenants" "$OUT_DIR/data/tenants"
copy_if_exists "$ROOT/licenses" "$OUT_DIR/licenses"
copy_if_exists "$ROOT/data/trades.db" "$OUT_DIR/data/trades.db"

# include env snapshot (without secrets redaction - keep backups private)
copy_if_exists "$ROOT/.env" "$OUT_DIR/.env"

( cd "$BACKUP_ROOT" && tar -czf "$STAMP.tgz" "$STAMP" && rm -rf "$STAMP" )

# Retention cleanup
find "$BACKUP_ROOT" -type f -name '*.tgz' -mtime +"$KEEP_DAYS" -delete

echo "backup_created=$BACKUP_ROOT/$STAMP.tgz"
