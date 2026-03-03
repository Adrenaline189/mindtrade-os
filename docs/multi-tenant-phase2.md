# Multi-tenant Phase 2 (foundation)

Phase 2 introduces a **per-tenant worker manager** while keeping existing routes and behavior backward-compatible.

## What was added

- `bot/tenant_worker_manager.py`
  - `TenantWorkerManager.start(tenant_id)`
  - `TenantWorkerManager.stop(tenant_id)` / `stop_all()`
  - `TenantWorkerManager.status(tenant_id)`
  - `TenantWorkerManager.list_status()`
- `bot/engine.py`
  - new `run_engine_for_tenant(tenant_id, stop_event, state, isolation_lock)`
  - legacy `run_engine()` now wraps the new runner for compatibility
- `bot/engine_manager.py`
  - now a facade over `TenantWorkerManager`
- `ui/app.py`
  - worker-aware running status per tenant
  - new admin worker APIs

## Isolation strategy (safe-first)

Current engine internals still use shared globals (`RUNTIME_CONFIG`, shared exchange instance, legacy helpers).
To avoid cross-tenant leakage in this phase, workers use a global isolation lock per tick:

1. enter tenant scope
2. load that tenant runtime config
3. run one cycle for that tenant
4. release lock

This is conservative (less parallel throughput) but strict on tenant context isolation and low-risk.

## Admin APIs (worker control)

- `GET /admin/workers` → list all worker statuses
- `GET /admin/workers/{tenant_id}` → worker status for one tenant
- `POST /admin/workers/start` (form: `tenant_id`)
- `POST /admin/workers/stop` (form: `tenant_id`)

Example:

```bash
curl -X POST -F "tenant_id=default" http://127.0.0.1:8000/admin/workers/start
curl http://127.0.0.1:8000/admin/workers
curl -X POST -F "tenant_id=default" http://127.0.0.1:8000/admin/workers/stop
```

## Backward compatibility

- Existing `/start` and `/stop` still work.
- `/start` starts the current session tenant worker.
- `/stop` stops the current session tenant worker.
- Legacy single-tenant usage remains valid.

## Next rollout step (Phase 2.1/3)

To unlock true parallel tenant execution without global lock:
- move runtime config/state from globals to per-worker objects
- create per-worker exchange client/session
- make engine loop pure/context-injected
