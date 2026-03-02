import os
import ccxt
from dotenv import load_dotenv

load_dotenv()

SYMBOL = "BTC/USDT"

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

print("🧪 Testing Binance Futures permissions (DRY RUN)")

if not api_key or not api_secret:
    print("❌ API NOT FOUND in environment")
    raise SystemExit(1)

exchange = ccxt.binance({
    "apiKey": api_key,
    "secret": api_secret,
    "enableRateLimit": True,
    "options": {"defaultType": "future"},
})

try:
    # 1) fetch balance (permission check)
    bal = exchange.fetch_balance()
    usdt_total = bal.get("USDT", {}).get("total", None)
    print(f"✅ Balance OK | Futures USDT total: {usdt_total}")

    # 2) fetch positions (futures permission check)
    # Some accounts/regions may block this; still useful
    try:
        positions = exchange.fetch_positions([SYMBOL])
        print(f"✅ Positions OK | count: {len(positions)}")
    except Exception as e:
        print("⚠️ fetch_positions not available/blocked on this account (still may trade).")
        print("   ", str(e))

    # 3) load markets + check symbol exists
    markets = exchange.load_markets()
    if SYMBOL not in markets:
        print(f"❌ SYMBOL not found in markets: {SYMBOL}")
        raise SystemExit(1)

    print("✅ Markets OK | symbol found:", SYMBOL)

    print("\n✅ DRY RUN PASSED (No order sent)")
    print("👉 Next step: enable bot to place *tiny* LIVE test order (if you want).")

except Exception as e:
    print("❌ API ERROR:")
    print(e)