#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

API="${KIRP_API_URL:-http://127.0.0.1:8000}"
POLL_TIMEOUT="${STAGING_SMOKE_POLL_SEC:-180}"
export STAGING_SMOKE_POLL_SEC="$POLL_TIMEOUT"
FAIL=0

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; FAIL=1; }

if ! url_err=$(python3 scripts/staging_tenant_helpers.py "$API" 2>&1); then
  echo "ERROR: $url_err"
  echo "Example: KIRP_API_URL=https://kirp-staging.yourdomain.com ./scripts/staging_tenant_smoke.sh"
  echo "Local: KIRP_API_URL=http://127.0.0.1:8000 SKIP_AUTH=0 ./scripts/staging_tenant_smoke.sh"
  exit 2
fi

token_for() {
  python3 scripts/staging_tenant_helpers.py token "$1" "$2"
}

echo "=== KIRP staging tenant isolation smoke ==="
echo "API=$API"
kafka_hint=$(python3 -c "from scripts.staging_tenant_helpers import kafka_host_hint; print(kafka_host_hint() or '')" 2>/dev/null || true)
if [[ -n "$kafka_hint" ]]; then
  echo "WARN: $kafka_hint"
fi
consumer_hint=$(python3 -c "from scripts.staging_tenant_helpers import kafka_consumer_hint; print(kafka_consumer_hint() or '')" 2>/dev/null || true)
if [[ -n "$consumer_hint" ]]; then
  echo "WARN: $consumer_hint"
fi

TMP_HEALTH="/tmp/kirp-tenant-health.json"
CURL_EXIT=0
HEALTH_CODE=$(curl -sS -o "$TMP_HEALTH" -w "%{http_code}" "$API/health" 2>/dev/null) || CURL_EXIT=$?

if [[ "$CURL_EXIT" -ne 0 ]]; then
  fail "GET /health unreachable (curl exit $CURL_EXIT — check host, DNS, VPN, TLS)"
elif [[ "$HEALTH_CODE" == "200" ]]; then
  pass "GET /health"
else
  fail "GET /health HTTP $HEALTH_CODE"
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "=== FAILED (fix API reachability first) ==="
  exit 1
fi

if [[ "${SKIP_AUTH:-0}" == "1" ]]; then
  echo "NOTE: SKIP_AUTH=1 — tenant JWT checks skipped."
  echo "      KIRP_API_URL=$API SKIP_AUTH=0 ./scripts/staging_tenant_smoke.sh"
  echo "=== PASSED (health only; auth checks skipped) ==="
  exit 0
fi

TOKEN_A=$(token_for "user_a" "tenant_a")
TOKEN_B=$(token_for "user_b" "tenant_b")
MARKER="tenant-smoke-$(date +%s)"

INGEST_A=$(curl -sS -o /tmp/kirp-tenant-ingest-a.json -w "%{http_code}" \
  -X POST "$API/api/v1/ingest" \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d "{\"content\":\"$MARKER\",\"source\":\"tenant_smoke\"}" 2>/dev/null) || INGEST_A="000"

if [[ "$INGEST_A" == "200" ]]; then
  pass "POST /api/v1/ingest tenant_a"
  echo "NOTE: first kafka message after consumer restart can take 60-90s (RAG/Qdrant cold start)"
else
  detail=$(python3 -c "import json; print(json.load(open('/tmp/kirp-tenant-ingest-a.json')).get('detail',''))" 2>/dev/null || true)
  fail "POST /api/v1/ingest tenant_a HTTP $INGEST_A ${detail:+(detail: $detail)}"
  echo "Hint: token must be signed with the same JWT_SECRET as the API (.env)"
  echo "=== FAILED ==="
  exit 1
fi

if python3 scripts/staging_tenant_helpers.py poll "$API" "$TOKEN_A" "$MARKER"; then
  pass "tenant_a sees own marker in EventStore (within ${POLL_TIMEOUT}s)"
else
  fail "tenant_a missing own marker after ${POLL_TIMEOUT}s (ingest pipeline can take ~100s — retry or STAGING_SMOKE_POLL_SEC=180)"
fi

LIST_B=$(curl -sS "$API/api/v1/events?limit=200" -H "Authorization: Bearer $TOKEN_B" 2>/dev/null || echo "{}")
if echo "$LIST_B" | python3 -c "import json,sys; from scripts.staging_tenant_helpers import events_json_contains_marker; sys.exit(0 if not events_json_contains_marker(sys.stdin.read(), sys.argv[1]) else 1)" "$MARKER" 2>/dev/null; then
  pass "tenant_b cannot see tenant_a marker"
else
  fail "tenant_b leaked tenant_a marker"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== ALL PASSED ==="
  exit 0
fi
echo "=== FAILED ==="
exit 1
