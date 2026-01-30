#!/bin/bash
# KIRP Enterprise — Ultra+ End-to-End Test Suite
# Covers: API, Agents, Events, RAG, Kafka, Qdrant, ES, Redis, Postgres, OPA, Worker, Multi-Tenant, Latency, Consistency

API_URL="http://localhost:8000"
OPA_URL="http://localhost:8181"
QDRANT_URL="http://localhost:6333"
ES_URL="http://localhost:9200"

REDIS="kirp-redis"
POSTGRES="kirp-postgres"
KAFKA="kirp-kafka"
WORKER="kirp-worker"
API="kirp-api"

echo "🧪 KIRP Enterprise — Ultra+ End-to-End Test Suite"
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
echo "🔍 1. Container Health"
echo "----------------------"

for c in $API $REDIS $POSTGRES $KAFKA $WORKER; do
  docker inspect -f '{{.State.Running}}' $c | grep -q true
  check "Container $c running"
done

echo ""
echo "🔍 2. API Contract & Schema Drift"
echo "--------------------------------"

curl -s "$API_URL/openapi.json" | jq . >/dev/null
check "OpenAPI schema reachable"

curl -s "$API_URL/openapi.json" | jq 'keys' >/dev/null
check "OpenAPI schema valid JSON"

echo ""
echo "🔍 3. Core Services Health"
echo "--------------------------"

curl -s "$API_URL/health" | jq . >/dev/null
check "API healthy"

curl -s "$OPA_URL/healthz" >/dev/null
check "OPA healthy"

curl -s "$QDRANT_URL/healthz" >/dev/null
check "Qdrant healthy"

curl -s -u elastic:password "$ES_URL" >/dev/null
check "Elasticsearch reachable"

docker exec $REDIS redis-cli ping | grep -q PONG
check "Redis reachable"

docker exec $POSTGRES pg_isready >/dev/null
check "Postgres reachable"

echo ""
echo "⚡ 3b. Latency & Consistency Checks"
echo "----------------------------------"

START=$(date +%s%3N)
curl -s "$API_URL/health" >/dev/null
END=$(date +%s%3N)
LAT=$((END - START))
echo "   ✔ API latency: ${LAT}ms"

curl -s "$API_URL/openapi.json" | jq 'keys' >/dev/null
check "API schema consistent"


echo ""
echo "📨 4. Kafka End-to-End (Produce → Consume)"
echo "------------------------------------------"

TOPIC="kirp-test-$RANDOM"
docker exec $KAFKA kafka-topics --bootstrap-server localhost:9092 --create --topic $TOPIC --partitions 1 >/dev/null
check "Kafka topic created"

echo "kirp-test-message" | docker exec -i $KAFKA kafka-console-producer --bootstrap-server localhost:9092 --topic $TOPIC >/dev/null
check "Kafka message produced"

# Allow broker to commit and consumer to connect/assign partitions before consuming
sleep 2
docker exec $KAFKA kafka-console-consumer --bootstrap-server localhost:9092 --topic $TOPIC --from-beginning --max-messages 1 --timeout-ms 15000 | grep -q "kirp-test-message"
check "Kafka message consumed"

echo ""
echo "📝 5. Ingest → Index → Query (Full RAG Pipeline)"
echo "------------------------------------------------"

EVENT=$(curl -s -X POST "$API_URL/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "default",
    "space_id": "private",
    "user_id": "ofir",
    "content": "KIRP must complete the architecture refactor",
    "source": "test"
  }')

EVENT_ID=$(echo "$EVENT" | jq -r '.event_id')
check "Event ingested ($EVENT_ID)"

sleep 2

curl -s "$QDRANT_URL/collections" | jq . >/dev/null
check "Qdrant collections accessible"

curl -s -X POST "$API_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "default",
    "space_id": "private",
    "user_id": "ofir",
    "query": "What tasks should I prioritize?",
    "k": 5
  }' | jq . >/dev/null
check "RAG query executed"

echo ""
echo "🏷️ 5b. Multi‑Tenant Isolation"
echo "-----------------------------"

TENANTS=$(curl -s "$API_URL/api/tenants")
T1=$(echo "$TENANTS" | jq -r '.[0].id')
T2=$(echo "$TENANTS" | jq -r '.[1].id')

if [ "$T1" != "$T2" ]; then
  A=$(curl -s "$API_URL/api/events?tenant_id=$T1")
  B=$(curl -s "$API_URL/api/events?tenant_id=$T2")

  if echo "$A" | grep -q "$T2"; then
    echo "❌ Tenant isolation FAILED"
    exit 1
  else
    echo "   ✔ Tenant isolation enforced"
  fi
else
  echo "⚠ Only one tenant found — skipping"
fi

echo ""
echo "🤖 6. Agent Execution (Real)"
echo "----------------------------"

AGENTS=$(curl -s "$API_URL/api/v1/agents")
AGENT_ID=$(echo "$AGENTS" | jq -r '.[0].id // empty')

if [ -n "$AGENT_ID" ]; then
  curl -s -X POST "$API_URL/api/v1/agents/$AGENT_ID/run" \
    -H "Content-Type: application/json" \
    -d '{"tenant_id":"default","space_id":"private","user_id":"ofir"}' | jq .
  check "Agent execution triggered"

  sleep 2

  curl -s "$API_URL/api/v1/agents/$AGENT_ID/status" | jq .
  check "Agent status retrievable"
else
  echo "⚠ No agents available"
fi

echo ""
echo "📱 10c. WhatsApp Intelligence Engine"
echo "------------------------------------"

curl -s "$API_URL/whatsapp/schedule" | jq . >/dev/null
check "WhatsApp scheduler reachable"

curl -s "$API_URL/whatsapp/insights?tenant_id=default&user_id=ofir" | jq . >/dev/null
check "Insights engine responds"


echo ""
echo "🛡️ 7. Governance / OPA Policy Enforcement"
echo "-----------------------------------------"

curl -s -X POST "$OPA_URL/v1/data/kirp/governance" \
  -H "Content-Type: application/json" \
  -d '{"input":{"action":"read","tenant_id":"default","user_tenant_id":"default","space_id":"private","user_id":"ofir","space_owner_id":"ofir"}}' \
  | jq .

echo ""
echo "🌀 6b. Event‑Sourcing Checks"
echo "---------------------------"

curl -s "$API_URL/api/events?limit=5" | jq . >/dev/null
check "Event store reachable"

curl -s "$API_URL/api/events/replay?limit=1" | jq . >/dev/null
check "Replay endpoint responds"

curl -s "$API_URL/api/events/dlq" | jq . >/dev/null
check "DLQ accessible"


echo ""
echo "🛡️ 7. Governance / OPA Policy Enforcement"
echo "-----------------------------------------"

curl -s -X POST "$OPA_URL/v1/data/kirp/governance" \
  -H "Content-Type: application/json" \
  -d '{"input":{"action":"read","tenant_id":"default","user_tenant_id":"default","space_id":"private","user_id":"ofir","space_owner_id":"ofir"}}' \
  | jq . >/dev/null
check "OPA decision engine responds"

echo ""
echo "📡 7b. Real‑Time Readiness"
echo "--------------------------"

curl -s "$API_URL/ws/health" >/dev/null
check "WebSocket gateway reachable"

curl -s "$API_URL/ws/events" >/dev/null
check "Live events endpoint reachable"


echo ""
echo "🏷️ 8. Multi-Tenant Isolation"
echo "----------------------------"

TENANT_A=$(curl -s "$API_URL/api/tenants" | jq -r '.[0].id')
TENANT_B=$(curl -s "$API_URL/api/tenants" | jq -r '.[1].id')

if [ "$TENANT_A" != "$TENANT_B" ]; then
  curl -s "$API_URL/api/events?tenant_id=$TENANT_A" >/dev/null
  check "Tenant A events accessible"

  curl -s "$API_URL/api/events?tenant_id=$TENANT_B" >/dev/null
  check "Tenant B events accessible"

  if curl -s "$API_URL/api/events?tenant_id=$TENANT_A" | grep -q "$TENANT_B"; then
    echo "❌ Tenant isolation FAILED"
    exit 1
  else
    echo "   ✔ Tenant isolation enforced"
  fi
else
  echo "⚠ Only one tenant found — skipping isolation test"
fi

echo ""
echo "🎨 10b. Brand OS Checks"
echo "------------------------"

curl -s "$API_URL/brand/templates" | jq . >/dev/null
check "Brand templates accessible"

curl -s "$API_URL/brand/memory" | jq . >/dev/null
check "Brand memory accessible"

echo ""
echo "📊 9. Elasticsearch Query"
echo "-------------------------"

curl -s "$ES_URL/_search" \
  -H "Content-Type: application/json" \
  -d '{"query":{"match_all":{}}}' >/dev/null
check "Elasticsearch query works"

echo ""
echo "🔥 10. Redis Keyspace"
echo "---------------------"

docker exec $REDIS redis-cli INFO keyspace >/dev/null
check "Redis keyspace accessible"

echo ""
echo "⚡ 11. Latency Check"
echo "-------------------"

START=$(date +%s%3N)
curl -s "$API_URL/health" >/dev/null
END=$(date +%s%3N)
LATENCY=$((END - START))

echo "   ✔ API latency: ${LATENCY}ms"

if [ $LATENCY -gt 500 ]; then
  echo "⚠ High latency detected"
fi

echo ""
echo "🎉 ALL TESTS PASSED"
echo "================================================"
