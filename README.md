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

Architecture notes and limitations: `docs/multi-tenant-phase1.md`

## Bot service scripts

```bash
./scripts/start_bot.sh
./scripts/status_bot.sh
./scripts/stop_bot.sh
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
