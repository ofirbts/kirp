#!/usr/bin/env bash
set -euo pipefail

API="${KIRP_API_URL:-http://127.0.0.1:8000}"
FAIL=0

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; FAIL=1; }

json_get() {
  python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)" 2>/dev/null || echo ""
}

echo "=== KIRP shadow pilot smoke ==="
echo "API=$API"

HEALTH=$(curl -sS "$API/health" || echo "{}")
HEALTH_CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API/health" || echo "000")
if [[ "$HEALTH_CODE" == "200" ]]; then
  pass "GET /health"
else
  fail "GET /health code=$HEALTH_CODE"
fi

MODE=$(echo "$HEALTH" | json_get "['telemetry']['governed_runtime_mode']")
if [[ "$MODE" == "shadow" ]]; then
  pass "governed_runtime_mode=shadow"
else
  fail "governed_runtime_mode=$MODE (expected shadow; set KIRP_GOVERNED_RUNTIME_MODE=shadow on API)"
fi

SEED_CODE=$(curl -sS -o /tmp/kirp-shadow-seed.json -w "%{http_code}" -X POST "$API/api/v1/traces/dev/seed?reset=true" || echo "000")
if [[ "$SEED_CODE" == "200" ]]; then
  pass "POST /api/v1/traces/dev/seed"
else
  fail "POST /api/v1/traces/dev/seed code=$SEED_CODE"
fi

BAD=$(curl -sS "$API/api/v1/trace/demo-trace-bad?include_full=true&include_governed_runtime=true" || echo "{}")
WOULD=$(echo "$BAD" | json_get "['governed_runtime']['would_block']")
ALLOW=$(echo "$BAD" | json_get "['governed_runtime']['allow_execute']")
MODE_RT=$(echo "$BAD" | json_get "['governed_runtime']['mode']")

if [[ "$WOULD" == "True" ]]; then
  pass "demo-trace-bad would_block in shadow pilot"
else
  fail "demo-trace-bad would_block=$WOULD"
fi

if [[ "$ALLOW" == "True" && "$MODE_RT" == "shadow" ]]; then
  pass "shadow allows execute despite would_block"
else
  fail "allow_execute=$ALLOW mode=$MODE_RT (shadow must allow execute)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== ALL PASSED ==="
  exit 0
fi
echo "=== FAILURES ==="
exit 1
