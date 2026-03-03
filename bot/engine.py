import csv
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import ccxt
import pandas as pd
from dotenv import load_dotenv

from bot.alerts import send_telegram_alert
from bot.config import EQUITY_USDT, MAX_SL_PERCENT
from bot.config_runtime import RUNTIME_CONFIG
from bot.indicators import ema, rsi
from bot.paths import get_tenant_paths
from bot.state import bot_state
from bot.storage import count_entries_today_utc, init_db, log_trade
from bot.tenant_context import default_tenant_id, tenant_scope

load_dotenv()

TIMEFRAME = "1h"
LOOP_INTERVAL = 30
BASE_DIR = Path(__file__).resolve().parents[1]
ACTIVE_TENANT_ID = default_tenant_id()


def set_active_tenant(tenant_id: str):
    global ACTIVE_TENANT_ID
    ACTIVE_TENANT_ID = (tenant_id or default_tenant_id()).strip()


def _data_file() -> Path:
    return get_tenant_paths(ACTIVE_TENANT_ID)["trades_csv"]

exchange = ccxt.binance(
    {
        "apiKey": os.getenv("BINANCE_API_KEY"),
        "secret": os.getenv("BINANCE_API_SECRET"),
        "enableRateLimit": True,
        "options": {"defaultType": "future"},
    }
)


def notify(msg: str, force: bool = False):
    print(msg)
    if force or RUNTIME_CONFIG.get("TELEGRAM_ALERTS", True):
        send_telegram_alert(msg)


def notify_trade(symbol: str, result: str, note: str = ""):
    if result in {"ENTRY_PAPER", "ENTRY_LIVE"} and RUNTIME_CONFIG.get("ALERT_ON_ENTRY", True):
        notify(f"📣 {result} {symbol} | {note}")
    elif result == "BLOCKED" and RUNTIME_CONFIG.get("ALERT_ON_BLOCKED", False):
        notify(f"🚧 BLOCKED {symbol} | {note}")


def log_to_csv(row: dict):
    data_file = _data_file()
    data_file.parent.mkdir(parents=True, exist_ok=True)
    file_exists = data_file.exists()
    with data_file.open(mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def fetch_ohlcv_df(symbol: str, limit=300):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=limit)
    return pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])


def compute_adx(df: pd.DataFrame, period: int = 14):
    high = pd.to_numeric(df["high"], errors="coerce").astype(float)
    low = pd.to_numeric(df["low"], errors="coerce").astype(float)
    close = pd.to_numeric(df["close"], errors="coerce").astype(float)

    up = high.diff()
    down = -low.diff()

    plus_dm = up.where((up > down) & (up > 0), 0.0).astype(float)
    minus_dm = down.where((down > up) & (down > 0), 0.0).astype(float)

    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    tr = pd.to_numeric(tr, errors="coerce").astype(float)

    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100.0 * (plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr)
    minus_di = 100.0 * (minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr)

    denom = (plus_di + minus_di).replace(0, float("nan"))
    dx = ((plus_di - minus_di).abs() / denom) * 100.0
    dx = pd.to_numeric(dx, errors="coerce").astype(float).fillna(0.0)

    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    return adx, atr


def in_news_blackout(now_utc: datetime) -> bool:
    hhmm = now_utc.strftime("%H:%M")
    for w in RUNTIME_CONFIG.get("NEWS_BLACKOUT_WINDOWS_UTC", []):
        try:
            s, e = w.split("-")
            if s <= hhmm <= e:
                return True
        except Exception:
            pass
    return False


def analyze_market(df):
    close = df["close"]
    df["ema50"] = ema(close, 50)
    df["ema200"] = ema(close, 200)
    df["rsi"] = rsi(close, 14)
    df["adx"], df["atr"] = compute_adx(df, 14)
    last = df.iloc[-2]

    bias = "NO TRADE"
    if last["ema50"] > last["ema200"] and last["close"] > last["ema200"]:
        bias = "LONG"
    elif last["ema50"] < last["ema200"] and last["close"] < last["ema200"]:
        bias = "SHORT"

    distance = abs((last["close"] - last["ema50"]) / last["ema50"]) * 100
    atr_pct = float(last["atr"] / last["close"] * 100) if last["close"] else 0.0

    golden_zone = (
        bias in ["LONG", "SHORT"]
        and distance <= RUNTIME_CONFIG["GOLDEN_ZONE_DISTANCE"]
        and RUNTIME_CONFIG["RSI_MIN"] <= last["rsi"] <= RUNTIME_CONFIG["RSI_MAX"]
    )
    quality_ok = (
        float(last["adx"]) >= float(RUNTIME_CONFIG.get("ADX_MIN", 18))
        and float(RUNTIME_CONFIG.get("ATR_PCT_MIN", 0.25)) <= atr_pct <= float(RUNTIME_CONFIG.get("ATR_PCT_MAX", 3.5))
    )

    return {
        "time": datetime.utcfromtimestamp(last["timestamp"] / 1000),
        "close": float(last["close"]),
        "rsi": float(last["rsi"]),
        "adx": float(last["adx"]),
        "atr_pct": atr_pct,
        "bias": bias,
        "golden_zone": golden_zone,
        "quality_ok": quality_ok,
    }


def calc_trade(df, analysis):
    entry = analysis["close"]
    bias = analysis["bias"]
    if bias == "LONG":
        sl = df["low"].iloc[-12:-2].min()
        sl_pct = (entry - sl) / entry * 100
    elif bias == "SHORT":
        sl = df["high"].iloc[-12:-2].max()
        sl_pct = (sl - entry) / entry * 100
    else:
        return None
    if sl_pct <= 0 or sl_pct > MAX_SL_PERCENT:
        return None
    risk_money = EQUITY_USDT * RUNTIME_CONFIG["RISK_PER_TRADE"]
    size = risk_money / (sl_pct / 100)
    if size < RUNTIME_CONFIG.get("MIN_NOTIONAL_USDT", 10):
        return None
    return {
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp1": round(entry * (1 + sl_pct / 100), 2) if bias == "LONG" else round(entry * (1 - sl_pct / 100), 2),
        "tp2": round(entry * (1 + (sl_pct * 3) / 100), 2) if bias == "LONG" else round(entry * (1 - (sl_pct * 3) / 100), 2),
        "size": round(size, 3),
    }


def can_enter_trade_now(state=None):
    state = state or bot_state
    if count_entries_today_utc() >= int(RUNTIME_CONFIG.get("MAX_TRADES_PER_DAY", 3)):
        return False, "daily_limit"
    cu = state.get("cooldown_until")
    if cu and datetime.utcnow() < cu:
        return False, "cooldown"
    if in_news_blackout(datetime.utcnow()):
        return False, "news_blackout"
    return True, "ok"


def touch_cooldown(state=None):
    state = state or bot_state
    state["cooldown_until"] = datetime.utcnow() + timedelta(minutes=int(RUNTIME_CONFIG.get("COOLDOWN_MINUTES", 60)))




def normalize_order_amount(symbol: str, amount: float):
    """Clamp + precision-normalize order amount to exchange market limits."""
    try:
        exchange.load_markets()
    except Exception:
        pass

    market = exchange.market(symbol)
    limits = (market.get('limits') or {}).get('amount') or {}
    min_amt = limits.get('min')
    max_amt = limits.get('max')

    amt = float(amount)
    changed = False

    if max_amt is not None and amt > float(max_amt):
        amt = float(max_amt)
        changed = True

    if min_amt is not None and amt < float(min_amt):
        return None, f'below_min_qty:{amt}<{min_amt}'

    try:
        amt = float(exchange.amount_to_precision(symbol, amt))
    except Exception:
        pass

    if amt <= 0:
        return None, 'non_positive_qty'

    if min_amt is not None and amt < float(min_amt):
        amt = float(min_amt)
        changed = True
        try:
            amt = float(exchange.amount_to_precision(symbol, amt))
        except Exception:
            pass

    return amt, ('clamped' if changed else '')


def send_live_order(symbol: str, side: str, trade):
    if RUNTIME_CONFIG["MODE"] != "LIVE" or not RUNTIME_CONFIG["ALLOW_LIVE_ORDERS"]:
        return "blocked"
    order_side = "buy" if side == "LONG" else "sell"
    close_side = "sell" if side == "LONG" else "buy"

    raw_size = float(trade["size"])
    size, reason = normalize_order_amount(symbol, raw_size)
    if size is None:
        notify(f"⚠️ order blocked {symbol}: invalid qty ({reason})")
        return "blocked"
    if reason:
        notify(f"⚠️ qty adjusted {symbol}: {raw_size} -> {size}")

    exchange.create_order(symbol, "MARKET", order_side, size)
    exchange.create_order(symbol, "STOP_MARKET", close_side, size, params={"stopPrice": trade["sl"], "reduceOnly": True})

    # TP split with safe fallback to single TP if split amounts are invalid
    half_target = size / 2
    half, _ = normalize_order_amount(symbol, half_target)
    rest = None
    if half is not None:
        rest, _ = normalize_order_amount(symbol, max(size - half, 0))

    if half is not None and rest is not None and rest > 0:
        exchange.create_order(symbol, "TAKE_PROFIT_MARKET", close_side, half, params={"stopPrice": trade["tp1"], "reduceOnly": True})
        exchange.create_order(symbol, "TAKE_PROFIT_MARKET", close_side, rest, params={"stopPrice": trade["tp2"], "reduceOnly": True})
    else:
        notify(f"⚠️ TP split fallback {symbol}: using single TP order")
        exchange.create_order(symbol, "TAKE_PROFIT_MARKET", close_side, size, params={"stopPrice": trade["tp1"], "reduceOnly": True})

    return "live_sent"




def apply_leverage_settings():
    default_lev = int(RUNTIME_CONFIG.get("LEVERAGE", 5))
    margin_mode = str(RUNTIME_CONFIG.get("MARGIN_MODE", "cross")).lower()
    lev_map = RUNTIME_CONFIG.get("LEVERAGE_BY_SYMBOL", {}) or {}

    try:
        exchange.load_markets()
    except Exception as e:
        notify(f"⚠️ load_markets failed before leverage set: {e}")

    for symbol in RUNTIME_CONFIG.get("SYMBOLS", ["BTC/USDT"]):
        try:
            lev = int(lev_map.get(symbol, default_lev))
            market = exchange.market(symbol)
            exchange.set_leverage(lev, market["id"], params={"marginMode": margin_mode})
            notify(f"⚙️ Leverage set {symbol} = {lev}x ({margin_mode})")
        except Exception as e:
            notify(f"⚠️ leverage set failed {symbol}: {e}")


def run_engine_for_tenant(tenant_id: str, stop_event=None, state=None, isolation_lock=None, license_gate=None):
    state = state or bot_state
    with tenant_scope(tenant_id):
        set_active_tenant(tenant_id)
        init_db()
        notify(f"🚀 Trading bot started (tenant={tenant_id})")

    leverage_applied = False
    last_license_check_at = 0.0
    while True:
        if stop_event is not None and stop_event.is_set():
            break
        if stop_event is None and not state.get("running", False):
            break
        try:
            now_ts = time.time()
            if license_gate is not None and (now_ts - last_license_check_at >= 30):
                last_license_check_at = now_ts
                lic_ok, lic_reason = license_gate(tenant_id)
                state["license_ok"] = bool(lic_ok)
                state["license_reason"] = lic_reason
                if not lic_ok:
                    notify(f"⛔ worker auto-stop tenant={tenant_id} reason={lic_reason}", force=True)
                    if stop_event is not None:
                        stop_event.set()
                    state["running"] = False
                    break

            if isolation_lock is not None:
                isolation_lock.acquire()
            try:
                with tenant_scope(tenant_id):
                    set_active_tenant(tenant_id)
                    # Strict tenant isolation for global runtime config/state dependent engine code
                    from bot.runtime_store import load_runtime_config
                    load_runtime_config(tenant_id)

                    if RUNTIME_CONFIG.get("MODE") == "LIVE" and not leverage_applied:
                        apply_leverage_settings()
                        leverage_applied = True

                    if RUNTIME_CONFIG.get("PANIC_STOP", False):
                        pass
                    else:
                        for symbol in RUNTIME_CONFIG.get("SYMBOLS", ["BTC/USDT"]):
                            try:
                                df = fetch_ohlcv_df(symbol)
                                analysis = analyze_market(df)
                                last_map = state.setdefault("last_candle_time_by_symbol", {})
                                if analysis["time"] == last_map.get(symbol):
                                    continue
                                last_map[symbol] = analysis["time"]

                                log = {
                                    "time": analysis["time"], "symbol": symbol, "bias": analysis["bias"], "close": analysis["close"],
                                    "rsi": analysis["rsi"], "golden_zone": analysis["golden_zone"], "result": "SKIP", "note": ""
                                }

                                if analysis["golden_zone"] and analysis["quality_ok"]:
                                    ok, reason = can_enter_trade_now(state=state)
                                    if not ok:
                                        log["result"] = "BLOCKED"; log["note"] = reason
                                    else:
                                        trade = calc_trade(df, analysis)
                                        if trade:
                                            if RUNTIME_CONFIG["MODE"] == "PAPER":
                                                log["result"] = "ENTRY_PAPER"
                                                log["note"] = f"entry={trade['entry']} sl={trade['sl']} tp1={trade['tp1']} tp2={trade['tp2']}"
                                                touch_cooldown(state=state)
                                            else:
                                                st = send_live_order(symbol, analysis["bias"], trade)
                                                log["result"] = "ENTRY_LIVE" if st == "live_sent" else "BLOCKED"
                                                log["note"] = st
                                                if st == "live_sent":
                                                    touch_cooldown(state=state)
                                elif analysis["golden_zone"] and not analysis["quality_ok"]:
                                    log["result"] = "BLOCKED"
                                    log["note"] = f"quality_filter adx={analysis['adx']:.1f} atr%={analysis['atr_pct']:.2f}"

                                log_to_csv(log)
                                log_trade(log)
                                notify_trade(symbol, log.get("result", ""), log.get("note", ""))
                            except Exception as e_sym:
                                if RUNTIME_CONFIG.get("ALERT_ON_ERROR", True):
                                    notify(f"⚠️ {symbol} error: {e_sym}")
            finally:
                if isolation_lock is not None:
                    isolation_lock.release()
        except Exception as e:
            if RUNTIME_CONFIG.get("ALERT_ON_ERROR", True):
                notify(f"⚠️ Engine error: {e}")
        time.sleep(LOOP_INTERVAL)

    notify(f"⏹ Trading bot stopped (tenant={tenant_id})")


def run_engine():
    # Backward-compatible legacy single-tenant runner
    run_engine_for_tenant(ACTIVE_TENANT_ID, state=bot_state)
