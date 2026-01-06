#!/bin/bash
echo "🔍 === KIRP FULL STATUS ($(date)) ==="
echo "═══════════════════════════════════════"

# SERVER STATUS
echo "🟢 SERVER STATUS:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health/ 2>/dev/null || echo "000")
TIME=$(curl -s -w "Time: %{time_total}s\n" -o /dev/null http://127.0.0.1:8000/health/ 2>/dev/null || echo "Time: N/A")
echo "Status: $HTTP_CODE | $TIME"

echo -e "\n📋 ENDPOINTS TEST:"
declare -A ENDPOINTS=(
    ["Health"]="GET /health/"
    ["Tasks"]="GET /tasks/" 
    ["Query"]="POST /query/"
    ["Ingest"]="POST /ingest/"
    ["Agent"]="POST /agent/"
)

for name in "${!ENDPOINTS[@]}"; do
    url="http://127.0.0.1:8000${ENDPOINTS[$name]}"
    if [[ $name == "Query" || $name == "Ingest" || $name == "Agent" ]]; then
        code=$(curl -s -w "%{http_code}" -X POST "$url" \
            -H "Content-Type: application/json" \
            -d '{"text":"test"}' -o /dev/null 2>/dev/null || echo "000")
    else
        code=$(curl -s -w "%{http_code}" "$url" -o /dev/null 2>/dev/null || echo "000")
    fi
    
    if [[ $code == "200" ]]; then
        echo "$name : 🟢 $code"
    else
        echo "$name : 🔴 $code" 
    fi
done

# DOCKER STATUS
echo -e "\n🐳 DOCKER:"
docker ps --filter "name=kirp" --format "table {{.Names}}\t{{.Status}}" || echo "No containers"

# MONGODB
echo -e "\n💾 MONGODB: $(docker ps --filter "name=kirp-mongo" --format "{{.Status}}" || echo "DOWN")"

echo -e "\n✅ SUMMARY: $([[ $HTTP_CODE == "200" ]] && echo "🟢 LIVE" || echo "🔴 DOWN")"
