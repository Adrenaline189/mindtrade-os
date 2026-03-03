# Production Release Checklist (v0.3.1 proposal)

## Pre-release
- [ ] `pip install -r requirements.txt`
- [ ] `python3 scripts/smoke_workers.py`
- [ ] `python3 scripts/smoke_multi_tenant_workers.py`
- [ ] `python3 scripts/load_test_tenant_workers.py --tenants 3 --duration 2.5`
- [ ] `python3 scripts/verify_stop_loop.py`
- [ ] `python3 scripts/smoke_billing_enforcement.py`
- [ ] `python3 scripts/smoke_signup_trial_admin_flow.py`
- [ ] `./scripts/final_acceptance_vps.sh` (with service running)
- [ ] `./scripts/backup_tenant_data.sh`
- [ ] `./scripts/restore_drill.sh <latest_backup.tgz>`

## Manual admin checks
- [ ] `/admin/control` shows tenant/email/plan/expiry/api/worker status.
- [ ] Suspend license => worker auto-stops quickly.
- [ ] Activate + renew license => worker start works again.
- [ ] `/admin/workers/start` returns clear license-gate message when blocked.

## Deploy
- [ ] Pull tag `v0.3.0`
- [ ] Restart service
- [ ] Check `/health` => `ok=true`
- [ ] Check `/admin/workers` and `/admin/control`

## Proposed tag notes: `v0.3.1`
- Billing enforcement hardened with periodic reconciler + auto-stop on gate fail.
- Improved worker start/stop API feedback messages.
- New one-page admin control (`/admin/control`) with worker + license actions.
- Added final VPS acceptance script and backup restore drill flow.
- Startup auto-run for default tenant worker (configurable via `AUTO_START_DEFAULT_WORKER`).
- Added signup-to-worker flow smoke (`scripts/smoke_signup_trial_admin_flow.py`).
