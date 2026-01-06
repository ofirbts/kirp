#!/bin/bash
echo "🔍 === KIRP FULL STATUS ($(date)) ==="
echo "═══════════════════════════════════════"

echo "🟢 SERVER STATUS:"
curl -s http://127.0.0.1:8000/health/ || echo "🔴 DOWN"
echo

echo "📋 ENDPOINTS TEST:"
echo "Health: $(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health/) → $(curl -s http://127.0.0.1:8000/health/ | head -c 50)"
echo "Tasks:  $(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/tasks/) → $(curl -s http://127.0.0.1:8000/tasks/ | head -c 50)"
echo "Query:  $(curl -s -X POST -H 'Content-Type: application/json' -d '{"question":"test"}' -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/query/) → $(curl -s -X POST -H 'Content-Type: application/json' -d '{"question":"test"}' http://127.0.0.1:8000/query/ | head -c 50)"
echo "Ingest: $(curl -s -X POST -H 'Content-Type: application/json' -d '{"text":"test"}' -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ingest/) → $(curl -s -X POST -H 'Content-Type: application/json' -d '{"text":"test"}' http://127.0.0.1:8000/ingest/ | head -c 50)"
echo

echo "🐳 DOCKER:"
docker ps --filter "name=kirp" --format "table {{.Names}}\t{{.Status}}"

echo "💾 MONGODB: $(docker ps --filter "name=kirp-mongo" --format "{{.Status}}" || echo "DOWN")"

echo -e "\n✅ SUMMARY: $(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health/ | grep -o '200\|[45]..' || echo '🔴 DOWN') LIVE"
