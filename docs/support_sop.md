# MindTrade OS Support SOP (v0.3.1)

## 1) Intake triage (first 5 minutes)
1. Confirm customer email + tenant_id.
2. Confirm symptom category:
   - Login/signup
   - License/billing
   - API connection
   - Worker start/stop
   - Runtime trading behavior
3. Capture timestamp + screenshot + exact error text.

## 2) Standard checks
```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/admin/workers
```
- `health.ok=true`
- target tenant appears in worker list or `/admin/control`
- `license_reason` should be `valid` or `default_tenant`

## 3) License/billing issues
- Open `/admin/control` first (single-pane status).
- If suspended/expired:
  - Activate: `POST /admin/licenses/activate`
  - Renew: `POST /admin/licenses/renew`
- Re-test worker start from `/admin/control`.

## 4) API issues
- Ask customer to re-check Binance permissions:
  - Read=ON, Futures=ON, Withdraw=OFF
  - IP whitelist includes VPS IP
- Customer saves keys from dashboard card (API Save).
- Run API test button (`/settings/api/test`).

## 5) Worker issues
- Start: `/admin/workers/start`
- Stop: `/admin/workers/stop` with timeout 15s (or lower for diagnostics)
- Check `stop_timed_out`, `last_stop_latency_sec`, `last_error`.

## 6) Escalation
Escalate when:
- repeated `crashed=true`
- `stop_timed_out=true` persists after restart
- payment webhook duplication/data corruption concerns

Attach:
- `/health` JSON
- `/admin/workers` JSON
- relevant `logs/bot.out` snippet
