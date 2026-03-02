#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP=$(mktemp)
(crontab -l 2>/dev/null || true) > "$TMP"

# Remove old entries for this project
grep -v "${ROOT}/scripts/watchdog_bot.sh" "$TMP" | grep -v "${ROOT}/scripts/performance_report.py" > "${TMP}.new" || true
mv "${TMP}.new" "$TMP"

# Every 5 minutes watchdog
printf "*/5 * * * * %s/scripts/watchdog_bot.sh >> %s/logs/watchdog.log 2>&1\n" "$ROOT" "$ROOT" >> "$TMP"
# Daily report 23:55
printf "55 23 * * * %s/scripts/performance_report.py > %s/logs/performance-$(date +\\%F).log 2>&1\n" "$ROOT" "$ROOT" >> "$TMP"

crontab "$TMP"
rm -f "$TMP"
echo "CRON_INSTALLED"
crontab -l | tail -n 5
