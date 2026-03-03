# Multi-tenant Phase 3 (full parallelization)

Phase 3 removes the main bottlenecks that still serialized tenant execution in Phase 2.

## What changed

### 1) Tenant-scoped service layer for UI read paths
- Added `bot/tenant_services.py`.
- UI read endpoints now resolve runtime + exchange through tenant scope instead of global `bot.engine.exchange` + global `RUNTIME_CONFIG`.
- Updated endpoints:
  - `/api/summary`, `/api/tenant/{tenant_id}/summary`
  - `/api/chart`
  - `/api/connection`
  - `/api/open-positions`
  - `/api/futures-balance`
  - `/api/leverage`

### 2) Removed global worker isolation bottleneck
- `TenantWorkerManager` no longer injects one process-wide engine lock.
- Workers now receive **per-tenant isolation lock** only.
- This allows concurrent tenant cycles without cross-tenant serialization.

### 3) Hardened worker recovery and containment
- Worker runs are wrapped with guarded execution (`_run_worker`).
- Crashes are captured into per-tenant state:
  - `last_error`
  - `crashed`
- Status now includes `ticks` and crash fields to simplify diagnostics.

### 4) Runtime baseline isolation
- Added `DEFAULT_RUNTIME_CONFIG` immutable baseline.
- `read_runtime_config_for_tenant()` now clones from baseline instead of mutable process-global runtime.

## Smoke test coverage

Extended `scripts/smoke_multi_tenant_workers.py` to assert:
- concurrent starts for **>=3 tenants**
- idempotent start behavior
- isolated per-tenant state tags
- isolated per-tenant metric markers
- clean stop path for all tenants

Run:

```bash
python3 scripts/smoke_multi_tenant_workers.py
```

## Rollout checklist

- [ ] Deploy Phase 3 build to staging.
- [ ] Run:
  - `python3 scripts/smoke_workers.py`
  - `python3 scripts/smoke_multi_tenant_workers.py`
- [ ] Verify `/admin/workers` shows multiple tenants running concurrently.
- [ ] Verify `/api/tenant/{tenant_id}/summary` returns isolated positions/metrics per tenant.
- [ ] Confirm no `crashed=true` or unexpected `last_error` in worker statuses.
- [ ] Roll to production with canary tenants first.

## Risk notes

1. **Exchange client cache lifecycle**
   - Tenant exchange clients are cached in-process.
   - If API keys rotate, call `tenant_services.refresh_tenant_exchange(tenant_id)` or restart process.

2. **Read-path latency under high tenant count**
   - UI endpoints now do tenant-scoped exchange reads; this is isolated but can increase aggregate outbound exchange calls.

3. **Legacy write endpoints still use global `RUNTIME_CONFIG` mutation pattern**
   - They are scoped by tenant on save/load, but internal mutation model remains mutable-global in request handler.
   - Safe enough for current topology, but future step is pure request-local config objects.
