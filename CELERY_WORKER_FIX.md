# Celery Worker Fix — Complete Solution

**Date:** 2026-01-26  
**Issue:** `ModuleNotFoundError: No module named 'src.workers.celery_tasks'`  
**Status:** ✅ **FIXED**

---

## ROOT CAUSE

The `celery_app.py` configuration was referencing a non-existent module:
- ❌ **Included:** `"src.workers.celery_tasks"` (doesn't exist)
- ❌ **Task routes:** Referenced `src.workers.celery_tasks.daily_intelligence_task` and `src.workers.celery_tasks.self_improvement_task`

**Reality:**
- ✅ All tasks are actually in `src/workers/tasks.py`
- ✅ Tasks defined: `ingest_task`, `whatsapp_send_task`, `daily_intelligence_task`, `self_improvement_task`

---

## FIXES APPLIED

### 1. Fixed `src/workers/celery_app.py`

**Before:**
```python
include=["src.workers.tasks", "src.workers.celery_tasks"],
task_routes={
    "src.workers.celery_tasks.daily_intelligence_task": {"queue": "scheduled"},
    "src.workers.celery_tasks.self_improvement_task": {"queue": "scheduled"},
}
```

**After:**
```python
include=["src.workers.tasks"],
task_routes={
    "src.workers.tasks.daily_intelligence_task": {"queue": "scheduled"},
    "src.workers.tasks.self_improvement_task": {"queue": "scheduled"},
}
```

### 2. Added Startup Diagnostics

Added logging to verify:
- Broker/backend URLs are correct
- All tasks are imported successfully
- Import errors are caught and logged

### 3. Enhanced `src/workers/__init__.py`

Ensures tasks module is properly imported when package loads.

### 4. Created Diagnostic Script

`deploy/worker-diagnostic.sh` — Comprehensive worker health check:
- Container status
- Redis broker connection
- Kafka connection (optional)
- Python module imports
- Celery task registration
- Environment variables

---

## VERIFICATION

### Step 1: Check Worker Logs
```bash
docker compose logs kirp-worker --tail 50
```

**Expected output:**
```
[INFO] Celery broker: redis://redis:6379/1
[INFO] Celery backend: redis://redis:6379/1
[INFO] All Celery tasks loaded successfully
[INFO] celery@<hostname> ready.
```

### Step 2: Run Diagnostic Script
```bash
./deploy/worker-diagnostic.sh
```

**Expected:**
- ✅ Worker container is running
- ✅ Redis broker connection successful
- ✅ All task imports successful
- ✅ All tasks registered

### Step 3: Test Task Execution
```bash
# Check registered tasks
docker exec kirp-worker celery -A src.workers.celery_app inspect registered

# Test a simple task (if API is running)
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"content": "test", "tenant_id": "default", "space_id": "private", "user_id": "test"}'
```

### Step 4: Verify Redis Connection
```bash
docker exec kirp-worker python -c "
import redis
r = redis.from_url('redis://redis:6379/1')
print('Redis ping:', r.ping())
"
```

### Step 5: Verify Kafka Connection (if needed)
```bash
docker exec kirp-worker python -c "
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers='kafka:9092')
producer.close()
print('Kafka connection successful')
"
```

---

## TASK REGISTRATION

All tasks should be registered with these names:
- `ingest_task` — Queue: `ingest`
- `whatsapp_send_task` — Queue: `whatsapp`
- `daily_intelligence_task` — Queue: `scheduled` (runs at 08:00)
- `self_improvement_task` — Queue: `scheduled` (runs at 02:00)

---

## SCHEDULED TASKS (Celery Beat)

**Note:** Celery Beat is NOT running by default. To enable scheduled tasks:

1. **Option 1:** Add a separate beat service to `docker-compose.yml`:
```yaml
kirp-beat:
  build:
    context: .
    dockerfile: Dockerfile.worker
  container_name: kirp-beat
  restart: unless-stopped
  env_file: .env
  environment:
    CELERY_BROKER_URL: redis://redis:6379/1
    CELERY_RESULT_BACKEND: redis://redis:6379/1
  command: celery -A src.workers.celery_app beat -l info
  depends_on:
    redis: { condition: service_healthy }
  networks:
    - kirp-net
```

2. **Option 2:** Run beat in the same worker (not recommended for production):
```yaml
command: celery -A src.workers.celery_app worker --beat -l info -c 4
```

---

## TROUBLESHOOTING

### Issue: Worker still can't find tasks

**Check imports:**
```bash
docker exec kirp-worker python -c "
import sys
sys.path.insert(0, '/app')
from src.workers.tasks import ingest_task
print('✅ Import successful')
"
```

### Issue: Redis connection fails

**Verify Redis is running:**
```bash
docker compose ps redis
docker compose logs redis --tail 20
```

**Test connection:**
```bash
docker exec kirp-redis redis-cli ping
```

**Check environment:**
```bash
docker exec kirp-worker env | grep -E "(CELERY|REDIS)"
```

### Issue: Tasks not executing

**Check worker is consuming:**
```bash
docker exec kirp-worker celery -A src.workers.celery_app inspect active
```

**Check queues:**
```bash
docker exec kirp-worker celery -A src.workers.celery_app inspect reserved
```

**Check Redis queues:**
```bash
docker exec kirp-redis redis-cli
> KEYS celery*
> LLEN celery
```

---

## FILES MODIFIED

1. **src/workers/celery_app.py**
   - Removed non-existent `src.workers.celery_tasks` from include
   - Fixed task routes to use `src.workers.tasks`
   - Added startup diagnostics and error handling

2. **src/workers/__init__.py**
   - Enhanced to ensure tasks are imported

3. **deploy/worker-diagnostic.sh** (NEW)
   - Comprehensive diagnostic tool

4. **CELERY_WORKER_FIX.md** (NEW)
   - This documentation

---

## EXPECTED BEHAVIOR

After fixes:
- ✅ Worker starts without import errors
- ✅ All 4 tasks are registered
- ✅ Redis broker connection works
- ✅ Tasks can be executed
- ✅ Scheduled tasks are configured (beat needed for execution)

---

## NEXT STEPS

1. **Restart worker:**
   ```bash
   docker compose restart kirp-worker
   ```

2. **Verify:**
   ```bash
   ./deploy/worker-diagnostic.sh
   ```

3. **Test task execution** (via API or direct call)

4. **Optional:** Add Celery Beat service for scheduled tasks

---

**Status:** ✅ **WORKER FIXED | READY FOR TESTING**
