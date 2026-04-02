import pandas as pd

CSV_PATH = "data/paper_trades_final.csv"
RR_TP2 = 3  # TP2 = 3R

def main():
    df = pd.read_csv(CSV_PATH)

    # normalize
    if "tp2_percent" not in df.columns:
        print("❌ CSV has no tp2_percent column")
        return

    df["tp2_percent"] = pd.to_numeric(df["tp2_percent"], errors="coerce")

    total = len(df)

    # ENTRY = มี tp2_percent จริง
    entries = df[df["tp2_percent"].notna()]
    skips = df[df["tp2_percent"].isna()]

    print("\n📊 PAPER TRADING OVERVIEW")
    print("-" * 45)
    print(f"Total candles      : {total}")
    print(f"Entries            : {len(entries)}")
    print(f"Skips              : {len(skips)}")

    entry_rate = len(entries) / total * 100
    avg_wait = total / max(len(entries), 1)

    print(f"Entry rate         : {entry_rate:.2f}%")
    print(f"Avg candles/entry  : {avg_wait:.1f}")

    if len(entries) == 0:
        print("\n❌ No entries\n")
        return

    # ----- REAL SL FROM RR -----
    entries = entries.copy()
    entries["sl_percent_real"] = entries["tp2_percent"] / RR_TP2

    avg_sl = entries["sl_percent_real"].mean()
    max_sl = entries["sl_percent_real"].max()
    avg_tp2 = entries["tp2_percent"].mean()
    rr = avg_tp2 / avg_sl if avg_sl > 0 else 0

    print("\n📐 RISK STRUCTURE (REAL)")
    print("-" * 45)
    print(f"Avg SL (%)         : {avg_sl:.2f}")
    print(f"Max SL (%)         : {max_sl:.2f}")
    print(f"Avg TP2 (%)        : {avg_tp2:.2f}")
    print(f"Avg RR             : 1 : {rr:.2f}")

    print("\n🧠 SYSTEM VERDICT")
    print("-" * 45)

    verdict = "HEALTHY ✅"
    if entry_rate < 5:
        verdict = "TOO STRICT ❄️"
    elif entry_rate > 35:
        verdict = "TOO LOOSE 🔥"

    print(verdict)
    print("\n✅ Analysis complete\n")

if __name__ == "__main__":
    main()
