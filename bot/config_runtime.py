from copy import deepcopy

# Runtime config ที่แก้ได้จาก UI
RUNTIME_CONFIG = {
    "RSI_MIN": 40,
    "RSI_MAX": 60,
    "GOLDEN_ZONE_DISTANCE": 0.8,
    "RISK_PER_TRADE": 0.005,
    "LEVERAGE": 5,
    "MARGIN_MODE": "cross",  # cross | isolated
    "LEVERAGE_BY_SYMBOL": {
        "BTC/USDT": 5,
        "ETH/USDT": 3,
        "SOL/USDT": 2,
    },

    # Symbols
    "SYMBOLS": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],

    # MODE
    "MODE": "PAPER",            # PAPER | LIVE
    "ALLOW_LIVE_ORDERS": False, # ต้อง True + MODE=LIVE เท่านั้นถึงยิงจริง

    # Risk guards
    "MAX_TRADES_PER_DAY": 3,
    "COOLDOWN_MINUTES": 60,
    "MIN_NOTIONAL_USDT": 10,
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
