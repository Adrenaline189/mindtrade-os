# Incident Runbook (MindTrade OS)

## Severity levels
- **SEV-1**: service down / all tenants unable to trade
- **SEV-2**: partial outage (subset tenants blocked unexpectedly)
- **SEV-3**: degraded UX/non-critical admin issue

## Immediate response
1. Freeze risky activity if needed:
   - UI: PANIC button
2. Verify process + health:
```bash
./scripts/status_bot.sh
curl -sS http://127.0.0.1:8000/health
```
3. Check worker/license control plane:
```bash
curl -sS http://127.0.0.1:8000/admin/workers
```

## Common incidents

### A) Service not responding
```bash
./scripts/stop_bot.sh
./scripts/start_bot.sh
sleep 3
curl -sS http://127.0.0.1:8000/health
```
If still failing, inspect `logs/bot.out` and roll back to last known-good tag.

### B) Worker blocked by license gate
- Open `/admin/control`
- If `suspended/expired/license_not_found`: activate/renew/create license
- Start worker again via `/admin/workers/start`

### C) Worker won’t stop cleanly
- Call stop with explicit timeout:
```bash
curl -sS -X POST -F 'tenant_id=<tenant>' -F 'timeout_sec=15' http://127.0.0.1:8000/admin/workers/stop
```
- Validate diagnostics (`stop_timed_out`, `last_stop_latency_sec`)
- Run local regression:
```bash
./venv/bin/python scripts/verify_stop_loop.py
```

### D) Billing enforcement anomaly
- Run:
```bash
./venv/bin/python scripts/smoke_billing_enforcement.py
```
- Verify suspend auto-stops and activate+renew allows restart

## Recovery verification (must pass)
```bash
BASE_URL=http://127.0.0.1:8000 PY=./venv/bin/python ./scripts/final_acceptance_vps.sh
```

## Communication template
- Incident start time
- Impacted scope (tenants/features)
- Mitigation done
- Recovery time
- Preventive action
