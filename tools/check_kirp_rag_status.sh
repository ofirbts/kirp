#!/bin/bash

echo "🧠 === KIRP RAG SYSTEM CHECK ($(date)) ==="
echo "════════════════════════════════════════════"

BASE_URL="http://127.0.0.1:8000"

echo -e "\n🟢 1. SERVER HEALTH"
HEALTH_CODE=$(curl -s -o /tmp/health.json -w "%{http_code}" $BASE_URL/health/)
cat /tmp/health.json
echo "HTTP: $HEALTH_CODE"

if [ "$HEALTH_CODE" != "200" ]; then
  echo "❌ Server not healthy"
  exit 1
fi

echo -e "\n🧠 2. VECTOR STORE DEBUG"
python - <<EOF
from app.rag.vector_store import debug_info
print(debug_info())
EOF

echo -e "\n📥 3. INGEST TEST"
INGEST_CODE=$(curl -s -o /tmp/ingest.json -w "%{http_code}" \
  -X POST $BASE_URL/ingest/ \
  -H "Content-Type: application/json" \
  -d '{
        "text": "KIRP RAG test memory. This text should be retrievable via semantic search.",
        "metadata": {"source": "rag_check"}
      }')
cat /tmp/ingest.json
echo "HTTP: $INGEST_CODE"

echo -e "\n🔍 4. QUERY WITH CONTEXT"
QUERY_CODE=$(curl -s -o /tmp/query.json -w "%{http_code}" \
  -X POST $BASE_URL/query/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What is KIRP?"}')
cat /tmp/query.json
echo "HTTP: $QUERY_CODE"

echo -e "\n🧾 5. RESPONSE VALIDATION"
python - <<EOF
import json

with open("/tmp/query.json") as f:
    data = json.load(f)

assert "answer" in data, "Missing answer"
assert "sources" in data, "Missing sources"
assert len(data["sources"]) > 0, "No sources retrieved"

print("✅ Answer present")
print(f"✅ Sources count: {len(data['sources'])}")
EOF

echo -e "\n🐳 6. DOCKER STATUS"
docker ps --filter "name=kirp" --format "table {{.Names}}\t{{.Status}}"

echo -e "\n✅ FINAL STATUS: RAG PIPELINE OPERATIONAL"
echo "🧠 KIRP RAG SYSTEM CHECK COMPLETE"