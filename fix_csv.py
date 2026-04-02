import csv
import os

INPUT = "data/paper_trades.csv"
OUTPUT = "data/paper_trades_fixed.csv"

# โครงสร้างคอลัมน์มาตรฐาน (ใช้ทั้งระบบ)
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
    print("🔧 Fixing CSV format (raw mode)...")

    fixed_rows = []

    with open(INPUT, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)  # อ่าน header เดิม (ทิ้งไป)

        for row in reader:
            # สร้าง dict เปล่าตามโครงสร้างมาตรฐาน
            data = {col: None for col in COLUMNS}

            # map ตามจำนวน field ที่มีจริงในแถว
            for i, value in enumerate(row):
                if i < len(COLUMNS):
                    data[COLUMNS[i]] = value

            fixed_rows.append(data)

    # เขียนไฟล์ใหม่
    with open(OUTPUT, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(fixed_rows)

    print("✅ CSV fixed successfully")
    print(f"➡️ Output file: {OUTPUT}")
    print("👉 Ready for analysis\n")

if __name__ == "__main__":
    main()
