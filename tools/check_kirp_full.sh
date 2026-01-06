#!/bin/bash
# check_kirp_full.sh - בדיקה מקיפה של KIRP
cd ~/projects/kirp || exit 1

echo "🔍 === KIRP SYSTEM AUDIT ($(date)) ==="
echo "═══════════════════════════════════════════════"

# 0. סטטוס שרת
echo "🟢 SERVER STATUS:"
curl -s -w "Status: % {http_code}\nTime: %{time_total}s\n" -o /dev/null http://127.0.0.1:8000/health/
health=$(curl -s http://127.0.0.1:8000/health/ 2>/dev/null || echo '{"status":"down"}')
echo "$health" | jq . || echo "$health"

echo -e "\n📋 ENDPOINTS TEST:"
declare -A endpoints=(
  ["Health"]="GET /health/"
  ["Tasks"]="GET /tasks/"
  ["Agent"]="POST /agent/"
  ["Weekly"]="POST /intelligence/weekly-summary"
  ["Query"]="POST /query/"
  ["Ingest"]="POST /ingest/"
)

for name in "${!endpoints[@]}"; do
  url="${endpoints[$name]}"
  printf "%-12s: " "$name"
  if [[ $url == POST* ]]; then
    code=$(curl -s -w "%{http_code}" -X POST -H "Content-Type: application/json" \
      -d '{"question":"test"}' "http://127.0.0.1:8000${url#POST }" -o /dev/null 2>/dev/null)
  else
    code=$(curl -s -w "%{http_code}" "http://127.0.0.1:8000${url#* }" -o /dev/null 2>/dev/null)
  fi
  color=$([[ "$code" == "200" ]] && echo "🟢" || echo "🔴")
  echo "$color $code"
done

echo -e "\n📊 DETAILED RESPONSES:"
echo "Tasks sample (first 200 chars):"
curl -s http://127.0.0.1:8000/tasks/ 2>/dev/null | head -c 200 || echo "ERROR"

echo -e "\nAgent test:"
curl -s -X POST http://127.0.0.1:8000/agent/ -H "Content-Type: application/json" \
  -d '{"question":"status"}' 2>/dev/null | head -c 300 || echo "ERROR/404"

echo -e "\n🔍 ROUTERS ANALYSIS:"
echo "Connected routers in main.py:"
grep -n "include_router" app/main.py || echo "No routers found"

echo -e "\n📂 FILE STRUCTURE:"
echo "Key files:"
find app -name "*.py" | grep -E "(router|query|tasks|intelligence)" | head -8

echo -e "\n🐳 DOCKER STATUS:"
docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | grep kirp || echo "No kirp containers"

echo -e "\n💾 DB STATUS:"
if command -v mongosh >/dev/null; then
  echo "MongoDB: OK"
  echo "DB size: $(mongosh --quiet kirp_db --eval 'db.stats().dataSize' 2>/dev/null || echo "N/A")"
else
  echo "MongoDB client: missing (sudo apt install mongodb-mongosh)"
fi

echo -e "\n✅ SUMMARY:"
healthy=$(curl -s -w "%{http_code}" http://127.0.0.1:8000/health/ -o /dev/null)
if [[ "$healthy" == "200" ]]; then
  echo "🟢 Backend: ALIVE"
else
  echo "🔴 Backend: DOWN"
fi

echo "═══════════════════════════════════════════════"
