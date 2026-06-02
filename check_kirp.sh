#!/bin/bash

echo "======================================"
echo "   KIRP Enterprise — Full Diagnostics"
echo "======================================"

check_port() {
  local name=$1
  local port=$2
  echo -n "Checking $name on port $port ... "
  if nc -z localhost $port 2>/dev/null; then
    echo "OK"
  else
    echo "FAILED"
  fi
}

check_container() {
  local name=$1
  echo -n "Checking container $name ... "
  if docker ps --format '{{.Names}}' | grep -q "^$name$"; then
    echo "RUNNING"
  else
    echo "NOT RUNNING"
  fi
}

check_health() {
  local name=$1
  echo -n "Health status for $name ... "
  docker inspect --format='{{.State.Health.Status}}' $name 2>/dev/null || echo "NO HEALTHCHECK"
}

echo ""
echo "=== Containers ==="
check_container kirp-api
check_container kirp-dashboard
check_container kirp-worker
check_container kirp-agent-processor
check_container kirp-kafka
check_container kirp-zookeeper
check_container kirp-redis
check_container kirp-mongodb
check_container kirp-postgres
check_container kirp-qdrant
check_container kirp-elasticsearch
check_container kirp-prometheus
check_container kirp-grafana

echo ""
echo "=== Healthchecks ==="
check_health kirp-api
check_health kirp-dashboard
check_health kirp-worker
check_health kirp-agent-processor
check_health kirp-kafka
check_health kirp-zookeeper
check_health kirp-redis
check_health kirp-mongodb
check_health kirp-postgres
check_health kirp-qdrant
check_health kirp-elasticsearch

echo ""
echo "=== Ports ==="
check_port "API" 8000
check_port "Dashboard" 8501
check_port "Grafana" 3000
check_port "Prometheus" 9090
check_port "Elasticsearch" 9200
check_port "Qdrant" 6333
check_port "Kafka" 9092
check_port "Redis" 6379
check_port "Mongo Express" 8081
check_port "OPA" 8181
check_port "Postgres" 5432
check_port "Cassandra" 9042

echo ""
echo "=== API Health Endpoint ==="
curl -s http://localhost:8000/health || echo "API not responding"

echo ""
echo "=== Qdrant Collections ==="
curl -s http://localhost:6333/collections || echo "Qdrant not responding"

echo ""
echo "=== Kafka Broker Check ==="
docker exec kirp-kafka kafka-broker-api-versions --bootstrap-server localhost:9092 2>/dev/null || echo "Kafka not responding"

echo ""
echo "=== Postgres Check ==="
docker exec kirp-postgres psql -U kirp_user -d kirp -c "SELECT COUNT(*) FROM events;" 2>/dev/null || echo "Postgres query failed"

echo ""
echo "=== Mongo Check ==="
docker exec kirp-mongodb mongosh --eval "db.adminCommand('ping')" 2>/dev/null || echo "Mongo not responding"

echo ""
echo "=== Redis Check ==="
docker exec kirp-redis redis-cli ping 2>/dev/null || echo "Redis not responding"

echo ""
echo "=== DONE ==="
