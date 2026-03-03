# Multi-tenant Isolation (Phase 1)

## What is implemented

- Tenant model mapping from logged-in user email -> `tenant_id`
  - Stored in `licenses/tenants.json`
- Per-tenant runtime/config and data paths under:
  - `data/tenants/<tenant_id>/runtime_config.json`
  - `data/tenants/<tenant_id>/paper_trades.csv`
  - `data/tenants/<tenant_id>/trading_bot.db`
  - `data/tenants/<tenant_id>/user_api_keys.json`
- UI endpoints now resolve tenant context from session and operate against tenant files:
  - dashboard (`/`)
  - summary/events/performance/chart APIs
  - runtime settings updates
  - API key save/test
- EngineManager abstraction introduced (`bot/engine_manager.py`)
  - Phase 1 still runs a **single engine process**
  - tracks active tenant and starts engine in that tenant context

## Limitations (Phase 1)

1. Single shared engine process only.
2. If two tenants update settings concurrently, only active engine tenant config is applied to running bot.
3. Live exchange connection is still shared process-wide.

## Planned Phase 2

- Spawn one worker/engine per tenant.
- Isolate exchange clients and in-memory bot state per worker.
- Add admin control plane for tenant worker lifecycle.
