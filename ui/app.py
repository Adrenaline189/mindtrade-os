import csv
import re
import threading
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, Header, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from bot.config_runtime import RUNTIME_CONFIG
from bot.engine import run_engine, exchange, apply_leverage_settings
from bot.state import bot_state
from bot.license import license_ok
from bot.license_service import issue_license, list_licenses, record_payment, has_payment_event, set_license_active, delete_license, renew_license, find_licenses, list_payments_for_license
from bot.auth_service import create_user, verify_user
from bot.runtime_store import load_runtime_config, save_runtime_config

load_dotenv()

app = FastAPI(title="MindTrade OS")
app.add_middleware(SessionMiddleware, secret_key=__import__('os').getenv('SESSION_SECRET', 'mindtrade-dev-secret'))
BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "ui" / "templates"))
TRADE_CSV = BASE_DIR / "data" / "paper_trades.csv"

# Load persisted runtime config first
load_runtime_config()

# Force LIVE-only operation
RUNTIME_CONFIG["MODE"] = "LIVE"
RUNTIME_CONFIG["ALLOW_LIVE_ORDERS"] = True


def load_trades(limit: int | None = None):
    if not TRADE_CSV.exists():
        return []
    with TRADE_CSV.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if limit:
        return rows[-limit:]
    return rows




def fetch_open_positions():
    out = []
    try:
        positions = exchange.fetch_positions(RUNTIME_CONFIG.get('SYMBOLS', []))
        for p in positions:
            contracts = float(p.get('contracts') or 0)
            if contracts == 0:
                continue
            out.append({
                'symbol': p.get('symbol'),
                'side': p.get('side'),
                'contracts': contracts,
                'entryPrice': p.get('entryPrice'),
                'markPrice': p.get('markPrice'),
                'unrealizedPnl': p.get('unrealizedPnl'),
            })
    except Exception:
        pass
    return out

def trade_summary(trades):
    entry_keys = {"ENTRY", "ENTRY_PAPER", "ENTRY_LIVE"}
    tp_keys = {"PAPER_TP1", "PAPER_TP2"}
    sl_keys = {"PAPER_SL"}

    counts = Counter(t.get("result", "") for t in trades)
    entries = sum(counts[k] for k in entry_keys)
    tps = sum(counts[k] for k in tp_keys)
    sls = sum(counts[k] for k in sl_keys)

    r_values = []
    for t in trades:
        note = str(t.get("note", ""))
        if note.startswith("r="):
            try:
                r_values.append(float(note.replace("r=", "")))
            except Exception:
                pass

    avg_r = round(sum(r_values) / len(r_values), 3) if r_values else 0.0
    total_r = round(sum(r_values), 3) if r_values else 0.0
    win_rate = round((tps / max(tps + sls, 1)) * 100, 2)

    by_symbol = Counter(t.get("symbol", "-") for t in trades if t.get("symbol"))

    return {
        "entries": entries,
        "tp_hits": tps,
        "sl_hits": sls,
        "win_rate": win_rate,
        "avg_r": avg_r,
        "total_r": total_r,
        "blocked": counts.get("BLOCKED", 0),
        "skips": counts.get("SKIP", 0),
        "by_symbol": dict(by_symbol),
    }


@app.get("/")
def dashboard(request: Request):
    trades = load_trades(limit=300)
    summary = trade_summary(trades)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "cfg": RUNTIME_CONFIG,
            "running": bot_state["running"],
            "trades": trades[-50:],
            "summary": summary,
        },
    )


@app.get('/health')
def health():
    lic_ok, lic_reason = license_ok()
    return {
        'ok': True,
        'running': bot_state['running'],
        'mode': RUNTIME_CONFIG['MODE'],
        'allow_live': RUNTIME_CONFIG['ALLOW_LIVE_ORDERS'],
        'panic_stop': RUNTIME_CONFIG['PANIC_STOP'],
        'symbols': RUNTIME_CONFIG.get('SYMBOLS', []),
        'license_ok': lic_ok,
        'license_reason': lic_reason,
    }


@app.get('/api/summary')
def api_summary(symbol: str | None = None):
    trades = load_trades(limit=500)
    if symbol:
        trades = [t for t in trades if t.get('symbol') == symbol]
    blocked_reasons = Counter((t.get('note') or '').split(':')[0] for t in trades if t.get('result')=='BLOCKED')
    positions = fetch_open_positions()
    exposure = sum(abs(float(p.get('unrealizedPnl') or 0)) for p in positions)
    return JSONResponse({'summary': trade_summary(trades), 'running': bot_state['running'], 'mode': RUNTIME_CONFIG['MODE'], 'symbol': symbol or 'ALL', 'blocked_reasons': dict(blocked_reasons), 'open_positions_count': len(positions), 'open_positions': positions, 'exposure_abs_upnl': round(exposure,4)})


@app.get('/api/events')
def api_events(limit: int = 200):
    trades = load_trades(limit=limit)
    return JSONResponse({'events': trades})


@app.get('/api/chart')
def api_chart(limit: int = 200, symbol: str | None = None):
    # Prefer Binance OHLCV for real multi-symbol chart
    symbols = [symbol] if symbol else list(RUNTIME_CONFIG.get('SYMBOLS', []))
    symbols = symbols[:3] if symbols else ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

    try:
        exchange.load_markets()
        raw = {}
        ts_union = set()
        for sym in symbols:
            ohlcv = exchange.fetch_ohlcv(sym, timeframe='5m', limit=limit)
            raw[sym] = ohlcv
            for row in ohlcv:
                ts_union.add(int(row[0]))

        ts_sorted = sorted(ts_union)
        labels = [__import__('datetime').datetime.utcfromtimestamp(t/1000).strftime('%H:%M') for t in ts_sorted]

        series = {}
        for sym in symbols:
            idx = {int(r[0]): float(r[4]) for r in raw.get(sym, [])}
            series[sym] = [idx.get(t) for t in ts_sorted]

        return JSONResponse({'labels': labels, 'series': series, 'source': 'binance_ohlcv'})
    except Exception:
        # fallback to local trade timeline
        trades = load_trades(limit=limit)
        if symbol:
            trades = [t for t in trades if t.get('symbol') == symbol]
        labels, prices, markers = [], [], []
        for t in trades:
            labels.append(t.get('time'))
            try:
                prices.append(float(t.get('close') or 0))
            except Exception:
                prices.append(None)
            markers.append(t.get('result'))
        return JSONResponse({'labels': labels, 'prices': prices, 'markers': markers, 'source': 'local_trades'})




@app.get('/api/performance')
def api_performance():
    trades = load_trades(limit=5000)
    r_values = []
    for t in trades:
        note = str(t.get('note',''))
        if note.startswith('r='):
            try:
                r_values.append(float(note[2:]))
            except Exception:
                pass

    total_r = sum(r_values) if r_values else 0.0
    avg_r = (total_r / len(r_values)) if r_values else 0.0

    # max drawdown in R space
    eq = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in r_values:
        eq += r
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd

    return JSONResponse({
        'realized_trades': len(r_values),
        'total_r': round(total_r, 4),
        'avg_r': round(avg_r, 4),
        'max_dd_r': round(max_dd, 4),
    })

@app.post("/start")
def start_bot():
    lic_ok, _ = license_ok()
    if not lic_ok:
        return RedirectResponse("/?err=license", status_code=303)
    if not bot_state["running"]:
        bot_state["running"] = True
        threading.Thread(target=run_engine, daemon=True).start()
    return RedirectResponse("/", status_code=303)


@app.post("/stop")
def stop_bot():
    bot_state["running"] = False
    return RedirectResponse("/", status_code=303)


@app.post("/panic")
def panic_stop():
    RUNTIME_CONFIG["PANIC_STOP"] = True
    return RedirectResponse("/", status_code=303)


@app.post("/unpanic")
def unpanic_stop():
    RUNTIME_CONFIG["PANIC_STOP"] = False
    return RedirectResponse("/", status_code=303)


@app.post("/update")
def update_config(
    rsi_min: int = Form(...),
    rsi_max: int = Form(...),
    gz: float = Form(...),
    risk: float = Form(...),
    leverage: int = Form(5),
    margin_mode: str = Form("cross"),
    leverage_by_symbol: str = Form(""),
    mode: str = Form("LIVE"),
    allow_live: str = Form("true"),
    max_trades: int = Form(3),
    cooldown_minutes: int = Form(60),
    daily_loss_cap_pct: float = Form(3.0),
    symbols: str = Form("BTC/USDT,ETH/USDT,SOL/USDT"),
):
    if rsi_min >= rsi_max:
        return RedirectResponse("/", status_code=303)
    if risk <= 0 or leverage < 1 or leverage > 125:
        return RedirectResponse("/", status_code=303)
    if margin_mode not in {"cross", "isolated"}:
        return RedirectResponse("/", status_code=303)
    if max_trades < 1 or cooldown_minutes < 0 or daily_loss_cap_pct <= 0:
        return RedirectResponse("/", status_code=303)

    RUNTIME_CONFIG["RSI_MIN"] = rsi_min
    RUNTIME_CONFIG["RSI_MAX"] = rsi_max
    RUNTIME_CONFIG["GOLDEN_ZONE_DISTANCE"] = gz
    RUNTIME_CONFIG["RISK_PER_TRADE"] = risk
    RUNTIME_CONFIG["LEVERAGE"] = leverage
    RUNTIME_CONFIG["MARGIN_MODE"] = margin_mode
    RUNTIME_CONFIG["MODE"] = "LIVE"
    RUNTIME_CONFIG["ALLOW_LIVE_ORDERS"] = True
    RUNTIME_CONFIG["MAX_TRADES_PER_DAY"] = max_trades
    RUNTIME_CONFIG["COOLDOWN_MINUTES"] = cooldown_minutes
    RUNTIME_CONFIG["DAILY_LOSS_CAP_PCT"] = daily_loss_cap_pct

    parsed = [x.strip().upper() for x in symbols.split(',') if x.strip()]
    # normalize separator
    parsed = [x.replace('-', '/').replace(' ', '') for x in parsed]
    valid = [x for x in parsed if '/' in x]
    if valid:
        RUNTIME_CONFIG["SYMBOLS"] = valid

    # leverage map format: BTC/USDT:5,ETH/USDT:3
    lev_map = {}
    raw_map = leverage_by_symbol.strip()
    if raw_map:
        for pair in raw_map.split(','):
            if ':' not in pair:
                continue
            sym, lv = pair.split(':', 1)
            sym = sym.strip().upper().replace('-', '/').replace(' ', '')
            try:
                lv_int = int(lv.strip())
                if 1 <= lv_int <= 125 and '/' in sym:
                    lev_map[sym] = lv_int
            except Exception:
                continue
    # keep leverage map aligned with selected symbols
    valid_set = set(RUNTIME_CONFIG.get("SYMBOLS", []))
    if lev_map:
        RUNTIME_CONFIG["LEVERAGE_BY_SYMBOL"] = {k: v for k, v in lev_map.items() if k in valid_set}
    else:
        # if user leaves field empty, clear per-symbol override and use default leverage
        RUNTIME_CONFIG["LEVERAGE_BY_SYMBOL"] = {}

    # always prune stale symbol overrides
    if RUNTIME_CONFIG.get("LEVERAGE_BY_SYMBOL"):
        RUNTIME_CONFIG["LEVERAGE_BY_SYMBOL"] = {
            k: v for k, v in RUNTIME_CONFIG["LEVERAGE_BY_SYMBOL"].items() if k in valid_set
        }

    # persist runtime settings
    try:
        save_runtime_config()
    except Exception:
        pass

    # apply leverage immediately when bot is already running in LIVE mode
    try:
        if bot_state.get("running") and RUNTIME_CONFIG.get("MODE") == "LIVE" and RUNTIME_CONFIG.get("ALLOW_LIVE_ORDERS"):
            apply_leverage_settings()
    except Exception:
        pass

    return RedirectResponse("/", status_code=303)


@app.get('/admin/licenses')
def admin_licenses(request: Request, q: str = ''):
    rows = find_licenses(q, 500) if q else list_licenses(500)
    return templates.TemplateResponse('licenses_admin.html', {'request': request, 'licenses': rows, 'q': q})


@app.post('/admin/licenses/create')
def admin_create_license(email: str = Form(...), plan: str = Form('starter'), days: int = Form(30), max_devices: int = Form(1)):
    issue_license(email=email, plan=plan, days=days, max_devices=max_devices)
    return RedirectResponse('/admin/licenses', status_code=303)


@app.post('/webhook/payment')
def payment_webhook(payload: dict, x_signature: str | None = Header(default=None)):
    secret = __import__('os').getenv('PAYMENT_WEBHOOK_SECRET', '').strip()
    if secret and x_signature != secret:
        raise HTTPException(status_code=401, detail='invalid_signature')

    event_id = str(payload.get('event_id') or '')
    if not event_id:
        raise HTTPException(status_code=400, detail='missing_event_id')
    if has_payment_event(event_id):
        return JSONResponse({'ok': True, 'duplicate': True})

    record_payment(payload)

    status = str(payload.get('status', '')).lower()
    if status in {'paid','success','succeeded'}:
        email = payload.get('email')
        plan = payload.get('plan', 'starter')
        if email:
            rec = issue_license(email=email, plan=plan, days=30 if plan=='starter' else 30, max_devices=1 if plan=='starter' else 2)
            return JSONResponse({'ok': True, 'license_token': rec['license_token'], 'plan': rec['plan']})

    return JSONResponse({'ok': True, 'processed': True})


@app.get('/webhook/payment/test')
def webhook_test():
    return PlainTextResponse('payment webhook ready')


@app.get('/api/connection')
def api_connection():
    ok = True
    err = ''
    try:
        exchange.fetch_ticker(RUNTIME_CONFIG.get('SYMBOLS', ['BTC/USDT'])[0])
    except Exception as e:
        ok = False
        err = str(e)
    return JSONResponse({'ok': ok, 'error': err[:180]})


@app.get('/api/open-positions')
def api_open_positions():
    return JSONResponse({'positions': fetch_open_positions()})


@app.get('/api/leverage')
def api_leverage():
    symbols = RUNTIME_CONFIG.get('SYMBOLS', [])
    default_lev = int(RUNTIME_CONFIG.get('LEVERAGE', 5))
    margin_mode = str(RUNTIME_CONFIG.get('MARGIN_MODE', 'cross'))
    lev_map = RUNTIME_CONFIG.get('LEVERAGE_BY_SYMBOL', {}) or {}

    rows = []
    for sym in symbols:
        rows.append({
            'symbol': sym,
            'leverage': int(lev_map.get(sym, default_lev)),
            'margin_mode': margin_mode,
        })

    return JSONResponse({'rows': rows, 'default_leverage': default_lev, 'margin_mode': margin_mode})


@app.post('/admin/licenses/suspend')
def admin_suspend_license(token: str = Form(...)):
    set_license_active(token, False)
    return RedirectResponse('/admin/licenses', status_code=303)


@app.post('/admin/licenses/activate')
def admin_activate_license(token: str = Form(...)):
    set_license_active(token, True)
    return RedirectResponse('/admin/licenses', status_code=303)


@app.post('/admin/licenses/delete')
def admin_delete_license(token: str = Form(...)):
    delete_license(token)
    return RedirectResponse('/admin/licenses', status_code=303)


@app.post('/admin/licenses/renew')
def admin_renew_license(token: str = Form(...), days: int = Form(30)):
    renew_license(token, days)
    return RedirectResponse('/admin/licenses', status_code=303)


@app.post('/admin/licenses/send-token')
def admin_send_token(token: str = Form(...), target_chat_id: str = Form(...)):
    import os, urllib.parse, urllib.request
    from pathlib import Path
    import json

    # load env quickly
    env_path = BASE_DIR / '.env'
    vals = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if '=' in line and not line.strip().startswith('#'):
                k,v=line.split('=',1); vals[k]=v

    bot_token = vals.get('TELEGRAM_BOT_TOKEN','').strip()
    if not bot_token:
        return RedirectResponse('/admin/licenses?err=no_tg', status_code=303)

    # find license
    data_path = BASE_DIR / 'licenses' / 'licenses.json'
    if not data_path.exists():
        return RedirectResponse('/admin/licenses?err=no_db', status_code=303)
    db = json.loads(data_path.read_text())
    rec = next((x for x in db.get('licenses',[]) if x.get('license_token')==token), None)
    if not rec:
        return RedirectResponse('/admin/licenses?err=no_license', status_code=303)

    msg = f"MindTrade OS License\nEmail: {rec.get('email')}\nPlan: {rec.get('plan')}\nToken: {rec.get('license_token')}\nExpires: {rec.get('expires_at')}"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage?" + urllib.parse.urlencode({'chat_id': target_chat_id, 'text': msg})
    try:
        urllib.request.urlopen(url, timeout=10).read()
    except Exception:
        return RedirectResponse('/admin/licenses?err=send_fail', status_code=303)

    return RedirectResponse('/admin/licenses?ok=sent', status_code=303)


@app.get('/profile')
def profile_page(request: Request, token: str = ''):
    from pathlib import Path
    import json
    from datetime import datetime, timezone

    db_path = BASE_DIR / 'licenses' / 'licenses.json'
    rec = None
    days_left = None
    expiry_state = 'unknown'
    payments = []

    user_email = (request.session.get('user_email') or '').strip().lower()
    if db_path.exists():
        db = json.loads(db_path.read_text())
        if token:
            rec = next((x for x in db.get('licenses',[]) if x.get('license_token')==token), None)
        elif user_email:
            rec = next((x for x in db.get('licenses',[]) if (x.get('email') or '').strip().lower()==user_email), None)

    if rec:
        exp_raw = rec.get('expires_at')
        try:
            exp = datetime.fromisoformat(str(exp_raw))
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            delta_days = int((exp - now).total_seconds() // 86400)
            days_left = delta_days
            if delta_days < 0:
                expiry_state = 'expired'
            elif delta_days <= 7:
                expiry_state = 'warning'
            else:
                expiry_state = 'ok'
        except Exception:
            expiry_state = 'unknown'

        payments = list_payments_for_license(rec.get('license_token',''), limit=20)

    announcement = "🚀 Welcome to MindTrade OS — New: profile expiry badge + payment history"
    return templates.TemplateResponse('profile.html', {
        'request': request,
        'rec': rec,
        'token': token,
        'announcement': announcement,
        'days_left': days_left,
        'expiry_state': expiry_state,
        'payments': payments,
        'user_email': request.session.get('user_email',''),
    })


@app.post('/profile/renew')
def profile_renew(token: str = Form(...), days: int = Form(30)):
    renew_license(token, days)
    return RedirectResponse(f'/profile?token={token}', status_code=303)


@app.get('/landing')
def landing_page(request: Request):
    return templates.TemplateResponse('landing.html', {
        'request': request,
        'product_name': 'MindTrade OS',
        'tagline': 'AI Trading Operating System for serious solo traders',
    })


@app.get('/auth/login')
def auth_login_page(request: Request, err: str = ''):
    return templates.TemplateResponse('login.html', {'request': request, 'err': err})


@app.post('/auth/login')
def auth_login(request: Request, email: str = Form(...), password: str = Form(...)):
    if not verify_user(email, password):
        return RedirectResponse('/auth/login?err=invalid', status_code=303)
    request.session['user_email'] = email.strip().lower()
    return RedirectResponse('/profile', status_code=303)


@app.get('/auth/signup')
def auth_signup_page(request: Request, err: str = ''):
    return templates.TemplateResponse('signup.html', {'request': request, 'err': err})


@app.post('/auth/signup')
def auth_signup(request: Request, email: str = Form(...), password: str = Form(...)):
    ok, reason = create_user(email, password)
    if not ok:
        return RedirectResponse(f'/auth/signup?err={reason}', status_code=303)
    request.session['user_email'] = email.strip().lower()
    return RedirectResponse('/profile', status_code=303)


@app.get('/auth/logout')
def auth_logout(request: Request):
    request.session.clear()
    return RedirectResponse('/auth/login', status_code=303)


@app.get('/setup')
def setup_page(request: Request):
    return templates.TemplateResponse('setup_wizard.html', {
        'request': request,
        'vps_ip': '185.230.138.51',
    })


BOT_ONLY_SCOPE_MSG = "ขออภัยค่ะ ระบบนี้ตอบเฉพาะการใช้งาน MindTrade OS และบอทเทรดเท่านั้นค่ะ"


def _help_answer(q: str) -> str:
    text = (q or '').strip().lower()
    if not text:
        return "พิมพ์คำถามเกี่ยวกับการใช้งานบอทได้เลยค่ะ เช่น leverage, cooldown, api key, start/stop"

    out_of_scope = ['หวย', 'ฟุตบอล', 'หนัง', 'เพลง', 'การเมือง', 'สุขภาพ', 'อาหาร', 'ท่องเที่ยว']
    if any(k in text for k in out_of_scope):
        return BOT_ONLY_SCOPE_MSG

    rules = [
        (['leverage by symbol', 'เลเวอเรจแยก', 'leverage'], "Leverage (x) คือค่าเริ่มต้นทุกเหรียญ ส่วน Leverage by symbol คือค่าแยกรายเหรียญที่มีลำดับความสำคัญสูงกว่า\nตัวอย่าง: BTC/USDT:5,ETH/USDT:3"),
        (['cooldown', 'พักไม้', 'cooldown minutes'], "Cooldown minutes คือเวลาพักหลังเข้าไม้ก่อนเข้าไม้ใหม่ (นาที)\nเช่น 120 = เข้าไม้แล้วพัก 2 ชั่วโมงก่อนสัญญาณใหม่"),
        (['api', 'binance', '-2015', 'permission', 'whitelist'], "การตั้ง Binance API ที่ถูกต้อง:\n1) Enable Reading ON\n2) Enable Futures ON\n3) Withdraw OFF\n4) ถ้าเปิด IP restriction ให้ whitelist IP VPS: 185.230.138.51\n5) ถ้าเจอ -2015 ให้เช็ก key/ip/permission อีกครั้ง"),
        (['start', 'เริ่มบอท', 'รันบอท'], "เริ่มบอทจาก Dashboard ด้วยปุ่ม START ได้เลยค่ะ และเช็กที่ /health ว่า running=true"),
        (['stop', 'หยุดบอท', 'panic'], "หยุดบอทปกติใช้ STOP\nถ้าต้องหยุดฉุกเฉินให้ใช้ PANIC"),
        (['risk', 'risk per trade', 'ความเสี่ยง'], "Risk / Trade คือความเสี่ยงต่อไม้\nตัวอย่าง 0.005 = 0.5% ต่อไม้ แนะนำเริ่มที่ 0.005-0.01"),
        (['หมดอายุ', 'expire', 'license', 'สมาชิก'], "ตรวจสอบสิทธิ์สมาชิกได้ที่หน้า Profile\nระบบจะแสดง plan, วันหมดอายุ และ days left พร้อมปุ่มต่ออายุ"),
    ]
    for keys, ans in rules:
        if any(k in text for k in keys):
            return ans

    return "น้องมายด์ตอบได้เฉพาะคู่มือใช้งาน MindTrade OS ค่ะ\nลองถามแบบนี้ได้: leverage ต่างกันยังไง, cooldown คืออะไร, ตั้งค่า API Binance ยังไง, วิธี start/stop บอท"


@app.get('/help-chat')
def help_chat_page(request: Request):
    return templates.TemplateResponse('help_chat.html', {'request': request})


@app.post('/api/help-chat')
def api_help_chat(payload: dict):
    q = str(payload.get('question') or '')
    ans = _help_answer(q)
    return JSONResponse({'ok': True, 'answer': ans})
