# KIRP End-to-End Verification Checklist

Use this checklist to verify the full stack after deployment.

## 1. AUTHENTICATION & TOKENS

- [ ] **SKIP_AUTH disabled**: `SKIP_AUTH=0` in kirp-api, `NEXT_PUBLIC_SKIP_AUTH=0` in Dashboard build
- [ ] **Login**: POST `/api/v1/auth/login` with `dev@localhost` / `dev` returns 200 + token (after seed)
- [ ] **Signup**: POST `/api/v1/auth/register` creates user and returns token
- [ ] **Me**: GET `/api/v1/auth/me` with `Authorization: Bearer <token>` returns user
- [ ] **Me 401**: GET `/api/v1/auth/me` without token returns 401
- [ ] **tenant_id propagation**: JWT and request.state.user include tenant_id, user_id

## 2. INGEST → EVENTS → PROCESSOR → HISTORY

- [ ] **Dashboard ingest**: Quick-ingest from Dashboard sends content
- [ ] **API receives**: POST `/api/v1/ingest` (with auth) publishes to Kafka
- [ ] **Processor consumes**: kirp-agent-processor logs `[INGEST] event created` and `[INGEST] event processed`
- [ ] **History written**: Processor logs `[INGEST] history entry written`
- [ ] **History API**: GET `/api/v1/history` (with auth) returns entries for authenticated user
- [ ] **Dashboard history**: History page displays entries
- [ ] **Multi-tenant**: tenant_id, space_id, user_id flow unchanged API → Kafka → Processor → History

## 3. KAFKA

- [ ] **Topic**: `kirp-events` exists (auto-created)
- [ ] **Consumer group**: `kirp-processor`
- [ ] **No Prometheus crash**: DISABLE_PROMETHEUS=1 on agent-processor

## 4. WEBSOCKET NOTIFICATIONS

- [ ] **Path**: `ws://<API>/ws/notifications?tenant_id=X&user_id=Y`
- [ ] **Connect**: Dashboard connects with authenticated tenant_id and user_id
- [ ] **Unread count**: On connect, server sends `{ type: "unread_count", unread_count: N }`

## 5. DASHBOARD

- [ ] **API URL**: NEXT_PUBLIC_API_URL baked at build (e.g. http://localhost:8000)
- [ ] **No hardcoded kirp-api:8000**: All use env or BASE
- [ ] **Login flow**: Can login with dev@localhost / dev
- [ ] **Auth guard**: Unauthenticated users redirected to /login
- [ ] **History page**: Loads and displays entries
- [ ] **Insights / Graph / Scenarios**: Work with authenticated context

## 6. DOCKER SERVICES

- [ ] **Start order**: mongodb, postgres, redis, qdrant, kafka, opa → kirp-api → kirp-agent-processor, kirp-dashboard
- [ ] **Healthchecks**: All pass
- [ ] **Env consistency**: MONGO_URI, POSTGRES_URI, KAFKA_BOOTSTRAP_SERVERS match across API and Processor

## Quick Test Commands

```bash
# Auth
curl -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"dev@localhost","password":"dev"}'

# Ingest (replace TOKEN)
curl -X POST http://localhost:8000/api/v1/ingest -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d '{"content":"Test ingest"}'

# History
curl http://localhost:8000/api/v1/history -H "Authorization: Bearer TOKEN"
```
