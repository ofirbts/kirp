#!/bin/bash
# Celery Worker Diagnostic Script for KIRP

set -e

echo "=== KIRP Celery Worker Diagnostic ==="
echo ""

# Check if container is running
if ! docker ps | grep -q kirp-worker; then
    echo "❌ ERROR: kirp-worker container is not running"
    exit 1
fi

echo "✅ Worker container is running"
echo ""

# Check Redis connection
echo "Testing Redis connection..."
REDIS_URL="${REDIS_URL:-redis://redis:6379/0}"
CELERY_BROKER="${CELERY_BROKER_URL:-redis://redis:6379/1}"

if docker exec kirp-worker python -c "
import os
import redis
try:
    broker_url = os.getenv('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'redis://redis:6379/1'))
    r = redis.from_url(broker_url)
    r.ping()
    print('✅ Redis broker connection successful')
except Exception as e:
    print(f'❌ Redis broker connection failed: {e}')
    exit(1)
"; then
    echo "✅ Redis broker accessible"
else
    echo "❌ ERROR: Cannot connect to Redis broker"
    exit 1
fi
echo ""

# Check Kafka connection (if needed)
echo "Testing Kafka connection..."
if docker exec kirp-worker python -c "
import os
from kafka import KafkaProducer
try:
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    producer = KafkaProducer(bootstrap_servers=bootstrap_servers)
    producer.close()
    print('✅ Kafka connection successful')
except Exception as e:
    print(f'⚠️  Kafka connection failed (may not be critical): {e}')
"; then
    echo "✅ Kafka accessible"
else
    echo "⚠️  WARNING: Cannot connect to Kafka (may not be critical for basic worker)"
fi
echo ""

# Check Python imports
echo "Testing Python module imports..."
if docker exec kirp-worker python -c "
import sys
sys.path.insert(0, '/app')
try:
    from src.workers.celery_app import celery_app
    print('✅ celery_app import successful')
    
    from src.workers.tasks import ingest_task, whatsapp_send_task, daily_intelligence_task, self_improvement_task
    print('✅ All task imports successful')
    
    # Check registered tasks
    tasks = list(celery_app.tasks.keys())
    print(f'✅ Found {len(tasks)} registered tasks')
    for task in ['ingest_task', 'whatsapp_send_task', 'daily_intelligence_task', 'self_improvement_task']:
        if task in tasks:
            print(f'   ✅ {task} is registered')
        else:
            print(f'   ❌ {task} is NOT registered')
except Exception as e:
    print(f'❌ Import failed: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"; then
    echo "✅ All imports successful"
else
    echo "❌ ERROR: Import test failed"
    exit 1
fi
echo ""

# Check Celery worker status
echo "Checking Celery worker status..."
if docker exec kirp-worker celery -A src.workers.celery_app inspect active 2>/dev/null | head -20; then
    echo "✅ Celery inspect command works"
else
    echo "⚠️  Celery inspect not available (worker may not be fully started)"
fi
echo ""

# Check environment variables
echo "Environment variables:"
docker exec kirp-worker env | grep -E "(CELERY|REDIS|KAFKA|MONGO|POSTGRES)" | sort
echo ""

echo "=== Diagnostic Complete ==="
echo ""
echo "If all checks passed, the worker should be functioning correctly."
echo "To view worker logs: docker compose logs kirp-worker --tail 50"
