#!/usr/bin/env bash
set -euo pipefail

API="${KIRP_API_URL:-http://127.0.0.1:8002}"
FAIL=0

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; FAIL=1; }

json_get() {
  python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)" 2>/dev/null || echo ""
}

echo "=== KIRP telemetry smoke ==="
echo "API=$API"

HEALTH_CODE=$(curl -sS -o /tmp/kirp-smoke-health.json -w "%{http_code}" "$API/health" || echo "000")
if [[ "$HEALTH_CODE" == "200" ]]; then
  pass "GET /health"
else
  fail "GET /health code=$HEALTH_CODE"
fi

SEED_CODE=$(curl -sS -o /tmp/kirp-smoke-seed.json -w "%{http_code}" -X POST "$API/api/v1/traces/dev/seed?reset=true" || echo "000")
if [[ "$SEED_CODE" == "200" ]]; then
  pass "POST /api/v1/traces/dev/seed"
else
  fail "POST /api/v1/traces/dev/seed code=$SEED_CODE (need ENV=development on API; optional KIRP_TRACE_LOG_PATH)"
fi

TRACE_HEALTH=$(curl -sS "$API/api/v1/traces/health" || echo "{}")
OK=$(echo "$TRACE_HEALTH" | json_get "['ok']")
if [[ "$OK" == "True" ]]; then
  pass "GET /api/v1/traces/health ok"
else
  fail "GET /api/v1/traces/health ok=$OK"
fi

STAGES=$(curl -sS "$API/api/v1/trace/demo-trace-1?include_full=true" | json_get "['timeline']['total_stages']")
if [[ "$STAGES" == "5" ]]; then
  pass "demo-trace-1 total_stages=5"
else
  fail "demo-trace-1 total_stages=$STAGES"
fi

DRIFT=$(curl -sS "$API/api/v1/trace/demo-trace-bad?include_full=true&baseline_trace_id=demo-trace-1" | json_get "['policy_drift']['drift_detected']")
if [[ "$DRIFT" == "True" ]]; then
  pass "demo-trace-bad drift_detected"
else
  fail "demo-trace-bad drift_detected=$DRIFT"
fi

BLOCK=$(curl -sS "$API/api/v1/trace/demo-trace-bad?include_full=true" | json_get "['governed_runtime']['would_block']")
if [[ "$BLOCK" == "True" ]]; then
  pass "demo-trace-bad would_block"
else
  fail "demo-trace-bad would_block=$BLOCK"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== ALL PASSED ==="
  exit 0
fi
echo "=== FAILURES ==="
exit 1
