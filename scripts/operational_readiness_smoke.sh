#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

API="${KIRP_API_URL:-http://127.0.0.1:8002}"
export KIRP_API_URL="$API"
FAIL=0

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; FAIL=1; }

echo "=== KIRP operational readiness ==="
echo "API=$API"

if python3 scripts/tenant_isolation_gate.py; then
  pass "tenant_isolation_gate"
else
  fail "tenant_isolation_gate"
fi

if bash scripts/staging_tenant_smoke.sh; then
  pass "staging_tenant_smoke"
else
  fail "staging_tenant_smoke"
fi

if bash scripts/telemetry_smoke.sh; then
  pass "telemetry_smoke"
else
  fail "telemetry_smoke"
fi

if bash scripts/shadow_pilot_smoke.sh; then
  pass "shadow_pilot_smoke"
else
  fail "shadow_pilot_smoke"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== OPERATIONAL READINESS: ALL PASSED ==="
  exit 0
fi
echo "=== OPERATIONAL READINESS: FAILED ==="
exit 1
