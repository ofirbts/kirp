#!/usr/bin/env bash
# Validate unified KIRP UI: pages and API endpoints.
# Usage: ./scripts/validate_ui.sh [BASE_URL]
# Default BASE_URL=http://localhost:3100

BASE="${1:-http://localhost:3100}"
API_BASE="${2:-http://localhost:8000}"

echo "=== Validating UI at $BASE ==="

PAGES="/ /dashboard /mission-control /system-control /agents /events /pipeline /content /visuals /signals /run /history /dev /tenants /observability /decisions /graph /governance/audit"
FAILED=0

for path in $PAGES; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE$path" 2>/dev/null || echo "000")
  if [[ "$code" == "200" || "$code" == "302" || "$code" == "307" ]]; then
    echo "[OK] $path -> $code"
  else
    echo "[FAIL] $path -> $code"
    FAILED=$((FAILED + 1))
  fi
done

echo "=== Next.js API routes ==="
for path in /api/health /api/agents /api/history /api/visuals /api/system/ports /api/system/containers /api/brand/templates /api/brand/memory; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE$path" 2>/dev/null || echo "000")
  if [[ "$code" == "200" ]]; then
    echo "[OK] $path -> $code"
  else
    echo "[FAIL] $path -> $code"
    FAILED=$((FAILED + 1))
  fi
done

echo "=== Backend API (optional) ==="
for path in /health /api/v1/stats /api/tenants /api/events /api/agents /api/decisions /api/graph /api/audit; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE$path" 2>/dev/null || echo "000")
  if [[ "$code" == "200" ]]; then
    echo "[OK] $path -> $code"
  else
    echo "[WARN] $path -> $code"
  fi
done

if [[ $FAILED -gt 0 ]]; then
  echo "[FAIL] $FAILED check(s) failed"
  exit 1
fi
echo "[OK] All UI and API route checks passed"
exit 0
