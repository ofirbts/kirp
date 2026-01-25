#!/bin/bash
# KIRP Enterprise — Complete System Startup

set -e

echo "🚀 KIRP Enterprise — Starting Complete Production System"
echo "=========================================================="

# 1. Database migration
echo "📊 Running database migrations..."
alembic upgrade head
echo "✅ Migrations complete"

# 2. Start Docker stack
echo "🐳 Starting Docker stack..."
docker compose up -d --build --remove-orphans
echo "✅ Docker stack started"

# 3. Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."

SERVICES=("kirp-postgres" "kirp-redis" "kirp-mongodb" "kirp-kafka" "kirp-zookeeper" "kirp-opa" "kirp-qdrant")

for SERVICE in "${SERVICES[@]}"; do
    echo "🔍 Checking $SERVICE..."
    for i in {1..30}; do
        STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$SERVICE" 2>/dev/null || echo "starting")
        if [[ "$STATUS" == "healthy" ]]; then
            echo "   ✔ $SERVICE is healthy"
            break
        fi
        if [[ "$STATUS" == "unhealthy" ]]; then
            echo "   ❌ $SERVICE is unhealthy — aborting startup"
            exit 1
        fi
        sleep 2
    done
done

echo "✅ All core services are healthy"

# 4. Start Celery workers
echo "👷 Starting Celery workers..."
celery -A src.workers.celery_app worker -l info -c 4 -Q ingest,whatsapp,scheduled &
CELERY_PID=$!

# 5. Start Celery beat
echo "⏰ Starting Celery beat..."
celery -A src.workers.celery_app beat -l info &
BEAT_PID=$!

# 6. Start Kafka processor
echo "🪢 Starting Kafka processor..."
python -m src.workers.kafka_processor &
KAFKA_PID=$!

echo ""
echo "✅ ALL SYSTEMS STARTED"
echo "=========================================================="
echo "📊 API: http://localhost:8000"
echo "📊 Dashboard: http://localhost:8501"
echo "📊 Grafana: http://localhost:3000"
echo "📊 Prometheus: http://localhost:9090"
echo "📊 Mongo Express: http://localhost:8081"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

trap "kill $CELERY_PID $BEAT_PID $KAFKA_PID 2>/dev/null; docker compose down; exit" INT TERM
wait
