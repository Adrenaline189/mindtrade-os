from pathlib import Path

from bot.tenant_context import default_tenant_id

ROOT = Path(__file__).resolve().parents[1]


def tenant_dir(tenant_id: str) -> Path:
    tid = (tenant_id or default_tenant_id()).strip()
    return ROOT / "data" / "tenants" / tid


def get_tenant_paths(tenant_id: str) -> dict:
    base = tenant_dir(tenant_id)
    return {
        "base": base,
        "runtime_config": base / "runtime_config.json",
        "trades_csv": base / "paper_trades.csv",
        "sqlite_db": base / "trading_bot.db",
        "api_key_db": base / "user_api_keys.json",
    }
