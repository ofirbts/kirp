#!/bin/bash
echo "🚀=== KIRP PRODUCTION AGENT DEMO ===🚀"

echo "📥 1. Ingest..."
curl -s -X POST "http://127.0.0.1:8000/ingest/" \
  -H "Content-Type: application/json" \
  -d '{"text":"Gym 8AM tomorrow"}'

echo -e "\n🤖 2. Agent finds tasks..."
RESPONSE=$(curl -s -X POST "http://127.0.0.1:8000/agent/" \
  -H "Content-Type: application/json" \
  -d '{"question":"My schedule?"}')
echo "$RESPONSE"

TRACE_ID=$(echo "$RESPONSE" | grep -o '"trace_id":"[^"]*' | cut -d'"' -f4)
echo -e "\n✅ 3. EXECUTING: $TRACE_ID"

curl -s -X POST "http://127.0.0.1:8000/agent/confirm" \
  -H "Content-Type: application/json" \
  -d "{\"trace_id\":\"$TRACE_ID\",\"confirm\":true}"

echo -e "\n📊 4. RAG confidence:"
curl -s -X POST "http://127.0.0.1:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"question":"gym"}'

echo "🎉 KIRP Full Agent Cycle COMPLETE!"
