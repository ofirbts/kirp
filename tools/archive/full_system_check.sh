#!/bin/bash
set -e

echo "🧠 === KIRP FULL SYSTEM CHECK ==="

echo "🟢 Health"
curl -s http://127.0.0.1:8000/health | jq .

echo "📥 Ingest"
curl -s -X POST http://127.0.0.1:8000/ingest/ \
  -H "Content-Type: application/json" \
  -d '{"text":"Buy milk tomorrow","metadata":{"source":"test"}}' | jq .

echo "🔍 Query"
curl -s -X POST http://127.0.0.1:8000/query/ \
  -H "Content-Type: application/json" \
  -d '{"question":"What should I do tomorrow?"}' | jq .

echo "🤖 Agent"
curl -s -X POST http://127.0.0.1:8000/agent/ \
  -H "Content-Type: application/json" \
  -d '{"question":"I need to buy milk tomorrow"}' | jq .

echo "✅ SYSTEM OK"
