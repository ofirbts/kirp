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
- [ ] **tenantContextStore sync**: AppShell syncs tenantId/userId from auth on load
- [ ] **History page**: Loads and displays entries
- [ ] **Open Tasks**: Dashboard and Tasks page show tasks for authenticated tenant
- [ ] **Today's Insights**: askV1 returns focus suggestion
- [ ] **Activity Center (Notifications)**: Bell and panel use tenant_id/user_id from auth
- [ ] **Second Brain**: Inbox, Timeline, Life Areas, Suggestions load
- [ ] **Life Graph**: Nodes/edges display from getGraphV1
- [ ] **Connections**: List and ConnectorCard use tenant/user from store
- [ ] **Think panel**: askV1 uses tenant from store
- [ ] **Insights / Graph / Agents / Decisions**: Work with authenticated context

## 6. DOCKER SERVICES

- [ ] **Start order**: mongodb, postgres, redis, qdrant, kafka, opa → kirp-api → kirp-agent-processor, kirp-dashboard
- [ ] **Healthchecks**: All pass
- [ ] **Env consistency**: MONGO_URI, POSTGRES_URI, KAFKA_BOOTSTRAP_SERVERS match across API and Processor

## Post-activation (steps 6–8)

After completing activation steps 1–5 and 6–8:

- [ ] **Step 6 – JWT on all v1 APIs**: Graph, Reminders, Connections use `get_tenant_context(request)`; no tenant_id/user_id from query for scoping (query params ignored when auth present). Verify: same token returns your data on `/api/v1/graph`, `/api/v1/reminders/upcoming`, `/api/v1/connections`.
- [ ] **Step 7 – Error and empty states**: Decisions page shows error and retry when list fails; Insights/History/Tasks show clear empty states. No silent failures on load.
- [ ] **Step 8 – This checklist**: Run the Quick Verify script below before release.

## Quick Test Commands

```bash
# Auth
curl -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"dev@localhost","password":"dev"}'

# Ingest (replace TOKEN)
curl -X POST http://localhost:8000/api/v1/ingest -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d '{"content":"Test ingest"}'

# History
curl http://localhost:8000/api/v1/history -H "Authorization: Bearer TOKEN"
```

## Quick Verify (post-activation)

Run `./scripts/verify_activation.sh` (or set API_URL and run the commands below) to sanity-check auth and JWT-backed endpoints.

```bash
# Get token first, then:
export TOKEN="<access_token from login response>"
export API_URL="${API_URL:-http://localhost:8000}"

curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/history?limit=5"        # expect 200
curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/notifications"       # expect 200
curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/graph?limit_nodes=10" # expect 200
curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/reminders/upcoming"   # expect 200
curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/connections"         # expect 200
```
