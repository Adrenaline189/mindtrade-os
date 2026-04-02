import csv
import os
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ccxt
import pandas as pd
from dotenv import load_dotenv

from bot.alerts import send_telegram_alert, send_telegram_alert_throttled
from bot.config import EQUITY_USDT, MAX_SL_PERCENT
from bot.config_runtime import RUNTIME_CONFIG
from bot.indicators import ema, rsi
from bot.paths import get_tenant_paths
from bot.state import bot_state
from bot.storage import count_entries_today_utc, fetch_trade_results_since, init_db, log_trade
from bot.tenant_context import default_tenant_id, tenant_scope
from bot.tenant_store import get_primary_email_for_tenant
from bot.user_api_store import get_user_api

load_dotenv()

TIMEFRAME = "1h"
LOOP_INTERVAL = 30
BASE_DIR = Path(__file__).resolve().parents[1]
ACTIVE_TENANT_ID = default_tenant_id()


@dataclass
class EngineContext:
    tenant_id: str
    runtime_config: dict
    exchange: object
    state: dict



def create_exchange_client(tenant_id: str | None = None):
    api_key = ""
    api_secret = ""

    tid = (tenant_id or default_tenant_id()).strip()
    email = get_primary_email_for_tenant(tid)
    if email:
        api_key, api_secret = get_user_api(email, tenant_id=tid)

    # Security fix (Fix #1): Only fall back to global env vars for the DEFAULT tenant.
    # All other tenants MUST have their own API keys configured.
    if not api_key or not api_secret:
        default_tid = default_tenant_id().strip()
        if tid == default_tid:
            # Default tenant can still use global env vars for dev convenience
            api_key = os.getenv("BINANCE_API_KEY", "")
            api_secret = os.getenv("BINANCE_API_SECRET", "")
        else:
            raise ValueError(
                f"Tenant {tid} has no API keys configured. "
                f"Please configure API keys for this tenant before trading."
            )

    return ccxt.binance(
        {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
        }
    )


def create_engine_context(tenant_id: str, state: dict | None = None, runtime_config: dict | None = None, exchange_client=None):
    tid = (tenant_id or default_tenant_id()).strip()
    return EngineContext(
        tenant_id=tid,
        runtime_config=runtime_config or deepcopy(RUNTIME_CONFIG),
        exchange=exchange_client or create_exchange_client(tid),
        state=state or bot_state,
    )


def set_active_tenant(tenant_id: str):
    global ACTIVE_TENANT_ID
    ACTIVE_TENANT_ID = (tenant_id or default_tenant_id()).strip()


def _cfg(ctx: EngineContext | None):
    return ctx.runtime_config if ctx else RUNTIME_CONFIG


def _exchange(ctx: EngineContext | None):
    return ctx.exchange if ctx else exchange


def _data_file(ctx: EngineContext | None = None) -> Path:
    tenant_id = (ctx.tenant_id if ctx else ACTIVE_TENANT_ID) or default_tenant_id()
    return get_tenant_paths(tenant_id)["trades_csv"]


exchange = create_exchange_client()


def notify(msg: str, force: bool = False, ctx: EngineContext | None = None):
    print(msg)
    cfg = _cfg(ctx)
    if force or cfg.get("TELEGRAM_ALERTS", True):
        send_telegram_alert(msg)


def notify_throttled(msg: str, *, dedupe_key: str, cooldown_sec: float = 900.0, ctx: EngineContext | None = None):
    print(msg)
    cfg = _cfg(ctx)
    if cfg.get("TELEGRAM_ALERTS", True):
        send_telegram_alert_throttled(msg, dedupe_key=dedupe_key, cooldown_sec=cooldown_sec)


def notify_trade(symbol: str, result: str, note: str = "", ctx: EngineContext | None = None):
    cfg = _cfg(ctx)
    if result in {"ENTRY_PAPER", "ENTRY_LIVE"} and cfg.get("ALERT_ON_ENTRY", True):
        notify(f"📣 {result} {symbol} | {note}", ctx=ctx)
    elif result == "BLOCKED" and cfg.get("ALERT_ON_BLOCKED", False):
        notify(f"🚧 BLOCKED {symbol} | {note}", ctx=ctx)


def log_to_csv(row: dict, ctx: EngineContext | None = None):
    data_file = _data_file(ctx)
    data_file.parent.mkdir(parents=True, exist_ok=True)
    file_exists = data_file.exists()
    with data_file.open(mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def fetch_ohlcv_df(symbol: str, limit=300, ctx: EngineContext | None = None):
    ex = _exchange(ctx)
    ohlcv = ex.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=limit)
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


def in_news_blackout(now_utc: datetime, ctx: EngineContext | None = None) -> bool:
    cfg = _cfg(ctx)
    hhmm = now_utc.strftime("%H:%M")
    for w in cfg.get("NEWS_BLACKOUT_WINDOWS_UTC", []):
        try:
            s, e = w.split("-")
            if s <= hhmm <= e:
                return True
        except Exception:
            pass
    return False


def _parse_session_windows_utc(raw: str) -> list[tuple[int, int]]:
    windows = []
    for part in str(raw or "").split(","):
        piece = part.strip()
        if not piece:
            continue
        try:
            s, e = piece.split("-")
            sh, eh = int(s), int(e)
            if 0 <= sh <= 23 and 0 <= eh <= 23:
                windows.append((sh, eh))
        except Exception:
            continue
    return windows


def is_session_open(now_utc: datetime, ctx: EngineContext | None = None) -> tuple[bool, str]:
    cfg = _cfg(ctx)
    if not bool(cfg.get("SESSION_FILTER_ENABLED", False)):
        return True, "disabled"

    windows_raw = cfg.get("SESSION_WINDOWS_UTC", "00-23")
    windows = _parse_session_windows_utc(windows_raw)
    if not windows:
        return False, f"session_filter_invalid windows={windows_raw}"

    hour = int(now_utc.hour)
    for start_h, end_h in windows:
        if start_h <= end_h:
            if start_h <= hour <= end_h:
                return True, "ok"
        else:
            if hour >= start_h or hour <= end_h:
                return True, "ok"
    return False, f"session_filter_closed hour={hour:02d} windows={windows_raw}"


def refresh_loss_streak_state(state: dict, ctx: EngineContext | None = None):
    cfg = _cfg(ctx)
    tenant_id = (ctx.tenant_id if ctx else None)
    last_id = int(state.get("loss_streak_last_trade_log_id", 0) or 0)

    while True:
        rows = fetch_trade_results_since(last_id=last_id, tenant_id=tenant_id, limit=300)
        if not rows:
            break
        for row_id, result in rows:
            last_id = int(row_id)
            if result == "PAPER_SL":
                state["loss_streak"] = int(state.get("loss_streak", 0) or 0) + 1
                state["consecutive_loss"] = state["loss_streak"]
            elif result in {"PAPER_TP1", "PAPER_TP2"}:
                state["loss_streak"] = 0
                state["consecutive_loss"] = 0

    state["loss_streak_last_trade_log_id"] = last_id

    if bool(cfg.get("LOSS_STREAK_COOLDOWN_ENABLED", True)):
        trigger = int(cfg.get("LOSS_STREAK_COOLDOWN_TRIGGER", 3) or 3)
        cooldown_minutes = int(cfg.get("LOSS_STREAK_COOLDOWN_MINUTES", 120) or 120)
        streak = int(state.get("loss_streak", 0) or 0)
        applied_for = int(state.get("loss_streak_cooldown_applied_for", 0) or 0)
        if trigger > 0 and streak >= trigger and streak != applied_for:
            until = datetime.now(timezone.utc) + timedelta(minutes=max(1, cooldown_minutes))
            current_until = state.get("cooldown_until")
            if not current_until or until > current_until:
                state["cooldown_until"] = until
            state["loss_streak_cooldown_applied_for"] = streak
        elif streak == 0:
            state["loss_streak_cooldown_applied_for"] = 0


def effective_risk_per_trade(state: dict, ctx: EngineContext | None = None) -> float:
    cfg = _cfg(ctx)
    base_risk = float(cfg.get("RISK_PER_TRADE", 0.0) or 0.0)
    loss_streak = int(state.get("loss_streak", 0) or 0)
    enabled = bool(cfg.get("LOSS_STREAK_DOWNSHIFT_ENABLED", False))
    trigger = int(cfg.get("LOSS_STREAK_TRIGGER", 2) or 2)
    mult = float(cfg.get("LOSS_STREAK_RISK_MULT", 0.7) or 0.7)

    risk = base_risk
    if enabled and trigger > 0 and loss_streak >= trigger:
        risk = base_risk * max(0.0, mult)
    state["effective_risk_per_trade"] = risk
    return risk


def analyze_market(df, ctx: EngineContext | None = None):
    cfg = _cfg(ctx)
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
        and distance <= cfg["GOLDEN_ZONE_DISTANCE"]
        and cfg["RSI_MIN"] <= last["rsi"] <= cfg["RSI_MAX"]
    )
    quality_ok = (
        float(last["adx"]) >= float(cfg.get("ADX_MIN", 18))
        and float(cfg.get("ATR_PCT_MIN", 0.25)) <= atr_pct <= float(cfg.get("ATR_PCT_MAX", 3.5))
    )

    return {
        "time": datetime.utcfromtimestamp(last["timestamp"] / 1000),
        "close": float(last["close"]),
        "ema50": float(last["ema50"]),
        "ema200": float(last["ema200"]),
        "distance_pct": float(distance),
        "rsi": float(last["rsi"]),
        "adx": float(last["adx"]),
        "atr_pct": atr_pct,
        "bias": bias,
        "golden_zone": golden_zone,
        "quality_ok": quality_ok,
    }


def _fetch_symbol_contracts(symbol: str, ctx: EngineContext | None = None) -> float:
    ex = _exchange(ctx)
    try:
        positions = ex.fetch_positions([symbol])
        for p in positions:
            if str(p.get("symbol") or "").upper() == symbol.upper():
                return float(p.get("contracts") or 0)
    except Exception:
        return 0.0
    return 0.0


def compute_realtime_score(analysis: dict, cfg: dict) -> dict:
    bias = analysis.get("bias", "NO TRADE")
    rsi_v = float(analysis.get("rsi") or 0.0)
    adx_v = float(analysis.get("adx") or 0.0)
    atr_pct = float(analysis.get("atr_pct") or 0.0)
    distance = float(analysis.get("distance_pct") or 99.0)
    close = float(analysis.get("close") or 0.0)
    ema200 = float(analysis.get("ema200") or 0.0)

    # Weighted components: trend(40) + momentum(35) + volatility(25)
    trend = 0.0
    momentum = 0.0
    volatility = 0.0
    reasons = []

    if bias in {"LONG", "SHORT"}:
        trend += 18.0
        reasons.append(f"bias={bias}")

        dist_limit = max(0.05, float(cfg.get("GOLDEN_ZONE_DISTANCE", 0.8)))
        if distance <= dist_limit:
            trend += 14.0
            reasons.append(f"pullback_ok distance={distance:.2f}%")
        else:
            reasons.append(f"pullback_far distance={distance:.2f}%>{dist_limit:.2f}%")

        if close > 0 and ema200 > 0:
            ema_gap = abs((close - ema200) / ema200) * 100
            if ema_gap >= 0.1:
                trend += min(8.0, ema_gap * 2.5)
                reasons.append(f"ema_trend_gap={ema_gap:.2f}%")

    rsi_min = float(cfg.get("RSI_MIN", 40))
    rsi_max = float(cfg.get("RSI_MAX", 60))
    rsi_mid = (rsi_min + rsi_max) / 2.0
    rsi_half = max(1.0, (rsi_max - rsi_min) / 2.0)
    rsi_offset = abs(rsi_v - rsi_mid)
    if rsi_min <= rsi_v <= rsi_max:
        momentum += max(0.0, 25.0 - (rsi_offset / rsi_half) * 8.0)
        reasons.append(f"rsi_in_range={rsi_v:.1f}")
    else:
        momentum += max(0.0, 8.0 - (rsi_offset / rsi_half) * 4.0)
        reasons.append(f"rsi_out_of_range={rsi_v:.1f}")

    adx_min = float(cfg.get("ADX_MIN", 14.0))
    if adx_v >= adx_min:
        momentum += min(10.0, (adx_v - adx_min) * 0.8 + 4.0)
        reasons.append(f"adx_ok={adx_v:.1f}")
    else:
        momentum += max(0.0, adx_v / max(adx_min, 1.0) * 4.0)
        reasons.append(f"adx_weak={adx_v:.1f}<{adx_min:.1f}")

    atr_min = float(cfg.get("ATR_PCT_MIN", 0.25))
    atr_max = float(cfg.get("ATR_PCT_MAX", 3.5))
    if atr_min <= atr_pct <= atr_max:
        atr_mid = (atr_min + atr_max) / 2.0
        atr_half = max(0.05, (atr_max - atr_min) / 2.0)
        atr_offset = abs(atr_pct - atr_mid)
        volatility += max(0.0, 25.0 - (atr_offset / atr_half) * 10.0)
        reasons.append(f"atr_in_range={atr_pct:.2f}%")
    else:
        volatility += 3.0
        reasons.append(f"atr_out_of_range={atr_pct:.2f}%")

    trend = max(0.0, min(40.0, trend))
    momentum = max(0.0, min(35.0, momentum))
    volatility = max(0.0, min(25.0, volatility))

    total = int(round(max(0.0, min(100.0, trend + momentum + volatility))))
    return {
        "score": total,
        "components": {
            "trend": round(trend, 2),
            "momentum": round(momentum, 2),
            "volatility": round(volatility, 2),
        },
        "reasons": reasons,
    }



def _min_notional_for_symbol(symbol: str, cfg: dict) -> float:
    by_symbol = cfg.get("MIN_NOTIONAL_BY_SYMBOL_USDT", {}) or {}
    if symbol in by_symbol:
        try:
            return float(by_symbol.get(symbol) or 0)
        except Exception:
            pass
    return float(cfg.get("MIN_NOTIONAL_USDT", 10) or 10)


def calc_trade(df, analysis, symbol: str | None = None, ctx: EngineContext | None = None):
    cfg = _cfg(ctx)
    entry = analysis["close"]
    bias = analysis["bias"]
    symbol_key = (symbol or '').strip().upper()

    sl_tp_map = cfg.get("SL_TP_BY_SYMBOL", {}) or {}
    preset = sl_tp_map.get(symbol_key)

    if preset:
        sl_pct = float(preset.get("sl_pct") or 0)
        tp_pct = float(preset.get("tp_pct") or 0)
        if sl_pct <= 0 or tp_pct <= 0:
            return None
        if sl_pct > MAX_SL_PERCENT:
            return None
        if bias == "LONG":
            sl = entry * (1 - sl_pct / 100)
            tp1 = entry * (1 + tp_pct / 100)
        elif bias == "SHORT":
            sl = entry * (1 + sl_pct / 100)
            tp1 = entry * (1 - tp_pct / 100)
        else:
            return None
        tp2 = tp1
    else:
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
        tp1 = entry * (1 + sl_pct / 100) if bias == "LONG" else entry * (1 - sl_pct / 100)
        tp2 = entry * (1 + (sl_pct * 3) / 100) if bias == "LONG" else entry * (1 - (sl_pct * 3) / 100)

    min_notional = _min_notional_for_symbol(symbol_key, cfg)

    fixed_order_usdt = float(cfg.get("ORDER_SIZE_USDT", 0) or 0)
    if fixed_order_usdt > 0:
        effective_order_usdt = max(fixed_order_usdt, min_notional)
        size = effective_order_usdt / entry
    else:
        risk_money = EQUITY_USDT * effective_risk_per_trade((ctx.state if ctx else bot_state), ctx=ctx)
        notional_size = risk_money / (sl_pct / 100)
        if notional_size < min_notional:
            return None
        size = notional_size / entry
    return {
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp1": round(tp1, 2),
        "tp2": round(tp2, 2),
        "size": round(size, 3),
    }


def count_open_positions_now(symbol: str | None = None, state: dict | None = None, ctx: EngineContext | None = None) -> int:
    cfg = _cfg(ctx)
    mode = str(cfg.get("MODE", "PAPER")).upper()

    if mode == "PAPER":
        st = state or (ctx.state if ctx else bot_state)
        paper_positions = st.get("paper_trade_by_symbol") or {}
        return len([v for v in paper_positions.values() if v])

    ex = _exchange(ctx)
    symbols = [symbol] if symbol else cfg.get("SYMBOLS", [])
    count = 0
    try:
        positions = ex.fetch_positions(symbols)
        for p in positions:
            contracts = float(p.get("contracts") or 0)
            if contracts != 0:
                count += 1
    except Exception:
        return 0
    return count


def has_open_position_now(symbol: str | None = None, ctx: EngineContext | None = None) -> bool:
    return count_open_positions_now(symbol=symbol, ctx=ctx) > 0


def can_enter_trade_now(state=None, symbol: str | None = None, ctx: EngineContext | None = None):
    cfg = _cfg(ctx)
    state = state or (ctx.state if ctx else bot_state)
    tenant_id = (ctx.tenant_id if ctx else None)
    if count_entries_today_utc(tenant_id=tenant_id) >= int(cfg.get("MAX_TRADES_PER_DAY", 3)):
        return False, "daily_limit"
    cu = state.get("cooldown_until")
    if cu and datetime.now(timezone.utc) < cu:
        return False, "cooldown"
    if bool(cfg.get("ONE_POSITION_AT_A_TIME", True)) and has_open_position_now(symbol=symbol, ctx=ctx):
        return False, "open_position_exists"

    max_open_positions = int(cfg.get("MAX_OPEN_POSITIONS", 1) or 1)
    if max_open_positions > 0:
        open_count = count_open_positions_now(state=state, ctx=ctx)
        if open_count >= max_open_positions:
            return False, f"max_open_positions:{open_count}/{max_open_positions}"
    now_utc = datetime.now(timezone.utc)
    if in_news_blackout(now_utc, ctx=ctx):
        return False, "news_blackout"
    session_ok, session_reason = is_session_open(now_utc, ctx=ctx)
    if not session_ok:
        return False, session_reason
    return True, "ok"


def touch_cooldown(state=None, ctx: EngineContext | None = None):
    cfg = _cfg(ctx)
    state = state or (ctx.state if ctx else bot_state)
    state["cooldown_until"] = datetime.now(timezone.utc) + timedelta(minutes=int(cfg.get("COOLDOWN_MINUTES", 60)))


def reconcile_live_close(symbol: str, analysis: dict, state: dict, ctx: EngineContext | None = None):
    live_positions = state.setdefault("live_positions", {})
    pos = live_positions.get(symbol)
    if not pos:
        return

    contracts = _fetch_symbol_contracts(symbol, ctx=ctx)
    if contracts != 0:
        return

    entry = float(pos.get("entry") or 0)
    sl = float(pos.get("sl") or 0)
    side = str(pos.get("side") or "")
    close_px = float(analysis.get("close") or entry or 0)
    if entry <= 0 or sl <= 0 or close_px <= 0:
        live_positions.pop(symbol, None)
        return

    risk = abs(entry - sl)
    if risk <= 0:
        live_positions.pop(symbol, None)
        return

    if side == "LONG":
        r = (close_px - entry) / risk
    else:
        r = (entry - close_px) / risk

    result = "LIVE_TP" if r >= 0 else "LIVE_SL"
    row = {
        "time": datetime.now(timezone.utc),
        "symbol": symbol,
        "bias": side,
        "close": close_px,
        "rsi": analysis.get("rsi"),
        "golden_zone": False,
        "result": result,
        "note": f"r={round(r,3)} close={round(close_px,4)} entry={entry} sl={sl}",
    }
    log_to_csv(row, ctx=ctx)
    log_trade(row, tenant_id=(ctx.tenant_id if ctx else None))
    notify(f"✅ {result} {symbol} | r={round(r,3)}", ctx=ctx)
    live_positions.pop(symbol, None)


def normalize_order_amount(symbol: str, amount: float, ctx: EngineContext | None = None):
    """Clamp + precision-normalize order amount to exchange market limits."""
    ex = _exchange(ctx)
    try:
        ex.load_markets()
    except Exception:
        pass

    market = ex.market(symbol)
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
        amt = float(ex.amount_to_precision(symbol, amt))
    except Exception:
        pass

    if amt <= 0:
        return None, 'non_positive_qty'

    if min_amt is not None and amt < float(min_amt):
        amt = float(min_amt)
        changed = True
        try:
            amt = float(ex.amount_to_precision(symbol, amt))
        except Exception:
            pass

    return amt, ('clamped' if changed else '')




def margin_precheck_ok(symbol: str, qty: float, entry_price: float, ctx: EngineContext | None = None):
    """Best-effort free margin pre-check with affordable qty downscale."""
    ex = _exchange(ctx)
    try:
        bal = ex.fetch_balance()
        usdt = (bal.get('USDT') or {}) if isinstance(bal, dict) else {}
        free = float(usdt.get('free') or 0)
    except Exception:
        return True, float(qty), 0.0, 0.0

    cfg = _cfg(ctx)
    default_lev = int(cfg.get('LEVERAGE', 5) or 5)
    lev_map = cfg.get('LEVERAGE_BY_SYMBOL', {}) or {}
    lev = int(lev_map.get(symbol, default_lev) or default_lev)
    lev = max(1, lev)

    price = max(0.0, float(entry_price or 0.0))
    if price <= 0:
        return True, float(qty), free, 0.0

    # Keep a safety reserve and cap usable margin to avoid over-sizing.
    reserve = max(2.0, free * 0.10)
    usable = max(0.0, free - reserve)

    required = (float(qty) * price) / lev
    if required <= usable:
        return True, float(qty), free, required

    affordable_qty = (usable * lev) / price if price > 0 else 0.0
    try:
        affordable_qty = float(ex.amount_to_precision(symbol, affordable_qty))
    except Exception:
        pass

    if affordable_qty <= 0:
        return False, 0.0, free, required

    return True, affordable_qty, free, required


def place_order_with_qty_retry(symbol: str, order_type: str, side: str, qty: float, *, params=None, max_attempts: int = 6, ctx: EngineContext | None = None):
    """Retry order with smaller qty when exchange returns max-qty errors."""
    ex = _exchange(ctx)
    params = params or {}
    current = float(qty)
    last_err = None
    for attempt in range(1, max_attempts + 1):
        adj, _ = normalize_order_amount(symbol, current, ctx=ctx)
        if adj is None:
            raise Exception(f"invalid_qty_after_normalize:{current}")
        try:
            return ex.create_order(symbol, order_type, side, adj, params=params), adj
        except Exception as e:
            last_err = e
            msg = str(e)
            if ('-4005' in msg) or ('max quantity' in msg.lower()):
                current = current * 0.5
                notify(f"⚠️ {symbol} {order_type} qty retry {attempt}: reduce -> {current}", ctx=ctx)
                continue
            if ('-2019' in msg) or ('margin is insufficient' in msg.lower()):
                notify_throttled(
                    f"🚨 {symbol} margin insufficient while placing {order_type}",
                    dedupe_key=f"margin_insufficient:{symbol}",
                    cooldown_sec=900,
                    ctx=ctx,
                )
                raise
            raise
    raise last_err if last_err else Exception('order_retry_failed')


def send_live_order(symbol: str, side: str, trade, ctx: EngineContext | None = None):
    cfg = _cfg(ctx)
    if cfg["MODE"] != "LIVE" or not cfg["ALLOW_LIVE_ORDERS"]:
        return "blocked"
    order_side = "buy" if side == "LONG" else "sell"
    close_side = "sell" if side == "LONG" else "buy"

    raw_size = float(trade["size"])
    size, reason = normalize_order_amount(symbol, raw_size, ctx=ctx)
    if size is None:
        notify(f"⚠️ order blocked {symbol}: invalid qty ({reason})", ctx=ctx)
        return "blocked"
    if reason:
        notify(f"⚠️ qty adjusted {symbol}: {raw_size} -> {size}", ctx=ctx)

    ok_margin, size_after_margin, free_margin, req_margin = margin_precheck_ok(symbol, size, float(trade.get("entry") or 0), ctx=ctx)
    if not ok_margin:
        notify_throttled(
            f"🚨 {symbol} blocked: margin insufficient (free={free_margin:.2f} < required≈{req_margin:.2f})",
            dedupe_key=f"margin_precheck:{symbol}",
            cooldown_sec=900,
            ctx=ctx,
        )
        return "blocked"

    if size_after_margin < size:
        notify(f"⚠️ {symbol} qty downscaled by margin: {size} -> {size_after_margin}", ctx=ctx)
        size = size_after_margin

    _, filled_qty = place_order_with_qty_retry(symbol, "MARKET", order_side, size, ctx=ctx)
    place_order_with_qty_retry(symbol, "STOP_MARKET", close_side, filled_qty, params={"stopPrice": trade["sl"], "reduceOnly": True}, ctx=ctx)

    half_target = filled_qty / 2
    half, _ = normalize_order_amount(symbol, half_target, ctx=ctx)
    rest = None
    if half is not None:
        rest, _ = normalize_order_amount(symbol, max(filled_qty - half, 0), ctx=ctx)

    if half is not None and rest is not None and rest > 0:
        place_order_with_qty_retry(symbol, "TAKE_PROFIT_MARKET", close_side, half, params={"stopPrice": trade["tp1"], "reduceOnly": True}, ctx=ctx)
        place_order_with_qty_retry(symbol, "TAKE_PROFIT_MARKET", close_side, rest, params={"stopPrice": trade["tp2"], "reduceOnly": True}, ctx=ctx)
    else:
        notify(f"⚠️ TP split fallback {symbol}: using single TP order", ctx=ctx)
        place_order_with_qty_retry(symbol, "TAKE_PROFIT_MARKET", close_side, filled_qty, params={"stopPrice": trade["tp1"], "reduceOnly": True}, ctx=ctx)

    return "live_sent"


def apply_leverage_settings(ctx: EngineContext | None = None):
    cfg = _cfg(ctx)
    ex = _exchange(ctx)
    default_lev = int(cfg.get("LEVERAGE", 5))
    margin_mode = str(cfg.get("MARGIN_MODE", "cross")).lower()
    lev_map = cfg.get("LEVERAGE_BY_SYMBOL", {}) or {}

    try:
        ex.load_markets()
    except Exception as e:
        notify(f"⚠️ load_markets failed before leverage set: {e}", ctx=ctx)

    for symbol in cfg.get("SYMBOLS", ["BTC/USDT"]):
        try:
            lev = int(lev_map.get(symbol, default_lev))
            market = ex.market(symbol)
            ex.set_leverage(lev, market["id"], params={"marginMode": margin_mode})
            notify(f"⚙️ Leverage set {symbol} = {lev}x ({margin_mode})", ctx=ctx)
        except Exception as e:
            notify(f"⚠️ leverage set failed {symbol}: {e}", ctx=ctx)


def run_engine_for_tenant(tenant_id: str, stop_event=None, state=None, isolation_lock=None, license_gate=None):
    state = state or bot_state
    ctx = create_engine_context(tenant_id=tenant_id, state=state)

    with tenant_scope(ctx.tenant_id):
        init_db(tenant_id=ctx.tenant_id)
        notify(f"🚀 Trading bot started (tenant={ctx.tenant_id})", ctx=ctx)

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
                lic_ok, lic_reason = license_gate(ctx.tenant_id)
                state["license_ok"] = bool(lic_ok)
                state["license_reason"] = lic_reason
                if not lic_ok:
                    notify(f"⛔ worker auto-stop tenant={ctx.tenant_id} reason={lic_reason}", force=True, ctx=ctx)
                    if stop_event is not None:
                        stop_event.set()
                    state["running"] = False
                    break

            if isolation_lock is not None:
                isolation_lock.acquire()
            try:
                from bot.runtime_store import read_runtime_config_for_tenant

                ctx.runtime_config = read_runtime_config_for_tenant(ctx.tenant_id)

                if ctx.runtime_config.get("MODE") == "LIVE" and not leverage_applied:
                    apply_leverage_settings(ctx=ctx)
                    leverage_applied = True

                refresh_loss_streak_state(state, ctx=ctx)
                effective_risk_per_trade(state, ctx=ctx)

                if ctx.runtime_config.get("PANIC_STOP", False):
                    pass
                else:
                    for symbol in ctx.runtime_config.get("SYMBOLS", ["BTC/USDT"]):
                        if stop_event is not None and stop_event.is_set():
                            break
                        try:
                            df = fetch_ohlcv_df(symbol, ctx=ctx)
                            analysis = analyze_market(df, ctx=ctx)
                            last_map = state.setdefault("last_candle_time_by_symbol", {})
                            if analysis["time"] == last_map.get(symbol):
                                continue
                            last_map[symbol] = analysis["time"]

                            reconcile_live_close(symbol, analysis, state, ctx=ctx)

                            score_data = compute_realtime_score(analysis, ctx.runtime_config)
                            threshold = int(ctx.runtime_config.get("ENTRY_SCORE_THRESHOLD", 65) or 65)
                            soft_gate = bool(ctx.runtime_config.get("ENTRY_SCORE_SOFT_GATE", True))
                            score_ok = score_data["score"] >= threshold
                            entry_setup_ok = analysis["golden_zone"] and analysis["quality_ok"]

                            state.setdefault("realtime_signals", {})[symbol] = {
                                "time": analysis["time"].isoformat(),
                                "symbol": symbol,
                                "bias": analysis["bias"],
                                "close": analysis["close"],
                                "rsi": analysis["rsi"],
                                "adx": analysis["adx"],
                                "atr_pct": analysis["atr_pct"],
                                "distance_pct": analysis["distance_pct"],
                                "golden_zone": analysis["golden_zone"],
                                "quality_ok": analysis["quality_ok"],
                                "score": score_data["score"],
                                "components": score_data["components"],
                                "score_reasons": score_data["reasons"],
                                "score_threshold": threshold,
                                "score_ok": score_ok,
                                "soft_gate": soft_gate,
                                "loss_streak": int(state.get("loss_streak", 0) or 0),
                                "effective_risk_per_trade": float(state.get("effective_risk_per_trade") or ctx.runtime_config.get("RISK_PER_TRADE", 0.0)),
                            }

                            log = {
                                "time": analysis["time"], "symbol": symbol, "bias": analysis["bias"], "close": analysis["close"],
                                "rsi": analysis["rsi"], "golden_zone": analysis["golden_zone"], "result": "SKIP",
                                "note": f"score={score_data['score']} trend={score_data['components']['trend']} momentum={score_data['components']['momentum']} volatility={score_data['components']['volatility']}"
                            }

                            if entry_setup_ok:
                                if soft_gate and not score_ok:
                                    log["result"] = "BLOCKED"
                                    log["note"] = f"score_gate score={score_data['score']}<{threshold} components={score_data['components']}"
                                else:
                                    ok, reason = can_enter_trade_now(state=state, symbol=symbol, ctx=ctx)
                                    if not ok:
                                        log["result"] = "BLOCKED"; log["note"] = f"{reason} score={score_data['score']}"
                                    else:
                                        trade = calc_trade(df, analysis, symbol=symbol, ctx=ctx)
                                        if trade:
                                            if ctx.runtime_config["MODE"] == "PAPER":
                                                log["result"] = "ENTRY_PAPER"
                                                log["note"] = f"entry={trade['entry']} sl={trade['sl']} tp1={trade['tp1']} tp2={trade['tp2']} score={score_data['score']} risk={state.get('effective_risk_per_trade')} loss_streak={state.get('loss_streak',0)} components={score_data['components']}"
                                                touch_cooldown(state=state, ctx=ctx)
                                            else:
                                                st = send_live_order(symbol, analysis["bias"], trade, ctx=ctx)
                                                log["result"] = "ENTRY_LIVE" if st == "live_sent" else "BLOCKED"
                                                log["note"] = f"{st} score={score_data['score']} risk={state.get('effective_risk_per_trade')} loss_streak={state.get('loss_streak',0)} components={score_data['components']}"
                                                if st == "live_sent":
                                                    state.setdefault("live_positions", {})[symbol] = {
                                                        "side": analysis["bias"],
                                                        "entry": trade["entry"],
                                                        "sl": trade["sl"],
                                                        "tp1": trade["tp1"],
                                                        "tp2": trade["tp2"],
                                                        "opened_at": datetime.now(timezone.utc).isoformat(),
                                                    }
                                                    touch_cooldown(state=state, ctx=ctx)
                                        else:
                                            log["result"] = "BLOCKED"
                                            log["note"] = f"calc_trade_failed score={score_data['score']}"
                            elif analysis["golden_zone"] and not analysis["quality_ok"]:
                                log["result"] = "BLOCKED"
                                log["note"] = f"quality_filter adx={analysis['adx']:.1f} atr%={analysis['atr_pct']:.2f} score={score_data['score']}"

                            log_to_csv(log, ctx=ctx)
                            log_trade(log, tenant_id=ctx.tenant_id)
                            notify_trade(symbol, log.get("result", ""), log.get("note", ""), ctx=ctx)
                        except Exception as e_sym:
                            if ctx.runtime_config.get("ALERT_ON_ERROR", True):
                                notify(f"⚠️ {symbol} error: {e_sym}", ctx=ctx)
            finally:
                if isolation_lock is not None:
                    isolation_lock.release()
            state["last_tick_at"] = time.time()
            state["ticks"] = int(state.get("ticks", 0)) + 1
        except Exception as e:
            state["last_error"] = str(e)
            if ctx.runtime_config.get("ALERT_ON_ERROR", True):
                notify_throttled(
                    f"🚨 Engine error ({ctx.tenant_id}): {e}",
                    dedupe_key=f"engine_error:{ctx.tenant_id}:{str(e)[:80]}",
                    cooldown_sec=600,
                    ctx=ctx,
                )
        if stop_event is not None:
            if stop_event.wait(LOOP_INTERVAL):
                break
        else:
            time.sleep(LOOP_INTERVAL)

    notify(f"⏹ Trading bot stopped (tenant={ctx.tenant_id})", ctx=ctx)


def run_engine():
    run_engine_for_tenant(ACTIVE_TENANT_ID, state=bot_state)
