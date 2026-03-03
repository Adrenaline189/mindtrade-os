# MindTrade OS Release Notes (Draft)

## Recommended tag
`v0.3.1`

## Highlights
- Added startup auto-run for default tenant worker (`AUTO_START_DEFAULT_WORKER`, default ON).
- Fixed `scripts/final_acceptance_vps.sh` health JSON parsing to prevent false failures.
- Added full business-flow smoke test:
  - `scripts/smoke_signup_trial_admin_flow.py`
  - validates signup -> trial license visibility -> admin control visibility -> API save/test -> worker start
- Strengthened go-live docs:
  - Support SOP
  - Incident runbook
  - Go/No-Go report

## Validation executed
- `scripts/final_acceptance_vps.sh` => PASS
- `scripts/verify_stop_loop.py` => PASS (50 loops)
- `scripts/smoke_billing_enforcement.py` => PASS
- `scripts/smoke_signup_trial_admin_flow.py` => PASS

## Upgrade notes
- No data migration required.
- Optional env:
  - `AUTO_START_DEFAULT_WORKER=0` to disable startup worker autostart.
