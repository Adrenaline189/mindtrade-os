import threading

from bot.config_runtime import RUNTIME_CONFIG
from bot.engine import run_engine, set_active_tenant
from bot.runtime_store import load_runtime_config
from bot.state import bot_state


class EngineManager:
    """
    Phase 1: single shared engine process.
    TODO: spawn one worker per tenant in Phase 2.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._active_tenant_id = "default"

    @property
    def active_tenant_id(self) -> str:
        return self._active_tenant_id

    def start(self, tenant_id: str) -> bool:
        with self._lock:
            self._active_tenant_id = tenant_id or self._active_tenant_id
            set_active_tenant(self._active_tenant_id)
            load_runtime_config(self._active_tenant_id)
            RUNTIME_CONFIG["MODE"] = "LIVE"
            RUNTIME_CONFIG["ALLOW_LIVE_ORDERS"] = True
            if bot_state["running"]:
                return False
            bot_state["running"] = True
            threading.Thread(target=run_engine, daemon=True).start()
            return True

    def stop(self):
        with self._lock:
            bot_state["running"] = False


engine_manager = EngineManager()
