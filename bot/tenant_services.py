from __future__ import annotations

import os
import threading
from dataclasses import dataclass

import ccxt

from bot.runtime_store import read_runtime_config_for_tenant
from bot.tenant_store import get_primary_email_for_tenant
from bot.user_api_store import get_user_api


@dataclass
class TenantExchangeHandle:
    tenant_id: str
    exchange: object
    lock: threading.Lock


class TenantServiceLayer:
    """Tenant-scoped runtime + exchange facade for UI read endpoints."""

    def __init__(self):
        self._lock = threading.Lock()
        self._handles: dict[str, TenantExchangeHandle] = {}

    def get_runtime_config(self, tenant_id: str) -> dict:
        return read_runtime_config_for_tenant(tenant_id)

    def _build_exchange(self, tenant_id: str):
        email = get_primary_email_for_tenant(tenant_id)
        api_key = ""
        api_secret = ""
        if email:
            api_key, api_secret = get_user_api(email, tenant_id=tenant_id)

        if not api_key or not api_secret:
            api_key = os.getenv("BINANCE_API_KEY", "")
            api_secret = os.getenv("BINANCE_API_SECRET", "")

        return ccxt.binance(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "future"},
            }
        )

    def exchange_for_tenant(self, tenant_id: str) -> TenantExchangeHandle:
        tid = (tenant_id or "default").strip() or "default"
        with self._lock:
            handle = self._handles.get(tid)
            if handle is None:
                handle = TenantExchangeHandle(
                    tenant_id=tid,
                    exchange=self._build_exchange(tid),
                    lock=threading.Lock(),
                )
                self._handles[tid] = handle
            return handle

    def refresh_tenant_exchange(self, tenant_id: str) -> None:
        tid = (tenant_id or "default").strip() or "default"
        with self._lock:
            self._handles[tid] = TenantExchangeHandle(
                tenant_id=tid,
                exchange=self._build_exchange(tid),
                lock=threading.Lock(),
            )


tenant_services = TenantServiceLayer()
