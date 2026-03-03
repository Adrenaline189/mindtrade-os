#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
PY="${PY:-python3}"

cd "$ROOT"

echo "[1/5] health endpoint"
health_json="$(curl -fsS "$BASE_URL/health")"
echo "$health_json" | $PY - <<'PY'
import json,sys
j=json.loads(sys.stdin.read())
assert j.get('ok') is True, j
print({'ok':j.get('ok'),'running':j.get('running'),'workers':len(j.get('workers') or [])})
PY

echo "[2/5] key api endpoints"
for p in \
  "/admin/workers" \
  "/api/summary" \
  "/api/performance" \
  "/api/pnl" \
  "/api/connection"
do
  code="$(curl -sS -o /dev/null -w '%{http_code}' "$BASE_URL$p")"
  [[ "$code" == "200" ]] || { echo "endpoint_failed path=$p code=$code"; exit 1; }
done

echo "[3/5] worker manager smoke"
$PY scripts/smoke_workers.py

echo "[4/5] 3-tenant concurrent worker smoke"
$PY scripts/smoke_multi_tenant_workers.py

echo "[5/5] mini load (3 tenants)"
$PY scripts/load_test_tenant_workers.py --tenants 3 --duration 2.5

echo "final_acceptance=PASS"
