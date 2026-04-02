import os
from dotenv import load_dotenv
import ccxt

load_dotenv()

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

if not api_key or not api_secret:
    raise SystemExit("❌ Missing BINANCE_API_KEY/BINANCE_API_SECRET in .env")

exchange = ccxt.binance({
    "apiKey": api_key,
    "secret": api_secret,
    "enableRateLimit": True,
    "options": {"defaultType": "future"},
})

try:
    balance = exchange.fetch_balance()
    usdt = balance.get("USDT", {})

    total = usdt.get("total")
    free = usdt.get("free")
    used = usdt.get("used")

    print("✅ Binance Futures balance")
    print(f"USDT total : {total}")
    print(f"USDT free  : {free}")
    print(f"USDT used  : {used}")
except Exception as e:
    raise SystemExit(f"❌ API error: {e}")
