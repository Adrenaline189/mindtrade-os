from datetime import date

bot_state = {
    "running": False,
    "last_candle_time": None,
    "last_candle_time_by_symbol": {},

    "today": date.today().isoformat(),
    "daily_loss_r": 0.0,
    "consecutive_loss": 0,
    "cooldown_until": None,

    "usdt_start_of_day": None,
    "usdt_current": None,

    "paper_trade": None,
    "paper_trade_by_symbol": {},
}
