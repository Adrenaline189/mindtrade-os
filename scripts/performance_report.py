#!/usr/bin/env python3
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / 'data' / 'paper_trades.csv'


def parse_r(note: str):
    note = (note or '').strip()
    if note.startswith('r='):
        try:
            return float(note[2:])
        except Exception:
            return None
    return None


def main():
    if not CSV_PATH.exists():
        print('No data file found:', CSV_PATH)
        return

    with CSV_PATH.open(newline='') as f:
        rows = list(csv.DictReader(f))

    counts = Counter(r.get('result', '') for r in rows)
    r_values = [x for x in (parse_r(r.get('note', '')) for r in rows) if x is not None]

    tp = counts.get('PAPER_TP1', 0) + counts.get('PAPER_TP2', 0)
    sl = counts.get('PAPER_SL', 0)
    decisions = tp + sl
    win_rate = (tp / decisions * 100) if decisions else 0.0

    total_r = sum(r_values) if r_values else 0.0
    avg_r = (total_r / len(r_values)) if r_values else 0.0

    # simple max drawdown in R-space (from sequence of realized r)
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in r_values:
        equity += r
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)

    print('=== PERFORMANCE REPORT ===')
    print('rows               :', len(rows))
    print('entries            :', counts.get('ENTRY_PAPER', 0) + counts.get('ENTRY_LIVE', 0) + counts.get('ENTRY', 0))
    print('tp hits            :', tp)
    print('sl hits            :', sl)
    print('win rate %         :', round(win_rate, 2))
    print('realized trades    :', len(r_values))
    print('total R            :', round(total_r, 4))
    print('avg R              :', round(avg_r, 4))
    print('max drawdown (R)   :', round(max_dd, 4))
    print('blocked            :', counts.get('BLOCKED', 0))
    print('skip               :', counts.get('SKIP', 0))


if __name__ == '__main__':
    main()
