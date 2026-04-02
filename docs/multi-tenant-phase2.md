# Multi-tenant Phase 2 (foundation + 2.1 hardening)

Phase 2 introduces a **per-tenant worker manager** while keeping existing routes and behavior backward-compatible.

## What was added

- `bot/tenant_worker_manager.py`
  - `TenantWorkerManager.start(tenant_id)`
  - `TenantWorkerManager.stop(tenant_id)` / `stop_all()`
  - `TenantWorkerManager.status(tenant_id)`
  - `TenantWorkerManager.list_status()`
  - Phase 2.1 safety:
    - stale thread record cleanup
    - idempotent start semantics (`already_running=true` if start called twice)
    - stop timeout diagnostics (`stop_timed_out`, `stop_timeout_sec`)
- `bot/engine.py`
  - new tenant-scoped `EngineContext` (`tenant_id`, `runtime_config`, `exchange`, `state`)
  - worker loop now uses tenant context for runtime/exchange operations
  - runtime config loaded per tenant into context via `read_runtime_config_for_tenant()`
  - storage writes use explicit `tenant_id`
- `bot/runtime_store.py`
  - new `read_runtime_config_for_tenant(tenant_id)` (non-global read)
  - legacy `load_runtime_config()` preserved for compatibility
- `bot/engine_manager.py`
  - stop APIs support timeout passthrough
- `ui/app.py`
  - tenant metrics helper used by summary/performance
  - new tenant-level endpoints:
    - `GET /api/tenant/{tenant_id}/summary`
    - `GET /api/tenant/{tenant_id}/performance`
    - `GET /api/tenant/{tenant_id}/pnl`
  - convenience endpoint for current tenant:
    - `GET /api/pnl`
  - admin worker stop accepts timeout:
    - `POST /admin/workers/stop` form `tenant_id`, optional `timeout_sec`
- `scripts/smoke_multi_tenant_workers.py`
  - concurrent start/stop smoke check
  - tenant state isolation assertions
  - idempotent start assertion

## Isolation strategy (safe-first)

Some legacy paths still rely on module-level globals (`RUNTIME_CONFIG`, shared `exchange` in UI read APIs).
To prevent cross-tenant leakage in workers, workers continue to use a global isolation lock per tick:

1. load tenant runtime config into worker-local context
2. run one cycle with tenant context (runtime + exchange + state)
3. release lock

This is conservative (less parallel throughput) but strict on isolation and low-risk for production.

## Admin APIs (worker control)

- `GET /admin/workers` → list all worker statuses
- `GET /admin/workers/{tenant_id}` → worker status for one tenant
- `POST /admin/workers/start` (form: `tenant_id`)
- `POST /admin/workers/stop` (form: `tenant_id`, optional `timeout_sec`)

Example:

```bash
curl -X POST -F "tenant_id=default" http://127.0.0.1:8000/admin/workers/start
curl http://127.0.0.1:8000/admin/workers
curl -X POST -F "tenant_id=default" -F "timeout_sec=15" http://127.0.0.1:8000/admin/workers/stop
```

## Tenant reporting APIs

```bash
# current session tenant
curl http://127.0.0.1:8000/api/summary
curl http://127.0.0.1:8000/api/performance
curl http://127.0.0.1:8000/api/pnl

# explicit tenant
curl http://127.0.0.1:8000/api/tenant/default/summary
curl http://127.0.0.1:8000/api/tenant/default/performance
curl http://127.0.0.1:8000/api/tenant/default/pnl
```

## Backward compatibility

- Existing `/start` and `/stop` still work.
- `/start` starts the current session tenant worker.
- `/stop` stops the current session tenant worker.
- Legacy single-tenant usage remains valid.
- Existing global imports (`from bot.engine import exchange, apply_leverage_settings`) still work.

## Production caveats (important)

1. **Engine worker loop is isolation-safe but still lock-serialized** due to remaining global dependencies.
2. **UI read APIs still use process-level exchange client** (`bot.engine.exchange`) for market/balance snapshots.
3. `load_runtime_config()` still mutates global `RUNTIME_CONFIG`; keep using tenant-local read in worker paths.
4. If stop timeout occurs (`stop_timed_out=true`), worker may still be winding down; check status before restart.

## Rollout checklist (Phase 2.1)

- [ ] Deploy with one tenant first (`default`) and verify `/health`, `/admin/workers`.
- [ ] Run smoke checks:
  - `python3 scripts/smoke_workers.py`
  - `python3 scripts/smoke_multi_tenant_workers.py`
- [ ] Verify per-tenant metrics endpoint responses are isolated.
- [ ] Validate start idempotency and stop timeout status flags.
- [ ] Monitor logs for 24h for unexpected `ALERT_ON_ERROR` spikes.

## Next rollout step (Phase 3)

To unlock true parallel tenant execution without the global lock:
- remove remaining global runtime config usage from UI/service flows
- move UI read endpoints to tenant-specific exchange clients
- make engine loop fully pure/context-injected (no fallback to globals)
