import argparse
import os
import time

import ccxt
from dotenv import load_dotenv
import serial

load_dotenv()


def fetch_balance_text():
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        raise RuntimeError("Missing BINANCE_API_KEY/BINANCE_API_SECRET in .env")

    exchange = ccxt.binance({
        "apiKey": api_key,
        "secret": api_secret,
        "enableRateLimit": True,
        "options": {"defaultType": "future"},
    })

    bal = exchange.fetch_balance()
    usdt = bal.get("USDT", {})
    total = usdt.get("total")
    free = usdt.get("free")
    used = usdt.get("used")
    return f"USDT total={total} | free={free} | used={used}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/tty.usbserial-57930205901")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--interval", type=int, default=10)
    args = ap.parse_args()

    with serial.Serial(args.port, args.baud, timeout=2) as ser:
        time.sleep(2)
        while True:
            try:
                line = fetch_balance_text()
                ser.write((line + "\n").encode())
                print("sent:", line)
            except Exception as e:
                msg = f"ERROR: {e}"
                ser.write((msg + "\n").encode())
                print(msg)
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
