#!/bin/bash
echo "🚀 Starting KIRP full stack..."

# 1. Docker (כבר רץ)
docker compose up -d kirp-api kirp-agent-processor
sleep 5

# 2. נטען .env בלי הערות
if [ -f .env.development ]; then
    echo "Loading clean .env.development..."
    # רק שורות ללא # וריקות
    export $(grep -v '^#' .env.development | grep -v '^$' | xargs)
fi

# 3. ודא venv פעיל
source .venv/bin/activate  # אתה משתמש ב-.venv, לא venv

# 4. Celery worker
nohup celery -A src.workers.celery_app.celery_app worker -l info -D > celery_worker.log 2>&1 &
echo $! > celery_worker.pid
echo "Worker PID: $!"

# 5. Celery beat  
nohup celery -A src.workers.celery_app.celery_app beat -l info -D > celery_beat.log 2>&1 &
echo $! > celery_beat.pid
echo "Beat PID: $!"

echo "✅ All services running!"
echo "Logs: tail -f celery_*.log"
echo "Check Celery: ps aux | grep celery"
echo "Stop: pkill -F celery_*.pid"
