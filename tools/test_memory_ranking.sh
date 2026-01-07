#!/bin/bash
echo "🧠 === MEMORY RANKING TEST ==="

echo "1. Ingest fresh memory..."
curl -s -X POST "http://127.0.0.1:8000/ingest/" \
  -H "Content-Type: application/json" \
  -d '{"text":"Buy milk tomorrow 8AM","metadata":{"INGESTED_AT":"'$(date -Iseconds -u)'","source":"api"}}' \
  | jq '.status'

sleep 1

echo -e "\n2. Ingest old memory..."
curl -s -X POST "http://127.0.0.1:8000/ingest/" \
  -H "Content-Type: application/json" \
  -d '{"text":"Bought milk last week","metadata":{"INGESTED_AT":"2025-12-28T10:00:00","source":"api"}}' \
  | jq '.status'

echo -e "\n3. Query 'milk' - expect FRESH first:"
curl -s -X POST "http://127.0.0.1:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"question":"milk"}' | head -30
