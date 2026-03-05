import sqlite3
from datetime import datetime

from bot.paths import get_tenant_paths
from bot.tenant_context import get_current_tenant


def _db_path(tenant_id: str | None = None):
    tid = tenant_id or get_current_tenant()
    return get_tenant_paths(tid)["sqlite_db"]


def init_db(tenant_id: str | None = None):
    db_path = _db_path(tenant_id)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
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
        cols = [r[1] for r in conn.execute("PRAGMA table_info(trade_logs)").fetchall()]
        if "symbol" not in cols:
            conn.execute("ALTER TABLE trade_logs ADD COLUMN symbol TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trade_logs_ts ON trade_logs(ts)")


def log_trade(row: dict, tenant_id: str | None = None):
    db_path = _db_path(tenant_id)
    with sqlite3.connect(db_path) as conn:
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


def count_entries_today_utc(tenant_id: str | None = None) -> int:
    db_path = _db_path(tenant_id)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM trade_logs WHERE result IN ('ENTRY','ENTRY_PAPER','ENTRY_LIVE') AND substr(ts,1,10)=?",
            (today,),
        )
        return int(cur.fetchone()[0])


def fetch_trade_results_since(last_id: int, tenant_id: str | None = None, limit: int = 200):
    db_path = _db_path(tenant_id)
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "SELECT id, result FROM trade_logs WHERE id > ? ORDER BY id ASC LIMIT ?",
            (int(last_id or 0), int(limit or 200)),
        )
        return cur.fetchall()
