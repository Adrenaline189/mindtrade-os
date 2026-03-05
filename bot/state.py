from datetime import date


def create_bot_state() -> dict:
    return {
        "running": False,
        "last_candle_time": None,
        "last_candle_time_by_symbol": {},

        "today": date.today().isoformat(),
        "daily_loss_r": 0.0,
        "consecutive_loss": 0,
        "loss_streak": 0,
        "loss_streak_last_trade_log_id": 0,
        "effective_risk_per_trade": None,
        "cooldown_until": None,

        "usdt_start_of_day": None,
        "usdt_current": None,

        "paper_trade": None,
        "paper_trade_by_symbol": {},

        # latest per-symbol realtime scoring snapshot for dashboard/API
        "realtime_signals": {},
    }


bot_state = create_bot_state()
