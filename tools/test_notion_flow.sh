#!/bin/bash
echo "🤖 === KIRP + NOTION FULL FLOW ==="

echo "1. Agent analysis..."
RESPONSE=$(curl -s -X POST "http://127.0.0.1:8000/agent/" \
  -H "Content-Type: application/json" \
  -d '{"question":"My milk tasks?"}')

TRACE_ID=$(echo "$RESPONSE" | grep -o '"trace_id":"[^"]*' | cut -d'"' -f4)
echo "📋 Trace ID: $TRACE_ID"

echo -e "\n2. Execute Notion tasks..."
curl -s -X POST "http://127.0.0.1:8000/agent/confirm" \
  -H "Content-Type: application/json" \
  -d "{\"trace_id\":\"$TRACE_ID\",\"confirm\":true}" | jq .
