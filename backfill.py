import os
import csv
import ccxt
import pandas as pd
from datetime import datetime, timedelta

from bot.indicators import ema, rsi
from bot.config import EQUITY_USDT, RISK_PER_TRADE, MAX_SL_PERCENT

# =============================
# CONFIG
# =============================
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
MONTHS_BACK = 6

GOLDEN_ZONE_DISTANCE = 0.5
RSI_MIN = 40
RSI_MAX = 60

CSV_PATH = "data/paper_trades.csv"

# =============================
# EXCHANGE
# =============================
exchange = ccxt.binance({
    "enableRateLimit": True,
    "options": {"defaultType": "future"}
})

# =============================
# CSV LOGGER
# =============================
def log_to_csv(row: dict):
    file_exists = os.path.isfile(CSV_PATH)
    with open(CSV_PATH, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

# =============================
# HELPERS
# =============================
def fetch_ohlcv_history():
    since = int((datetime.utcnow() - timedelta(days=30*MONTHS_BACK)).timestamp() * 1000)
    all_ohlcv = []

    while True:
        ohlcv = exchange.fetch_ohlcv(
            SYMBOL,
            timeframe=TIMEFRAME,
            since=since,
            limit=1000
        )
        if not ohlcv:
            break

        since = ohlcv[-1][0] + 1
        all_ohlcv.extend(ohlcv)

        if len(ohlcv) < 1000:
            break

    df = pd.DataFrame(
        all_ohlcv,
        columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    return df

def find_swing_low(df, idx, lookback=10):
    return df["low"].iloc[idx-lookback:idx].min()

def find_swing_high(df, idx, lookback=10):
    return df["high"].iloc[idx-lookback:idx].max()

# =============================
# MAIN BACKFILL
# =============================
def main():
    print("🚀 Starting BACKFILL 6 months BTCUSDT 1H")

    df = fetch_ohlcv_history()
    print(f"📦 Candles loaded: {len(df)}")

    df["ema50"] = ema(df["close"], 50)
    df["ema200"] = ema(df["close"], 200)
    df["rsi"] = rsi(df["close"], 14)

    entries = 0
    skips = 0

    for i in range(210, len(df) - 1):
        candle = df.iloc[i]

        # -------------------------
        # Market Bias
        # -------------------------
        bias = "NO TRADE"
        if candle["ema50"] > candle["ema200"] and candle["close"] > candle["ema200"]:
            bias = "LONG"
        elif candle["ema50"] < candle["ema200"] and candle["close"] < candle["ema200"]:
            bias = "SHORT"

        # -------------------------
        # Golden Zone
        # -------------------------
        distance = abs((candle["close"] - candle["ema50"]) / candle["ema50"]) * 100

        golden_zone = (
            bias in ["LONG", "SHORT"]
            and distance <= GOLDEN_ZONE_DISTANCE
            and RSI_MIN <= candle["rsi"] <= RSI_MAX
        )

        log_row = {
            "time": datetime.utcfromtimestamp(candle["timestamp"]/1000),
            "bias": bias,
            "close": round(candle["close"], 2),
            "ema50": round(candle["ema50"], 2),
            "ema200": round(candle["ema200"], 2),
            "rsi": round(candle["rsi"], 2),
            "distance_ema50": round(distance, 2),
            "golden_zone": golden_zone,
            "result": "SKIP"
        }

        if golden_zone:
            # -------------------------
            # SL / TP
            # -------------------------
            if bias == "LONG":
                sl = find_swing_low(df, i)
                sl_pct = (candle["close"] - sl) / candle["close"] * 100
            else:
                sl = find_swing_high(df, i)
                sl_pct = (sl - candle["close"]) / candle["close"] * 100

            if 0 < sl_pct <= MAX_SL_PERCENT:
                risk_money = EQUITY_USDT * RISK_PER_TRADE
                position_size = risk_money / (sl_pct / 100)

                log_row.update({
                    "entry": round(candle["close"], 2),
                    "sl": round(sl, 2),
                    "sl_percent": round(sl_pct, 2),
                    "tp1_percent": round(sl_pct * 2, 2),
                    "tp2_percent": round(sl_pct * 3, 2),
                    "position_size": round(position_size, 0),
                    "result": "ENTRY"
                })
                entries += 1
            else:
                skips += 1
        else:
            skips += 1

        log_to_csv(log_row)

    print("✅ Backfill complete")
    print(f"📈 Entries: {entries}")
    print(f"⏭ Skips: {skips}")
    print("👉 You can now run analyze_results.py and simulate_results.py\n")

if __name__ == "__main__":
    main()
