import os
from pathlib import Path

def _root() -> Path:
    """Get project root, overridable via MINDTRADE_ROOT env var."""
    if os.getenv("MINDTRADE_ROOT"):
        return Path(os.getenv("MINDTRADE_ROOT"))
    return Path(__file__).resolve().parents[1]

def get_tenant_paths(tenant_id: str) -> dict:
    """
    Returns all paths for a tenant, derived from MINDTRADE_DATA_ROOT (default: <root>/data).
    """
    data_root = os.getenv("MINDTRADE_DATA_ROOT", str(_root() / "data"))
    tenant_root = Path(data_root) / "tenants" / tenant_id
    return {
        "root": tenant_root,
        "base": tenant_root,  # legacy alias
        "runtime_config": tenant_root / "runtime_config.json",
        "trades_csv": tenant_root / "paper_trades.csv",  # legacy path
        "sqlite_db": tenant_root / "trading_bot.db",  # legacy path
        "state_json": tenant_root / "state.json",
        "api_key_db": tenant_root / "user_api_keys.json",
        "logs": tenant_root / "logs",
    }

def get_license_root() -> Path:
    """License data root, overridable via MINDTRADE_LICENSE_ROOT env var."""
    if os.getenv("MINDTRADE_LICENSE_ROOT"):
        return Path(os.getenv("MINDTRADE_LICENSE_ROOT"))
    return _root() / "licenses"
