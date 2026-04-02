# Go / No-Go Report — 2026-03-04 (Asia/Bangkok)

## Decision
**GO** (with monitored launch)

## Pass/Fail checklist

### Phase A/B acceptance
- [x] VPS final acceptance pass  
  Evidence: `BASE_URL=http://127.0.0.1:8000 PY=./venv/bin/python ./scripts/final_acceptance_vps.sh` => `final_acceptance=PASS`
- [x] Default tenant worker running after deployment  
  Evidence: restart + `/health` returned `running=true`, worker contains `tenant_id=default`.
- [x] Stop-timeout behavior validated under repeated loops  
  Evidence: `./venv/bin/python scripts/verify_stop_loop.py` => `passed=true`, failures `[]`.

### Phase C business readiness
- [x] License/billing enforcement UX + one-page admin control present (`/admin/control`).
- [x] Billing auto-stop enforcement regression pass (`smoke_billing_enforcement.py`).
- [x] Signup -> trial -> admin visibility -> API save/test -> worker start flow pass (`smoke_signup_trial_admin_flow.py`).

### Phase D go-live pack
- [x] Production checklist updated (`docs/production_release_checklist.md`).
- [x] Support SOP completed (`docs/support_sop.md`).
- [x] Incident runbook completed (`docs/incident_runbook.md`).
- [x] Release notes draft completed (`docs/release_notes_v0.3.1.md`).
- [x] Recommended tag prepared: `v0.3.1`.

## Residual risks
1. **Medium** — Live exchange/API dependency may still fail per tenant due to invalid key/IP whitelist mismatch (`-2015`).  
   Mitigation: enforce setup wizard + API test before worker start.
2. **Medium** — Default worker autostart can immediately attempt live loop if config/keys are bad and produce noisy logs.  
   Mitigation: keep monitor + health checks; disable with `AUTO_START_DEFAULT_WORKER=0` if needed.
3. **Low** — Concurrent smoke/load tests use fake runners and do not simulate exchange latency spikes.  
   Mitigation: run canary on production VPS with real API in reduced-risk mode.

## Launch-day exact commands
```bash
cd /Users/adrenaline/trading-bot
./venv/bin/pip install -r requirements.txt

# preflight
./venv/bin/python scripts/smoke_workers.py
./venv/bin/python scripts/smoke_multi_tenant_workers.py
./venv/bin/python scripts/load_test_tenant_workers.py --tenants 3 --duration 2.5
./venv/bin/python scripts/verify_stop_loop.py
./venv/bin/python scripts/smoke_billing_enforcement.py
./venv/bin/python scripts/smoke_signup_trial_admin_flow.py
BASE_URL=http://127.0.0.1:8000 PY=./venv/bin/python ./scripts/final_acceptance_vps.sh

# deploy/restart
./scripts/stop_bot.sh
./scripts/start_bot.sh
sleep 3
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/admin/workers

# backup + drill
KEEP_DAYS=14 ./scripts/backup_tenant_data.sh
./scripts/restore_drill.sh backups/<latest_backup>.tgz
```
