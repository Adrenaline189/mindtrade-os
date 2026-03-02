# Runtime config ที่แก้ได้จาก UI
RUNTIME_CONFIG = {
    "RSI_MIN": 40,
    "RSI_MAX": 60,
    "GOLDEN_ZONE_DISTANCE": 0.5,
    "RISK_PER_TRADE": 0.01,
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
    "DAILY_LOSS_CAP_PCT": 3.0,

    # Entry quality filters
    "ADX_MIN": 18.0,
    "ATR_PCT_MIN": 0.25,
    "ATR_PCT_MAX": 3.5,

    # News blackout (UTC HH:MM-HH:MM)
    "NEWS_BLACKOUT_WINDOWS_UTC": [
        "12:25-12:45",
    ],

    # Alerts
    "TELEGRAM_ALERTS": True,
    "ALERT_ON_ENTRY": True,
    "ALERT_ON_BLOCKED": False,
    "ALERT_ON_ERROR": True,

    # 🔴 PANIC SWITCH
    "PANIC_STOP": False
}
