from copy import deepcopy

# Runtime config ที่แก้ได้จาก UI
RUNTIME_CONFIG = {
    "RSI_MIN": 40,
    "RSI_MAX": 60,
    "GOLDEN_ZONE_DISTANCE": 0.8,
    "RISK_PER_TRADE": 0.007,
    "LEVERAGE": 5,
    "MARGIN_MODE": "cross",  # cross | isolated
    "LEVERAGE_BY_SYMBOL": {
        "BTC/USDT": 5,
        "ETH/USDT": 6,
        "SOL/USDT": 7,
        "BNB/USDT": 8,
        "XRP/USDT": 10,
        "DOGE/USDT": 5,
        "ADA/USDT": 5,
        "AVAX/USDT": 5,
        "LINK/USDT": 5,
        "TRX/USDT": 5,
    },

    # Symbols
    "SYMBOLS": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "LINK/USDT", "TRX/USDT"],

    # MODE
    "MODE": "PAPER",            # PAPER | LIVE
    "ALLOW_LIVE_ORDERS": False, # ต้อง True + MODE=LIVE เท่านั้นถึงยิงจริง

    # Risk guards
    "MAX_TRADES_PER_DAY": 3,
    "COOLDOWN_MINUTES": 60,
    "ONE_POSITION_AT_A_TIME": False,
    "MAX_OPEN_POSITIONS": 2,
    "MIN_NOTIONAL_USDT": 10,
    "MIN_NOTIONAL_BY_SYMBOL_USDT": {
        "BTC/USDT": 25,
        "ETH/USDT": 12,
        "SOL/USDT": 10,
        "BNB/USDT": 10,
        "XRP/USDT": 10,
        "DOGE/USDT": 10,
        "ADA/USDT": 10,
        "AVAX/USDT": 10,
        "LINK/USDT": 10,
        "TRX/USDT": 10,
    },
    "SL_TP_BY_SYMBOL": {
        "BTC/USDT": {"sl_pct": 2.0, "tp_pct": 3.4},
        "ETH/USDT": {"sl_pct": 2.2, "tp_pct": 3.8},
        "SOL/USDT": {"sl_pct": 3.1, "tp_pct": 5.3},
        "BNB/USDT": {"sl_pct": 2.1, "tp_pct": 3.6},
        "XRP/USDT": {"sl_pct": 2.8, "tp_pct": 4.8},
        "DOGE/USDT": {"sl_pct": 2.5, "tp_pct": 4.2},
        "ADA/USDT": {"sl_pct": 2.4, "tp_pct": 4.0},
        "AVAX/USDT": {"sl_pct": 2.9, "tp_pct": 5.0},
        "LINK/USDT": {"sl_pct": 2.6, "tp_pct": 4.4},
        "TRX/USDT": {"sl_pct": 1.9, "tp_pct": 3.2}
    },
    "ORDER_SIZE_USDT": 10,
    "DAILY_LOSS_CAP_PCT": 3.0,

    # Entry quality filters
    "ADX_MIN": 14.0,
    "ATR_PCT_MIN": 0.25,
    "ATR_PCT_MAX": 3.5,

    # Realtime entry scoring (0-100)
    "ENTRY_SCORE_SOFT_GATE": True,
    "ENTRY_SCORE_THRESHOLD": 65,

    # News blackout (UTC HH:MM-HH:MM)
    "NEWS_BLACKOUT_WINDOWS_UTC": [
        "12:25-12:45",
    ],

    # Session filter (UTC hour windows, e.g. "00-04,12-16")
    "SESSION_FILTER_ENABLED": False,
    "SESSION_WINDOWS_UTC": "00-23",

    # Lose-streak risk downshift
    "LOSS_STREAK_DOWNSHIFT_ENABLED": False,
    "LOSS_STREAK_TRIGGER": 2,
    "LOSS_STREAK_RISK_MULT": 0.7,
    "LOSS_STREAK_COOLDOWN_ENABLED": True,
    "LOSS_STREAK_COOLDOWN_TRIGGER": 3,
    "LOSS_STREAK_COOLDOWN_MINUTES": 120,

    # Alerts
    "TELEGRAM_ALERTS": True,
    "ALERT_ON_ENTRY": True,
    "ALERT_ON_BLOCKED": False,
    "ALERT_ON_ERROR": True,

    # 🔴 PANIC SWITCH
    "PANIC_STOP": False
}


# Immutable baseline used for tenant-scoped reads (avoid global mutable bleed)
DEFAULT_RUNTIME_CONFIG = deepcopy(RUNTIME_CONFIG)
