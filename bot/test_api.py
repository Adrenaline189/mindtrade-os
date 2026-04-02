import os
import ccxt

print("🔍 Checking Binance Futures API...")

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

if not api_key or not api_secret:
    print("❌ API NOT FOUND in environment")
    exit()

exchange = ccxt.binance({
    "apiKey": api_key,
    "secret": api_secret,
    "enableRateLimit": True,
    "options": {"defaultType": "future"},
})

try:
    balance = exchange.fetch_balance()
    usdt = balance["USDT"]["total"]
    print("✅ API CONNECTED SUCCESSFULLY")
    print(f"💰 Futures USDT Balance: {usdt}")
except Exception as e:
    print("❌ API ERROR")
    print(e)