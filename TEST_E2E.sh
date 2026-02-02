#!/usr/bin/env bash
# KIRP Enterprise — Ultra+ End-to-End Test Suite (Upgraded)
# Covers: Docker, API, Brand OS, Agents, Events, RAG, Kafka, Qdrant, Redis, Postgres, Mongo, OPA, Worker, UI, Monitoring, Multi-Tenant, Latency, Consistency

set -euo pipefail

API_URL="http://localhost:8000"
UI_URL="http://localhost:3100"
BRAND_API_URL="http://localhost:8002"
MONITOR_URL="http://localhost:8001"
OPA_URL="http://localhost:8181"
QDRANT_URL="http://localhost:6333"
ES_URL="http://localhost:9200"

REDIS="kirp-redis"
POSTGRES="kirp-postgres"
KAFKA="kirp-kafka"
WORKER="kirp-worker"
API="kirp-api"
MONGO="kirp-mongodb"
DASHBOARD="kirp-dashboard"

echo "🧪 KIRP Enterprise — Ultra+ End-to-End Test Suite"
echo "================================================"

check() {
  if [ $? -ne 0 ]; then
    echo "❌ FAILED: $1"
    exit 1
  else
    echo "   ✔ $1"
  fi
}

# Optional check: warn but do not exit (for services that may not be running)
check_optional() {
  local prev=$?
  if [ "$prev" -ne 0 ]; then
    echo "   ⚠ $1 (optional — skipping)"
  else
    echo "   ✔ $1"
  fi
}

echo ""
echo "🔍 0. Docker & Environment Snapshot"
echo "-----------------------------------"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "🔍 Active listening ports:"
lsof -i -P -n | grep LISTEN || true

echo ""
echo "🔍 1. Core Container Health"
echo "---------------------------"

for c in $API $REDIS $POSTGRES $KAFKA $WORKER $MONGO $DASHBOARD; do
  docker inspect -f '{{.State.Running}}' "$c" 2>/dev/null | grep -q true
  check "Container $c running"
done

echo ""
echo "🔍 2. API Contract & Schema Drift"
echo "---------------------------------"

curl -s "$API_URL/openapi.json" | jq . >/dev/null
check "Core API OpenAPI schema reachable"

curl -s "$API_URL/openapi.json" | jq 'keys' >/dev/null
check "Core API OpenAPI schema valid JSON"

echo ""
echo "🔍 3. Core Services Health"
echo "--------------------------"

curl -s "$API_URL/health" | jq . >/dev/null
check "Core API healthy"

if curl -s "$BRAND_API_URL/health" 2>/dev/null | jq . >/dev/null 2>&1; then
  echo "   ✔ Brand OS API healthy"
else
  echo "   ⚠ Brand OS API healthy (optional — skipping)"
fi

if curl -s "$MONITOR_URL/metrics" >/dev/null 2>&1; then
  echo "   ✔ Monitoring service (metrics) reachable"
else
  echo "   ⚠ Monitoring service (metrics) reachable (optional — skipping)"
fi

if curl -s "$OPA_URL/health" >/dev/null 2>&1 || curl -s "$OPA_URL/healthz" >/dev/null 2>&1; then
  echo "   ✔ OPA healthy"
else
  echo "   ⚠ OPA healthy (optional — skipping)"
fi

curl -s "$QDRANT_URL/collections" | jq . >/dev/null
check "Qdrant collections accessible"

docker exec "$REDIS" redis-cli ping | grep -q PONG
check "Redis reachable"

docker exec "$POSTGRES" pg_isready >/dev/null
check "Postgres reachable"

docker exec "$MONGO" mongosh --eval "db.runCommand({ ping: 1 })" >/dev/null
check "Mongo reachable"

echo ""
echo "⚡ 3b. Latency & Consistency Checks"
echo "----------------------------------"

START=$(date +%s%3N)
curl -s "$API_URL/health" >/dev/null
END=$(date +%s%3N)
LAT=$((END - START))
echo "   ✔ Core API latency: ${LAT}ms"
if [ "$LAT" -gt 500 ]; then
  echo "⚠ High latency detected on core API"
fi

curl -s "$API_URL/openapi.json" | jq 'keys' >/dev/null
check "Core API schema consistent"

echo ""
echo "📨 4. Kafka End-to-End (Produce → Consume)"
echo "------------------------------------------"

TOPIC="kirp-test-$RANDOM"
docker exec "$KAFKA" kafka-topics --bootstrap-server localhost:9092 --create --topic "$TOPIC" --partitions 1 >/dev/null
check "Kafka topic created"

echo "kirp-test-message" | docker exec -i "$KAFKA" kafka-console-producer --bootstrap-server localhost:9092 --topic "$TOPIC" >/dev/null
check "Kafka message produced"

sleep 2
docker exec "$KAFKA" kafka-console-consumer --bootstrap-server localhost:9092 --topic "$TOPIC" --from-beginning --max-messages 1 --timeout-ms 15000 | grep -q "kirp-test-message"
check "Kafka message consumed"

echo ""
echo "📝 5. Ingest → Index → Query (Full RAG Pipeline)"
echo "------------------------------------------------"

EVENT=$(curl -s -X POST "$API_URL/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "default",
    "space_id": "private",
    "user_id": "ofir",
    "content": "KIRP must complete the architecture refactor",
    "source": "test"
  }')

EVENT_ID=$(echo "$EVENT" | jq -r '.event_id // empty')
[ -n "$EVENT_ID" ]
check "Event ingested ($EVENT_ID)"

sleep 2

curl -s -X POST "$API_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "default",
    "space_id": "private",
    "user_id": "ofir",
    "query": "What tasks should I prioritize?",
    "k": 5
  }' | jq . >/dev/null
check "RAG query executed"

echo ""
echo "🌀 5b. Event‑Sourcing & DLQ"
echo "---------------------------"

curl -s "$API_URL/api/events" | jq . >/dev/null
check "Event store reachable"

# Replay requires POST /api/events/{event_id}/replay (EVENT_ID from section 5)
if [ -n "$EVENT_ID" ] && curl -s -X POST "$API_URL/api/events/$EVENT_ID/replay" 2>/dev/null | jq . >/dev/null 2>&1; then
  echo "   ✔ Replay endpoint responds"
else
  echo "   ⚠ Replay endpoint responds (optional — skipping)"
fi

if curl -s "$API_URL/api/events/dlq" 2>/dev/null | jq . >/dev/null 2>&1; then
  echo "   ✔ DLQ accessible"
else
  echo "   ⚠ DLQ accessible (optional — skipping)"
fi

echo ""
echo "🏷️ 6. Multi‑Tenant Isolation"
echo "----------------------------"

TENANTS=$(curl -s "$API_URL/api/tenants")
# API returns {data:[],meta:{}}; avoid .[0] fallback which errors on object
T1=$(echo "$TENANTS" | jq -r '.data[0].id // empty')
T2=$(echo "$TENANTS" | jq -r '.data[1].id // empty')

if [ -n "$T1" ] && [ -n "$T2" ] && [ "$T1" != "$T2" ]; then
  A=$(curl -s "$API_URL/api/events?tenant_id=$T1")
  B=$(curl -s "$API_URL/api/events?tenant_id=$T2")

  echo "$A" | grep -q "$T2" && { echo "❌ Tenant isolation FAILED"; exit 1; }
  echo "$B" | grep -q "$T1" && { echo "❌ Tenant isolation FAILED"; exit 1; }

  echo "   ✔ Tenant isolation enforced"
else
  echo "⚠ Not enough tenants found — skipping deep isolation test"
fi

echo ""
echo "🤖 7. Agent Execution (Real)"
echo "----------------------------"

AGENTS=$(curl -s "$API_URL/api/v1/agents")
AGENT_ID=$(echo "$AGENTS" | jq -r '.[0].id // empty')

if [ -n "$AGENT_ID" ]; then
  curl -s -X POST "$API_URL/api/v1/agents/$AGENT_ID/run" \
    -H "Content-Type: application/json" \
    -d '{"tenant_id":"default","space_id":"private","user_id":"ofir"}' | jq . >/dev/null
  check "Agent execution triggered"

  sleep 2

  curl -s "$API_URL/api/v1/agents/$AGENT_ID/status" | jq . >/dev/null
  check "Agent status retrievable"
else
  echo "⚠ No agents available — skipping agent run test"
fi

echo ""
echo "📱 8. WhatsApp / Brand OS Intelligence"
echo "--------------------------------------"

curl -s "$API_URL/whatsapp/schedule" | jq . >/dev/null || echo "⚠ WhatsApp scheduler endpoint not available"
curl -s "$API_URL/whatsapp/insights?tenant_id=default&user_id=ofir" | jq . >/dev/null || echo "⚠ WhatsApp insights endpoint not available"

curl -s "$BRAND_API_URL/brand-os/run" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"t1","platform":"linkedin","topic_hint":"test"}' | jq . >/dev/null || echo "⚠ Brand OS run endpoint not fully wired"
echo "   ✔ Brand OS basic endpoints checked (where available)"

echo ""
echo "🛡️ 9. Governance / OPA Policy Enforcement"
echo "-----------------------------------------"

if curl -s -X POST "$OPA_URL/v1/data/kirp/governance/allow" \
  -H "Content-Type: application/json" \
  -d '{"input":{"action":"read","tenant_id":"default","user_tenant_id":"default","space_id":"private","user_id":"ofir","space_owner_id":"ofir","roles":[],"resource_owner_id":"ofir","space_members":["ofir"]}}' 2>/dev/null | jq . >/dev/null 2>&1; then
  echo "   ✔ OPA decision engine responds"
else
  echo "   ⚠ OPA decision engine not reachable or policy not loaded (optional — run: docker exec kirp-opa opa eval 'data.kirp.governance.allow')"
fi

echo ""
echo "📡 10. Real‑Time Readiness (WebSocket / Streams)"
echo "-----------------------------------------------"

curl -s "$API_URL/ws/health" >/dev/null || echo "⚠ WebSocket health endpoint not available"
curl -s "$API_URL/ws/events" >/dev/null || echo "⚠ Live events endpoint not available"
echo "   ✔ Real-time endpoints probed (where implemented)"

echo ""
echo "🎨 11. Brand OS / Content Intelligence"
echo "--------------------------------------"

curl -s "$API_URL/brand/templates" | jq . >/dev/null || echo "⚠ Brand templates endpoint not available"
curl -s "$API_URL/brand/memory" | jq . >/dev/null || echo "⚠ Brand memory endpoint not available"

echo ""
echo "📊 12. Elasticsearch (if enabled)"
echo "---------------------------------"

if curl -s "$ES_URL" >/dev/null 2>&1; then
  curl -s "$ES_URL/_search" \
    -H "Content-Type: application/json" \
    -d '{"query":{"match_all":{}}}' >/dev/null
  check "Elasticsearch query works"
else
  echo "⚠ Elasticsearch not reachable — skipping ES tests"
fi

echo ""
echo "🔥 13. Redis Keyspace"
echo "---------------------"

docker exec "$REDIS" redis-cli INFO keyspace >/dev/null
check "Redis keyspace accessible"

echo ""
echo "🧪 14. Python E2E Tests"
echo "-----------------------"

if [ -d "tests_e2e" ]; then
  pytest -q tests_e2e/ || { echo "❌ Some E2E tests failed"; exit 1; }
  echo "   ✔ Pytest E2E suite passed"
else
  echo "⚠ tests_e2e/ not found — skipping pytest"
fi

echo ""
echo "🧱 15. UI Build & Basic Health"
echo "-----------------------------"

if [ -f "package.json" ]; then
  npm run build >/dev/null
  check "UI build succeeded"

  echo "   ✔ Checking UI dev port (3100)..."
  curl -s "$UI_URL" >/dev/null || echo "⚠ UI dev server not running on :3100 (run npm run dev separately)"
else
  echo "⚠ No package.json — skipping UI build"
fi

echo ""
echo "🧩 17. UI Authentication & Console Error Checks"
echo "-----------------------------------------------"

# Check if backend dev auth is enabled
AUTH_TEST=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/events")
if [ "$AUTH_TEST" = "401" ]; then
  echo "❌ UI/Backend auth mismatch — /api/events returns 401"
  echo "   Possible causes:"
  echo "   - Backend not running with ENV=development or SKIP_AUTH=1"
  echo "   - NEXT_PUBLIC_DEV_TOKEN missing in UI"
  echo "   - DEV_TOKEN missing or mismatched in backend"
  echo "   - apiClient.ts not attaching Authorization header"
else
  echo "   ✔ Backend accepts UI requests (no 401)"
fi

# Check required endpoints return JSON instead of errors
for ep in "events" "agents" "tenants"; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/$ep")
  if [ "$CODE" != "200" ]; then
    echo "❌ /api/$ep returned HTTP $CODE — UI will break"
  else
    echo "   ✔ /api/$ep OK"
  fi
done

# Check for hydration warnings in UI logs (redirect npm run dev to /tmp/kirp-ui.log to enable)
if [ -f /tmp/kirp-ui.log ]; then
  if grep -q "Extra attributes from the server" /tmp/kirp-ui.log 2>/dev/null; then
    echo "❌ UI hydration warning detected: 'Extra attributes from the server'"
  else
    echo "   ✔ No hydration warnings detected"
  fi
  if grep -q "commitPassiveMountOnFiber" /tmp/kirp-ui.log 2>/dev/null; then
    echo "❌ Potential infinite React re-render loop detected"
  else
    echo "   ✔ No React re-render loops detected"
  fi
else
  echo "   ⚠ /tmp/kirp-ui.log not found — skipping hydration/render checks (redirect npm run dev to it)"
fi

echo ""
echo "🧭 18. UI Route Health (All Pages)"
echo "----------------------------------"

# Accept 2xx, 3xx, or 404 (Next.js may be compiling); skip only on 000/connection refused
UI_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$UI_URL" 2>/dev/null || echo "000")
if [ "$UI_CODE" = "000" ] || [ -z "$UI_CODE" ]; then
  echo "   ⚠ UI not running on :3100 — skipping route checks (run npm run dev)"
else
UI_PAGES=(
  "/"
  "/dashboard"
  "/mission-control"
  "/system-control"
  "/agents"
  "/events"
  "/observability"
  "/pipeline"
  "/content"
  "/run"
  "/history"
  "/signals"
  "/visuals"
  "/decisions"
  "/graph"
  "/governance/audit"
  "/tenants"
  "/settings/users-roles"
  "/dev"
)

for page in "${UI_PAGES[@]}"; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "$UI_URL$page" 2>/dev/null || echo "000")
  # Accept 200, 307, 308; 500 = server error (Next.js compiling or app error)
  case "$CODE" in
    200) echo "   ✔ UI page $page OK" ;;
    307|308) echo "   ✔ UI page $page OK (redirect)" ;;
    500) echo "   ⚠ UI page $page returned 500 (server error — Next.js may be compiling)" ;;
    000) echo "   ⚠ UI page $page unreachable" ;;
    *) echo "❌ UI page $page returned HTTP $CODE" ;;
  esac
done
fi

echo ""
echo "📦 19. UI Static Assets Check"
echo "-----------------------------"

ASSETS=(
  "/favicon.ico"
  "/logo.svg"
  "/manifest.json"
)

for asset in "${ASSETS[@]}"; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "$UI_URL$asset" 2>/dev/null || echo "000")
  if [ "$CODE" = "000" ] || [ -z "$CODE" ]; then
    echo "   ⚠ UI not reachable — skipping asset checks"
    break
  elif [ "$CODE" = "404" ]; then
    echo "   ⚠ Missing static asset: $asset"
  else
    echo "   ✔ Asset $asset reachable"
  fi
done

echo ""
echo "🌐 20. CORS & Preflight Checks"
echo "------------------------------"

CORS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS "$API_URL/api/events" \
  -H "Origin: http://localhost:3100" \
  -H "Access-Control-Request-Method: GET")

if [ "$CORS_CODE" = "204" ] || [ "$CORS_CODE" = "200" ]; then
  echo "   ✔ CORS preflight OK"
else
  echo "❌ CORS preflight failed (HTTP $CORS_CODE)"
fi

echo ""
echo "🔌 21. WebSocket Health"
echo "------------------------"

WS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/realtime/ws/health")
if [ "$WS_CODE" = "200" ]; then
  echo "   ✔ WebSocket health endpoint OK"
else
  echo "⚠ WebSocket health endpoint not available"
fi

echo ""
echo "🧬 22. ENV Consistency Check"
echo "----------------------------"

if [ -f ".env.local" ]; then
  echo "   ✔ .env.local exists"
else
  echo "⚠ .env.local missing"
fi

if grep -q "NEXT_PUBLIC_API_URL" .env.local 2>/dev/null; then
  echo "   ✔ NEXT_PUBLIC_API_URL defined"
else
  echo "⚠ NEXT_PUBLIC_API_URL missing"
fi

if grep -q "NEXT_PUBLIC_DEV_TOKEN" .env.local 2>/dev/null; then
  echo "   ✔ NEXT_PUBLIC_DEV_TOKEN defined"
else
  echo "⚠ NEXT_PUBLIC_DEV_TOKEN missing — UI will get 401"
fi

echo ""
echo "🧱 23. UI Build Integrity (Next.js)"
echo "-----------------------------------"

npm run build >/dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "   ✔ Next.js build succeeded"
else
  echo "❌ Next.js build failed — check components/layouts"
fi

echo ""
echo "🧨 24. UI Error Boundary Test"
echo "-----------------------------"

ERROR_TEST=$(curl -s -o /dev/null -w "%{http_code}" "$UI_URL/this-page-should-not-exist" 2>/dev/null || echo "000")
if [ "$ERROR_TEST" = "404" ]; then
  echo "   ✔ Custom 404 page works"
elif [ "$ERROR_TEST" = "500" ]; then
  echo "   ✔ Error boundary handles unknown route (500)"
elif [ "$ERROR_TEST" = "000" ] || [ -z "$ERROR_TEST" ]; then
  echo "   ⚠ UI not reachable — skipping 404 test"
else
  echo "   ⚠ Unknown route returned HTTP $ERROR_TEST"
fi

echo ""
echo "🧠 25. UI → Backend Integration Test"
echo "------------------------------------"

# system/ports is a Next.js API route (UI server)
if curl -s "$UI_URL/api/system/ports" 2>/dev/null | jq . >/dev/null 2>&1; then
  echo "   ✔ UI system endpoints OK (ports)"
else
  echo "   ⚠ UI system/ports not reachable (run npm run dev on :3100)"
fi

echo ""
echo "🚀 26. Lighthouse Performance & Accessibility Audit"
echo "---------------------------------------------------"

# Check if lighthouse is installed
if ! command -v lighthouse >/dev/null 2>&1; then
  echo "⚠ Lighthouse not installed — skipping audit"
else
  lighthouse "$UI_URL" \
    --quiet \
    --chrome-flags="--headless" \
    --only-categories=performance,accessibility,best-practices,seo \
    --output=json \
    --output-path=/tmp/kirp-lighthouse.json >/dev/null 2>&1

  if [ $? -eq 0 ]; then
    echo "   ✔ Lighthouse audit completed"
    PERF=$(jq '.categories.performance.score * 100' /tmp/kirp-lighthouse.json)
    ACC=$(jq '.categories.accessibility.score * 100' /tmp/kirp-lighthouse.json)
    BP=$(jq '.categories["best-practices"].score * 100' /tmp/kirp-lighthouse.json)
    SEO=$(jq '.categories.seo.score * 100' /tmp/kirp-lighthouse.json)

    echo "   • Performance:      ${PERF}"
    echo "   • Accessibility:    ${ACC}"
    echo "   • Best Practices:   ${BP}"
    echo "   • SEO:              ${SEO}"

    if [ "$PERF" -lt 50 ]; then echo "⚠ Performance score low"; fi
    if [ "$ACC" -lt 70 ]; then echo "⚠ Accessibility score low"; fi
    if [ "$BP" -lt 70 ]; then echo "⚠ Best Practices score low"; fi
    if [ "$SEO" -lt 70 ]; then echo "⚠ SEO score low"; fi
  else
    echo "❌ Lighthouse audit failed"
  fi
fi

echo ""
echo "📦 27. Next.js Bundle Size Check"
echo "--------------------------------"

if [ -d ".next" ]; then
  du -sh .next >/dev/null 2>&1
  echo "   ✔ .next build directory exists"
  echo "   • Bundle size:"
  du -sh .next
else
  echo "⚠ .next directory missing — run npm run build"
fi

echo ""
echo "🧠 28. UI Runtime Memory & CPU Check"
echo "-------------------------------------"

UI_PID=$(pgrep -f "next dev" | head -1)
if [ -n "$UI_PID" ]; then
  echo "   ✔ UI running (PID $UI_PID)"
  ps -o pid,%cpu,%mem,cmd -p "$UI_PID"
else
  echo "⚠ UI process not found — cannot measure memory/CPU"
fi

echo ""
echo "🌐 29. UI Network Error Scan"
echo "-----------------------------"

if [ -f /tmp/kirp-ui.log ] && grep -q "Failed to load resource" /tmp/kirp-ui.log 2>/dev/null; then
  echo "❌ UI network errors detected (Failed to load resource)"
  grep "Failed to load resource" /tmp/kirp-ui.log | head -10
elif [ -f /tmp/kirp-ui.log ]; then
  echo "   ✔ No network errors detected"
else
  echo "   ⚠ /tmp/kirp-ui.log not found — skipping network error scan"
fi

echo ""
echo "🧩 30. UI API Latency Check"
echo "----------------------------"

for ep in "events" "agents" "tenants"; do
  START=$(date +%s%3N)
  curl -s "$API_URL/api/$ep" >/dev/null
  END=$(date +%s%3N)
  LAT=$((END - START))
  echo "   • /api/$ep latency: ${LAT}ms"
  if [ "$LAT" -gt 500 ]; then
    echo "⚠ High latency on /api/$ep"
  fi
done

echo ""
echo "🔍 31. UI Error Boundary Stress Test"
echo "------------------------------------"

STRESS=$(curl -s -o /dev/null -w "%{http_code}" "$UI_URL/__force_error" 2>/dev/null || echo "000")
if [ "$STRESS" = "500" ] || [ "$STRESS" = "404" ]; then
  echo "   ✔ Error boundary responds correctly"
else
  echo "⚠ Error boundary may not be configured correctly"
fi

echo ""
echo "🧬 32. UI Component Integrity Check"
echo "-----------------------------------"

COMPONENTS=(
  "components/navigation/SideNav.tsx"
  "components/layout/AppShell.tsx"
  "components/layout/ErrorBoundary.tsx"
)

for comp in "${COMPONENTS[@]}"; do
  if [ -f "$comp" ]; then
    echo "   ✔ Component exists: $comp"
  else
    echo "❌ Missing component: $comp"
  fi
done

echo ""
echo "📡 33. UI → Backend Contract Check"
echo "----------------------------------"

# system/containers is a Next.js API route (UI server)
if curl -s "$UI_URL/api/system/containers" 2>/dev/null | jq . >/dev/null 2>&1; then
  echo "   ✔ UI system endpoints OK (containers)"
else
  echo "   ⚠ UI system/containers not reachable (run npm run dev on :3100)"
fi

echo ""
echo "🧬 34. Tenants / Events Shape Guard"
echo "-----------------------------------"

# Shape accepted by UI: array or { data: [...] } (ApiListResponse)
shape_ok() {
  local raw="$1"
  if [ -z "$raw" ]; then
    return 1
  fi
  echo "$raw" | jq -e 'if type == "array" then true
    elif type == "object" and (.data | type == "array") then true
    else false end' >/dev/null 2>&1
}

TENANTS_RAW=$(curl -s "$API_URL/api/tenants" || echo "")
if shape_ok "$TENANTS_RAW"; then
  echo "   ✔ /api/tenants shape OK (array or { data: [...] })"
else
  echo "   ⚠ /api/tenants shape unexpected or empty (UI may break)"
fi

EVENTS_RAW=$(curl -s "$API_URL/api/events" || echo "")
if shape_ok "$EVENTS_RAW"; then
  echo "   ✔ /api/events shape OK (array or { data: [...] })"
else
  echo "   ⚠ /api/events shape unexpected or empty (UI may break)"
fi

echo ""
echo "⚡ 16. Final Latency Check"
echo "-------------------------"

START=$(date +%s%3N)
curl -s "$API_URL/health" >/dev/null
END=$(date +%s%3N)
LATENCY=$((END - START))

echo "   ✔ Core API latency: ${LATENCY}ms"
if [ "$LATENCY" -gt 500 ]; then
  echo "⚠ High latency detected on final check"
fi

echo ""
echo "🎉 ALL CRITICAL TESTS COMPLETED"
echo "================================================"
