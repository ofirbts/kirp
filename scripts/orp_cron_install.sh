#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MARKER="# kirp-orp-daily"
CRON_LINE="0 9 * * * cd ${ROOT_DIR} && KIRP_API_URL=\${KIRP_API_URL:-http://127.0.0.1:8000} SKIP_AUTH=0 STAGING_SMOKE_POLL_SEC=180 ./scripts/orp_daily.sh >> ${ROOT_DIR}/artifacts/operational_readiness/cron.log 2>&1"
existing="$(crontab -l 2>/dev/null || true)"
if echo "$existing" | grep -Fq "$MARKER"; then
  echo "ORP cron already installed"
  exit 0
fi
{
  echo "$existing"
  echo "$CRON_LINE $MARKER"
} | crontab -
echo "Installed ORP daily cron (09:00 local): orp_daily.sh"
crontab -l | grep -F "$MARKER" || true
