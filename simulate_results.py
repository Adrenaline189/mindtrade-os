import pandas as pd
import random

CSV_PATH = "data/paper_trades_final.csv"
RR_TP2 = 3  # TP2 = 3R

def main():
    df = pd.read_csv(CSV_PATH)

    if "tp2_percent" not in df.columns:
        print("❌ CSV has no tp2_percent column")
        return

    df["tp2_percent"] = pd.to_numeric(df["tp2_percent"], errors="coerce")

    # ENTRY = มี tp2_percent
    entries = df[df["tp2_percent"].notna()]

    if len(entries) == 0:
        print("❌ No ENTRY rows")
        return

    total = len(entries)

    # ---- Conservative Monte Carlo ----
    assumed_win_rate = 0.35  # realistic for RR 1:3

    wins = 0
    losses = 0

    for _ in range(total):
        if random.random() < assumed_win_rate:
            wins += 1
        else:
            losses += 1

    win_rate = wins / total * 100
    expectancy = (wins * RR_TP2 - losses) / total

    print("\n📊 BACKTEST (SIMULATED – STRUCTURAL)")
    print("-" * 45)
    print(f"Total trades : {total}")
    print(f"WIN          : {wins}")
    print(f"LOSS         : {losses}")
    print(f"Win rate    : {win_rate:.2f}%")
    print(f"Expectancy  : {expectancy:.2f}R")
    print("\n✅ Simulation complete\n")

if __name__ == "__main__":
    main()
