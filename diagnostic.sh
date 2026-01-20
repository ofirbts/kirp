#!/bin/bash

API_URL="http://localhost:8000"
DOCKER_API_NAME="kirp-api"

echo "🚀 KIRP OS - ULTIMATE DIAGNOSTIC V5.0"
echo "======================================"

# 1. בדיקת זמינות בסיסית
echo "--- Step 1: Infrastructure & Connectivity ---"
if ! curl -s --head  --request GET "$API_URL/health" | grep "200 OK" > /dev/null; then
    echo "❌ API is DOWN (URL: $API_URL)"
    echo "📜 Last 10 lines of API logs:"
    docker logs $DOCKER_API_NAME --tail 10
    exit 1
fi
echo "✅ API is REACHABLE"

# 2. הרצת בדיקות עומק ספציפיות מ-Tools
echo -e "\n--- Step 2: Core Logic Tests (from /tools) ---"

run_internal_test() {
    local test_name="$1"
    local script_path="$2"
    echo -n "🧪 Testing $test_name... "
    output=$(docker exec $DOCKER_API_NAME python3 "$script_path" 2>&1)
    if [ $? -eq 0 ]; then
        echo "✅ PASSED"
    else
        echo "❌ FAILED"
        echo "--- Error Detail ---"
        echo "$output" | tail -n 5
        echo "--------------------"
    fi
}

run_internal_test "Vector Search & RAG" "tools/check_kirp_rag_status.sh"
run_internal_test "Explainability Integrity" "tools/check_kirp_explainability.py"
run_internal_test "Memory Growth Policy" "tools/check_kirp_memory_growth.py"
run_internal_test "Chaos/Input Resiliency" "tools/check_kirp_chaos.py"

# 3. בדיקת סטטוס מסד נתונים ו-Qdrant
echo -e "\n--- Step 3: Service Health Snapshot ---"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep "kirp"

echo -e "\n✅ Diagnostic Finished."