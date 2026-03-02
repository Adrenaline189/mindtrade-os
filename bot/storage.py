import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "trading_bot.db"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                candle_time TEXT,
                symbol TEXT,
                bias TEXT,
                close REAL,
                rsi REAL,
                golden_zone INTEGER,
                result TEXT,
                note TEXT
            )
            """
        )
        # migration (older db)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(trade_logs)").fetchall()]
        if "symbol" not in cols:
            conn.execute("ALTER TABLE trade_logs ADD COLUMN symbol TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trade_logs_ts ON trade_logs(ts)")


def log_trade(row: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO trade_logs (ts, candle_time, symbol, bias, close, rsi, golden_zone, result, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(),
                str(row.get("time", "")),
                row.get("symbol"),
                row.get("bias"),
                row.get("close"),
                row.get("rsi"),
                1 if row.get("golden_zone") else 0,
                row.get("result"),
                row.get("note"),
            ),
        )


def count_entries_today_utc() -> int:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM trade_logs WHERE result IN ('ENTRY','ENTRY_PAPER','ENTRY_LIVE') AND substr(ts,1,10)=?",
            (today,),
        )
        return int(cur.fetchone()[0])
