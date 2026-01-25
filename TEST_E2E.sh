#!/bin/bash
# KIRP Enterprise — Full End-to-End Test Suite

API_URL="http://localhost:8000"
OPA_URL="http://localhost:8181"
QDRANT_URL="http://localhost:6333"
ES_URL="http://localhost:9200"
REDIS_CONTAINER="kirp-redis"
POSTGRES_CONTAINER="kirp-postgres"
KAFKA_CONTAINER="kirp-kafka"
WORKER_CONTAINER="kirp-worker"

echo "🧪 KIRP Enterprise — Full End-to-End Test Suite"
echo "================================================"

check() {
  if [ $? -ne 0 ]; then
    echo "❌ FAILED: $1"
    exit 1
  else
    echo "   ✔ $1"
  fi
}

echo ""
echo "🔍 1. Core Services Health Checks"
echo "--------------------------------"

curl -s "$API_URL/health" | jq . >/dev/null
check "API is healthy"

curl -s "$OPA_URL/healthz" | jq . >/dev/null
check "OPA is healthy"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$QDRANT_URL/healthz")
[ "$STATUS" = "200" ]
check "Qdrant is healthy"

curl -s -u elastic:password "$ES_URL" >/dev/null
check "Elasticsearch reachable"

docker exec $REDIS_CONTAINER redis-cli ping | grep -q PONG
check "Redis reachable"

docker exec $POSTGRES_CONTAINER pg_isready >/dev/null
check "Postgres reachable"

docker inspect -f '{{.State.Running}}' $WORKER_CONTAINER | grep -q true
check "Celery worker is ready"


echo ""
echo "📨 2. Kafka Test"
echo "----------------"

docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server localhost:9092 --list >/dev/null
check "Kafka topics listable"

echo ""
echo "📦 3. OPA Policy Decision Test"
echo "------------------------------"

curl -s -X POST "$OPA_URL/v1/data/kirp/governance" \
  -H "Content-Type: application/json" \
  -d '{"input":{"action":"read","tenant_id":"t1","user_tenant_id":"t1","space_id":"private","user_id":"u1","space_owner_id":"u1"}}' \
  | jq . >/dev/null
check "OPA decision engine responds"

echo ""
echo "📝 4. Ingest Event"
echo "------------------"

EVENT_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "default",
    "space_id": "private",
    "user_id": "ofir",
    "content": "I need to finish the KIRP architecture refactor by Friday",
    "source": "api"
  }')

echo "$EVENT_RESPONSE" | jq .
EVENT_ID=$(echo "$EVENT_RESPONSE" | jq -r '.event_id')
check "Event ingested (ID: $EVENT_ID)"

echo ""
echo "🔍 5. Query (RAG + Agent)"
echo "-------------------------"

curl -s -X POST "$API_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "default",
    "space_id": "private",
    "user_id": "ofir",
    "query": "What are my 3 most critical actions for today?",
    "k": 10
  }' | jq .
check "RAG + Agent query executed"

echo ""
echo "📱 6. WhatsApp Daily Intelligence"
echo "--------------------------------"

curl -s "$API_URL/whatsapp/daily-intelligence?user_id=ofir&tenant_id=default&space_id=private" | jq .
check "WhatsApp intelligence generated"

echo ""
echo "🤖 7. Command Execution"
echo "-----------------------"

curl -s -X POST "$API_URL/command/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "analyze bootcamp progress and suggest 3 actions",
    "tenant_id": "default",
    "space_id": "private",
    "user_id": "ofir"
  }' | jq .
check "Command executed"

echo ""
echo "🛡️ 8. Governance Approvals"
echo "--------------------------"

curl -s "$API_URL/governance/approvals" | jq .
check "Governance approvals endpoint works"

echo ""
echo "🤖 9. Agents List"
echo "-----------------"

curl -s "$API_URL/api/v1/agents" | jq .
check "Agents list retrieved"

echo ""
echo "🎨 10. Brand Content Generation"
echo "------------------------------"

curl -s -X POST "$API_URL/brand/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "idea": "Building an event-sourced agent OS",
    "user_id": "ofir"
  }' | jq .
check "Brand content generated"

echo ""
echo "📊 11. Elasticsearch Index Check"
echo "--------------------------------"

curl -s "$ES_URL/_cat/indices?v" >/dev/null
check "Elasticsearch indices accessible"

echo ""
echo "🧠 12. Qdrant Collections Check"
echo "-------------------------------"

curl -s "$QDRANT_URL/collections" | jq . >/dev/null
check "Qdrant collections accessible"

echo ""
echo "🔥 13. Redis Keyspace Check"
echo "---------------------------"

docker exec $REDIS_CONTAINER redis-cli INFO keyspace >/dev/null
check "Redis keyspace accessible"

echo ""
echo "🎉 ALL TESTS PASSED"
echo "================================================"
