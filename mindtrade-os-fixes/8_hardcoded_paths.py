"""
FIX 8: Replace hardcoded paths with environment-based configurable paths

STEP 1: In bot/paths.py - REPLACE the entire file with this:

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
        "trades_csv": tenant_root / "trades.csv",
        "state_json": tenant_root / "state.json",
        "api_key_db": tenant_root / "api_keys.json",
        "logs": tenant_root / "logs",
    }

def get_license_root() -> Path:
    """License data root, overridable via MINDTRADE_LICENSE_ROOT env var."""
    if os.getenv("MINDTRADE_LICENSE_ROOT"):
        return Path(os.getenv("MINDTRADE_LICENSE_ROOT"))
    return _root() / "licenses"

# Update license_service.py to use the new function:
# Replace: ROOT = Path(__file__).resolve().parents[1]
#          DB = ROOT / 'licenses' / 'licenses.json'
# With:
#          from bot.paths import get_license_root
#          DB = get_license_root() / 'licenses.json'

# Update tenant_store.py similarly:
# Replace: ROOT = Path(__file__).resolve().parents[1]
#          DB = ROOT / "licenses" / "tenants.json"
# With:
#          from bot.paths import get_license_root
#          DB = get_license_root() / "tenants.json"


STEP 2: In .env.example, ADD these new environment variables:

# Path configuration (optional - defaults work out of the box)
# MINDTRADE_ROOT=/path/to/mindtrade-os
# MINDTRADE_DATA_ROOT=/path/to/mindtrade-os/data
# MINDTRADE_LICENSE_ROOT=/path/to/mindtrade-os/licenses


STEP 3: Update .gitignore to allow .env to override paths:
# (no change needed - .env is already gitignored)


BENEFIT: Now you can install the bot in any location and data stays in a
consistent, configurable location — critical for Windows installer and
multi-tenant deployments.
"""
