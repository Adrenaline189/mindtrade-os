import argparse
import os
import time
from datetime import datetime

import ccxt
import serial
from dotenv import load_dotenv

load_dotenv()


def fmt_num(v, d=2):
    try:
        return f"{float(v):.{d}f}"
    except Exception:
        return "-"


def build_line(ex):
    status = 'OK'
    try:
        bal = ex.fetch_balance()
        usdt = bal.get('USDT', {})
        total = fmt_num(usdt.get('total'))
        free = fmt_num(usdt.get('free'))
        used = fmt_num(usdt.get('used'))

        btc = ex.fetch_ticker('BTC/USDT').get('last')
        eth = ex.fetch_ticker('ETH/USDT').get('last')

        pnl = 0.0
        pos_count = 0
        try:
            positions = ex.fetch_positions(['BTC/USDT', 'ETH/USDT'])
            for p in positions:
                contracts = float(p.get('contracts') or 0)
                if contracts != 0:
                    pos_count += 1
                    pnl += float(p.get('unrealizedPnl') or 0)
        except Exception:
            pass

        pnl_s = f"{pnl:+.2f}"
        now = datetime.now().strftime('%H:%M:%S')
        return (
            f"TOTAL={total};FREE={free};USED={used};"
            f"BTC={fmt_num(btc,1)};ETH={fmt_num(eth,1)};"
            f"PNL={pnl_s};POS={pos_count};TIME={now};STATUS={status};"
        )
    except Exception:
        now = datetime.now().strftime('%H:%M:%S')
        return f"TOTAL=-;FREE=-;USED=-;BTC=-;ETH=-;PNL=-;POS=-;TIME={now};STATUS=ERR;"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='/dev/tty.usbserial-57930205901')
    ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--interval', type=int, default=8)
    args = ap.parse_args()

    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    if not api_key or not api_secret:
        raise SystemExit('Missing BINANCE_API_KEY/BINANCE_API_SECRET')

    ex = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {'defaultType': 'future'},
    })

    while True:
        try:
            with serial.Serial(args.port, args.baud, timeout=2) as ser:
                time.sleep(2)
                while True:
                    line = build_line(ex)
                    ser.write((line + '\n').encode())
                    print('sent:', line)
                    time.sleep(args.interval)
        except Exception as e:
            print('serial reconnect:', e)
            time.sleep(2)


if __name__ == '__main__':
    main()
