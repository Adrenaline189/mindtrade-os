import csv

INPUT = "data/paper_trades_fixed.csv"
OUTPUT = "data/paper_trades_final.csv"

COLUMNS = [
    "time",
    "bias",
    "close",
    "ema50",
    "ema200",
    "rsi",
    "distance_ema50",
    "golden_zone",
    "entry",
    "sl",
    "sl_percent",
    "tp1_percent",
    "tp2_percent",
    "position_size",
    "result",
]

def main():
    print("🧠 Realigning CSV result column...")

    fixed = []

    with open(INPUT, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)

        for row in reader:
            data = {col: None for col in COLUMNS}

            # ใส่ค่าตามตำแหน่งก่อน
            for i, val in enumerate(row):
                if i < len(COLUMNS):
                    data[COLUMNS[i]] = val

            # ถ้า result ยังว่าง → หา ENTRY / SKIP ในทั้งแถว
            if data["result"] not in ("ENTRY", "SKIP"):
                for v in row:
                    if v in ("ENTRY", "SKIP"):
                        data["result"] = v
                        break

            fixed.append(data)

    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(fixed)

    print("✅ CSV realigned")
    print(f"➡️ Output: {OUTPUT}")
    print("👉 Use this file for analysis")

if __name__ == "__main__":
    main()
