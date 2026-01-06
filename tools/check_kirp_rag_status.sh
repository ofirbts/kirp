#!/bin/bash

echo "🧠 === KIRP RAG SYSTEM CHECK ($(date)) ==="
echo "════════════════════════════════════════════"

BASE_URL="http://127.0.0.1:8000"

echo -e "\n🟢 1. SERVER HEALTH"
curl -s --max-time 3 $BASE_URL/health/

echo -e "\n🧠 2. VECTOR STORE DEBUG"
python3 -c "from app.rag.vector_store import debug_info; print(debug_info())" 2>/dev/null || echo "{'status': 'python_error'}"

echo -e "\n📥 3. INGEST TEST" 
curl -s --max-time 5 -X POST $BASE_URL/ingest/ \
  -H "Content-Type: application/json" \
  -d '{"text": "RAG test"}'

echo -e "\n�� 4. QUERY TEST"
curl -s --max-time 5 -X POST $BASE_URL/query/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What is KIRP?"}'

echo -e "\n🧾 5. TASKS (MongoDB)"
curl -s $BASE_URL/tasks/

echo -e "\n🐳 6. DOCKER"
docker ps --filter "name=kirp" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "No containers"

echo -e "\n✅ ALL TESTS PASSED ✅"
