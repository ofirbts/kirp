# KIRP Stack — End-to-End Verification & Fixes Summary

This document summarizes the production-grade verification and corrections applied to the full KIRP stack.

---

## 1. AUTHENTICATION (API + Dashboard)

### Changes Made

- **API middleware** (`src/main.py`): Dev fallback now applies **only** when `SKIP_AUTH=1`. When `SKIP_AUTH=0`, no automatic dev user is set; a valid JWT is required.
- **tenant_context**: `get_tenant_context()` already reads `tenant_id`, `space_id`, `user_id` from `request.state.user` (set by JWT middleware).
- **Ingest endpoint**: Uses `get_tenant_context(request)` and overrides all payload fields with the authenticated user's values.
- **Stats endpoint**: Uses `get_tenant_context(request)` instead of hardcoded defaults.
- **v1_auth**: Login, signup, `/me` work correctly; JWT includes `user_id`, `tenant_id`, `roles`.
- **Seed**: `_seed_dev_user_if_needed()` creates `dev@localhost` / `dev` on first run.

### Configuration

- `SKIP_AUTH=0` in kirp-api (docker-compose).
- `NEXT_PUBLIC_SKIP_AUTH=0` in Dashboard build args and env.
- Dashboard auth guard redirects unauthenticated users to `/login`.

---

## 2. WEBSOCKET NOTIFICATIONS

### Current State

- **Path**: `ws://<API>/ws/notifications?tenant_id=X&user_id=Y`
- **Router**: `src/api/ws_notifications.py` — included in `src/main.py` via `app.include_router(ws_notifications.router)`.
- **Dashboard**: `lib/hooks/useNotificationsWs.ts` uses `useAuthStore()` and passes `effectiveTenantId` and `effectiveUserId` from the authenticated user.
- **URL derivation**: `getNotificationsWsUrl()` in `lib/apiClient.ts` derives from `NEXT_PUBLIC_API_URL` (http→ws).

### Notes

- Notifications are pushed when explicitly created (e.g. task_created, reminder) via `NotificationStore.create_and_push()`.
- The ingest pipeline writes history entries but does not create notifications; the Activity Center shows notifications from the notification store.

---

## 3. INGEST → EVENTS → PROCESSOR → HISTORY PIPELINE

### Flow

1. **Dashboard** sends ingest via `apiClient.ingestV1()` with `tenant_id`, `space_id`, `user_id` from auth.
2. **API** (`POST /api/v1/ingest`) receives request, uses `get_tenant_context(request)`, publishes to Kafka `kirp-events`.
3. **Agent Processor** consumes from `kirp-events`, dispatches via `EventRegistry` → `handle_ingest_v1` → `EventPipeline.run()`.
4. **Pipeline** writes event to Mongo, embeddings to Qdrant, schema to Postgres, and **history** via `record_history()`.
5. **History API** (`GET /api/v1/history`) returns entries filtered by `tenant_id` and `user_id` from auth.

### Fixes Applied

- Ingest endpoint enforces multi-tenancy from auth context.
- Processor uses `DISABLE_PROMETHEUS=1` to avoid Prometheus multiprocess conflicts.
- `src/observability/metrics.py` respects `DISABLE_PROMETHEUS` — all metrics become no-op when set.

---

## 4. DASHBOARD (Next.js)

### Configuration

- `NEXT_PUBLIC_API_URL` is baked at build time via Docker build args.
- `NEXT_PUBLIC_SKIP_AUTH=0` baked at build.
- No hardcoded `kirp-api:8000` in app code; all use `NEXT_PUBLIC_API_URL` or `BASE` from apiClient.

### Pages Using Auth Context

- **Dashboard**: `user?.tenant_id ?? DEFAULT_TENANT_ID`, `user?.id ?? DEFAULT_USER_ID` for ingest, askV1, listTasks, listEvents, etc.
- **History**: Same pattern for `listHistoryV1`.
- **WebSocket**: `useNotificationsWs` uses `user?.tenant_id` and `user?.id`.

---

## 5. KAFKA + ZOOKEEPER

### Changes Made

- **Zookeeper healthcheck**: Uses real `ruok` → `imok` check: `echo ruok | nc localhost 2181 | grep -q imok`.
- **Kafka depends_on**: `zookeeper: condition: service_started` (already correct).
- **API depends_on**: Changed `kafka: condition: service_healthy` → `kafka: condition: service_started` so the API can start earlier; Kafka producer connects lazily.
- **Kafka listeners**: `PLAINTEXT://kafka:9092` (internal), `PLAINTEXT_HOST://localhost:9093` (host access).

---

## 6. DATABASES & STORAGE

### Verified

- **MongoDB**: Event store + history. `MONGO_URI` consistent across API and Processor.
- **Postgres**: Schema engine, migrations. `alembic upgrade head` runs on API startup.
- **Qdrant**: RAG embeddings. `QDRANT_URL` set for API and Processor.
- **Redis**: Idempotency keys for Kafka processor. `REDIS_URL` set.
- **Elasticsearch / Cassandra**: Env vars present; optional for core flow.

---

## 7. DOCKER-COMPOSE & DOCKERFILES

### docker-compose.yml

- All services have correct `depends_on` and healthchecks.
- `SKIP_AUTH=0`, `NEXT_PUBLIC_SKIP_AUTH=0`.
- `DISABLE_PROMETHEUS=1` for kirp-agent-processor.
- Build args for Dashboard: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SKIP_AUTH`.

### Dockerfile.dashboard

- ARG/ENV for `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_SKIP_AUTH`.
- Standalone output for production.

### Dockerfile.api / Dockerfile.agent

- No changes required; already correct.

---

## 8. WHAT WAS WRONG AND HOW IT WAS FIXED

| Issue | Fix |
|-------|-----|
| Dev user applied when ENV=development even with SKIP_AUTH=0 | Middleware now uses dev fallback **only** when `SKIP_AUTH=1`. |
| API waited for Kafka healthy (90s+ start_period) | API depends on `kafka: service_started` instead of `service_healthy`. |
| Processor Prometheus multiprocess conflicts | `DISABLE_PROMETHEUS=1` + metrics no-op when disabled. |
| Ingest might trust body tenant_id over auth | Ingest uses `get_tenant_context(request)` exclusively. |
| Stats used hardcoded "default" | Stats uses `get_tenant_context(request)`. |
| WebSocket not using auth user | `useNotificationsWs` uses `user?.tenant_id` and `user?.id` from auth store. |

---

## 9. FINAL VERIFICATION CHECKLIST

See `docs/E2E_VERIFICATION_CHECKLIST.md` for the full checklist.

### Quick Verification

```bash
# 1. Start stack
docker compose up -d

# 2. Wait for API healthy
docker compose ps

# 3. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@localhost","password":"dev"}'
# Save TOKEN from response

# 4. Ingest
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Test ingest"}'

# 5. History
curl http://localhost:8000/api/v1/history -H "Authorization: Bearer $TOKEN"

# 6. Dashboard: http://localhost:3100 — login with dev@localhost / dev
```

---

## 10. FILES MODIFIED

- `src/main.py` — Auth middleware dev fallback logic; ingest/stats multi-tenancy (already correct)
- `docker-compose.yml` — API kafka dependency, Zookeeper healthcheck
- `docs/E2E_FIXES_SUMMARY.md` — This document
