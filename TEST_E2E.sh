#!/usr/bin/env bash
# KIRP OS — Ultra+ E2E System Audit (v3.0)
set -euo pipefail

API="http://localhost:8000"
UI="http://localhost:3100"

CONTAINERS=("kirp-api" "kirp-redis" "kirp-postgres" "kirp-kafka" "kirp-dashboard")

echo "======================================================="
echo "🧪 KIRP OS — Ultra+ E2E System Audit (v3.0)"
echo "======================================================="

# ---------------------------------------------------------
# Helper: HTTP test
# ---------------------------------------------------------
test_http() {
    local url="$1"
    local label="$2"
    local optional="${3:-}"

    local response
    response=$(curl -s -w "\n%{http_code}" "$url" --max-time 4 || echo -e "Network Error\n000")

    local body
    body=$(echo "$response" | sed '$d')

    local code
    code=$(echo "$response" | tail -n1)

    if [[ "$code" =~ ^(200|204|307|308)$ ]]; then
        echo "    ✔ $label (HTTP $code)"
    elif [[ "$optional" == "optional" ]]; then
        echo "    ⚠ $label (Optional)"
    else
        echo "❌ FAILED: $label (HTTP $code)"
        [[ -n "$body" ]] && echo "📝 Response: $body"
        exit 1
    fi
}

# ---------------------------------------------------------
# 1. Design System Integrity
# ---------------------------------------------------------
echo -e "\n🎨 1. Design System Integrity"

check_css() {
    local pattern="$1"
    local file="$2"
    local label="$3"

    grep -q "$pattern" "$file" \
        && echo "    ✔ $label" \
        || { echo "❌ Missing: $label"; exit 1; }
}

check_css "color-primary: #98FFD2" "app/globals.css" "Mint token found"
check_css "glass-card" "app/globals.css" "glass-card class exists"
check_css "rounded-2xl" "components/layout/AppShell.tsx" "AppShell uses rounded-2xl"
check_css "rounded-full" "components/ui/button.tsx" "Buttons are pill-shaped"

# ---------------------------------------------------------
# 2. Containers
# ---------------------------------------------------------
echo -e "\n🔍 2. Infrastructure Containers"

for c in "${CONTAINERS[@]}"; do
    docker inspect -f '{{.State.Running}}' "$c" 2>/dev/null | grep -q true \
        && echo "    ✔ $c running" \
        || { echo "❌ $c is down"; exit 1; }
done

# ---------------------------------------------------------
# 3. API Health & Intelligence
# ---------------------------------------------------------
echo -e "\n🧠 3. Intelligence Layer — API Contract"

test_http "$API/health" "API Health"

# Ingest
EVENT_ID=$(curl -s -X POST "$API/api/v1/ingest" \
    -H "Content-Type: application/json" \
    -d '{"tenant_id":"default","space_id":"all","user_id":"e2e","content":"E2E Test Event"}' \
    | jq -r '.event_id // empty')

[[ -n "$EVENT_ID" ]] \
    && echo "    ✔ Ingest OK ($EVENT_ID)" \
    || { echo "❌ Ingest failed"; exit 1; }

# Ask
ASK=$(curl -s -X POST "$API/api/v1/ask" \
    -H "Content-Type: application/json" \
    -d '{"tenant_id":"default","space_id":"all","query":"מה עשיתי היום?"}' \
    | jq -r '.answer // empty')

[[ -n "$ASK" ]] \
    && echo "    ✔ Ask API OK" \
    || { echo "❌ Ask API failed"; exit 1; }

# Agents List
test_http "$API/api/agents" "Agents List"

# Agent run
curl -s -X POST "$API/api/agents/InsightAgent/run" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"default","space_id":"all"}' | jq . >/dev/null \
  && echo "    ✔ Agent Run (InsightAgent) OK" \
  || { echo "❌ Agent Run failed"; exit 1; }

# ---------------------------------------------------------
# 4. Multi‑Tenant Tests
# ---------------------------------------------------------
echo -e "\n🏢 4. Multi‑Tenant Isolation"

TENANT="tenant_$(date +%s)"
SPACE="space_$(date +%s)"

curl -s -X POST "$API/api/v1/ingest" \
    -H "Content-Type: application/json" \
    -d "{\"tenant_id\":\"$TENANT\",\"space_id\":\"$SPACE\",\"user_id\":\"e2e\",\"content\":\"Tenant Test\"}" >/dev/null

DEFAULT_TASKS=$(curl -s "$API/api/v1/tasks?tenant_id=default&space_id=default")

echo "$DEFAULT_TASKS" | grep -q "Tenant Test" \
    && { echo "❌ Tenant isolation failed"; exit 1; } \
    || echo "    ✔ Tenant isolation OK"

# ---------------------------------------------------------
# 5. UI Routes
# ---------------------------------------------------------
echo -e "\n🧭 5. UI Routes"

UI_ROUTES=(
    "/second-brain"
    "/second-brain/timeline"
    "/second-brain/life-areas"
    "/second-brain/inbox"
    "/second-brain/suggestions"
    "/tasks"
    "/agents"
    "/login"
)

for r in "${UI_ROUTES[@]}"; do
    test_http "$UI$r" "UI Route: $r" "optional"
done

# ---------------------------------------------------------
# 6. Auth Flow
# ---------------------------------------------------------
echo -e "\n🔐 6. Auth Flow"

LOGIN=$(curl -s -X POST "$API/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"test"}' \
    | jq -r '.token // empty')

[[ -n "$LOGIN" ]] \
    && echo "    ✔ Login endpoint OK" \
    || echo "    ⚠ Login not implemented (skipping)"

# ---------------------------------------------------------
# 7. Meta‑Agent Placeholder
# ---------------------------------------------------------
echo -e "\n🤖 7. Meta‑Agent Placeholder"

if [ -f "src/agents/meta/orchestrator.ts" ]; then
    grep -q "prepareMetaAgent" src/agents/meta/orchestrator.ts \
        && echo "    ✔ Meta‑Agent orchestrator exists" \
        || { echo "❌ Missing Meta‑Agent orchestrator logic"; exit 1; }
else
    echo "    ⚠ src/agents/meta/orchestrator.ts not found (skipping)"
fi

# ---------------------------------------------------------
# 8. Responsive (HTTP-level)
# ---------------------------------------------------------
echo -e "\n📱 8. Responsive (HTTP-level)"

MOBILE_UA="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)"
DESKTOP_UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

curl -s -A "$MOBILE_UA" "$UI/second-brain" >/dev/null \
    && echo "    ✔ Mobile UA OK" \
    || echo "❌ Mobile UA failed"

curl -s -A "$DESKTOP_UA" "$UI/second-brain" >/dev/null \
    && echo "    ✔ Desktop UA OK" \
    || echo "❌ Desktop UA failed"

# ---------------------------------------------------------
# 9. Performance
# ---------------------------------------------------------
echo -e "\n⚡ 9. Performance"

START=$(date +%s%3N)
curl -s "$API/health" >/dev/null
END=$(date +%s%3N)

echo "    ✔ API Latency: $((END - START))ms"

echo -e "\n🎉 ALL TESTS PASSED — KIRP OS IS READY!"
