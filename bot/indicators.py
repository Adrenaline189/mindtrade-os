# bot/indicators.py
import pandas as pd
import numpy as np

def ema(series, period: int):
    return series.ewm(span=period, adjust=False).mean()

def rsi(series, period: int = 14):
    delta = series.diff()

    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    gain_ema = pd.Series(gain).ewm(alpha=1/period, adjust=False).mean()
    loss_ema = pd.Series(loss).ewm(alpha=1/period, adjust=False).mean()

    rs = gain_ema / loss_ema
    rsi = 100 - (100 / (1 + rs))

    return rsi
