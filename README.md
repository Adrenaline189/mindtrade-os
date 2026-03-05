## MindTrade OS

# trading-bot

## Setup

```bash
cd /Users/adrenaline/trading-bot
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
# fill BINANCE_API_KEY / BINANCE_API_SECRET if using LIVE mode
```

## Run dashboard

```bash
./venv/bin/python main.py
```

Default behavior: app startup auto-starts default tenant worker.
Disable with:

```bash
AUTO_START_DEFAULT_WORKER=0 ./venv/bin/python main.py
```

Open: http://127.0.0.1:8000

## Safety for LIVE

- Default mode is `PAPER`
- LIVE needs both:
  - `MODE=LIVE`
  - `ALLOW_LIVE_ORDERS=True`
- Use Panic button/endpoint to pause trading loop quickly.

## Health check

```bash
curl http://127.0.0.1:8000/health
```

## Multi-tenant (Phase 1)

This project now supports tenant-scoped storage per logged-in user.

- Mapping: `licenses/tenants.json`
- Data root: `data/tenants/<tenant_id>/...`
- Migration script for legacy global files:

```bash
./venv/bin/python scripts/migrate_to_tenants.py
```

Architecture notes and limitations:
- `docs/multi-tenant-phase1.md`
- `docs/multi-tenant-phase2.md`
- `docs/realtime-entry-scoring-v1.md`

### Worker admin APIs + UI (Phase 2)

```bash
curl http://127.0.0.1:8000/admin/workers
curl -X POST -F "tenant_id=default" http://127.0.0.1:8000/admin/workers/start
curl -X POST -F "tenant_id=default" http://127.0.0.1:8000/admin/workers/stop
```

Admin UI:
- `/admin/workers/ui`

License enforcement (Phase 2 hardening):
- Worker start is denied for suspended/expired tenant license.
- Running worker re-checks license every ~30s and auto-stops on invalid license.

Smoke checks:

```bash
./venv/bin/python scripts/smoke_workers.py
./venv/bin/python scripts/smoke_multi_tenant_workers.py
./venv/bin/python scripts/load_test_tenant_workers.py --tenants 3 --duration 2.5
./venv/bin/python scripts/verify_stop_loop.py
./venv/bin/python scripts/smoke_billing_enforcement.py
./venv/bin/python scripts/smoke_signup_trial_admin_flow.py
```

## Bot service scripts

```bash
./scripts/start_bot.sh
./scripts/status_bot.sh
./scripts/stop_bot.sh
```

## Ops scripts (production)

Backup tenant+license data with retention:

```bash
KEEP_DAYS=14 ./scripts/backup_tenant_data.sh
```

Monitor service + health + worker state (Telegram alert on failure):

```bash
SERVICE_NAME=mindtrade.service ./scripts/monitor_service.sh
```

## Telegram alerts (optional)

Add to `.env`:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Alerts sent on: bot start/stop, PAPER/LIVE entry, panic stop, engine errors.

## Product assets

- Landing page mock: `product/site/landing.html`
- Pricing: `product/pricing.md`
- Founder onboarding: `product/onboarding/founder-checklist.md`

## License token v1

Set in `.env`:

```env
REQUIRED_LICENSE_TOKEN=your-secret-license
LICENSE_TOKEN=your-secret-license
```

If `REQUIRED_LICENSE_TOKEN` is set and `LICENSE_TOKEN` mismatches, `/start` will be blocked.

## Signup + Payment Mock

Open `product/site/signup.html` in browser for founder signup + payment mock flow.

## Generate license token

```bash
./scripts/generate_license.py --email customer@example.com --plan pro --days 30 --max-devices 1
```

This writes to `licenses/licenses.json`.
Use generated token in customer `.env` as `LICENSE_TOKEN=...`.

## Dual-channel payments (Binance Pay + PromptPay fallback)

New flows:
- Customer checkout: `/checkout`
- Order detail/instruction: `/checkout/order/{order_id}`
- Customer status page: `/payments/status/{order_id}`
- Binance Pay webhook: `POST /webhook/binance-pay`
- Binance Pay health: `GET /webhook/binance-pay/test`
- Admin payment queue: `/admin/payments`

Backwards compatibility kept:
- Existing `POST /webhook/payment` remains active.
- Existing license admin APIs/pages still work.

### Env vars

Add to `.env`:

```env
# Optional secret used to verify Binance-Pay style callbacks
# Signature expected in header: X-Signature (hex hmac sha256 of raw body)
BINANCE_PAY_WEBHOOK_SECRET=replace-with-strong-secret

# legacy endpoint still supported
PAYMENT_WEBHOOK_SECRET=optional-legacy-secret
```

### Example webhook payload

```json
{
  "event_id": "evt_20260304_001",
  "order_id": "ord_20260304153001_ab12cd34",
  "status": "paid"
}
```

### Payment smoke test

```bash
./venv/bin/python -m unittest tests/test_payment_flow_smoke.py -v
```

## Windows one-click installer (beta)

Files:
- `installer/windows/setup_oneclick.bat`
- `installer/windows/bootstrap.ps1`
- `installer/windows/first_run_wizard.ps1`

Usage on Windows:
1. Copy project folder to target machine.
2. Run `installer\windows\setup_oneclick.bat` as Administrator.
3. Open `http://127.0.0.1:8000`
4. Run first-run wizard to set API keys:
   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\TradingBot\installer\windows\first_run_wizard.ps1" -InstallDir "$env:USERPROFILE\TradingBot"`

### Extra installer utilities
- Quick menu: `installer/windows/gui/welcome_menu.bat`
- Uninstaller: `installer/windows/uninstall.ps1`
- Distribution zip: `dist/TradingBot-Windows-Beta.zip`
