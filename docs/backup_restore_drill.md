# Backup Restore Drill

## 1) Create backup

```bash
./scripts/backup_tenant_data.sh
```

It prints:

```text
backup_created=/.../backups/YYYY-MM-DD_HHMMSS.tgz
```

## 2) Run restore drill (local simulation)

```bash
./scripts/restore_drill.sh /path/to/backups/YYYY-MM-DD_HHMMSS.tgz
```

Expected output includes:
- license/payment counts
- tenant dir count
- `restore_drill=PASS`

## 3) Notes

- Drill extracts to `tmp/restore_drill` by default (safe, non-destructive).
- This validates backup readability + core structure (`data/tenants`, `licenses`).
- For production incident recovery, restore into a clean host path, then point service to restored root.
