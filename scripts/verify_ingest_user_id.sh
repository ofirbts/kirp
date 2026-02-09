#!/usr/bin/env bash
# Verify ingest uses REAL user_id from JWT (not "dev").
# Run with stack up: docker compose up -d
# Expect: processor logs show user=<real_uuid> not user=dev

set -euo pipefail
API="${API:-http://localhost:8000}"

echo "=== 1. Login (dev user from seed) ==="
# Try dev@localhost (seed default); if email validation rejects it, try dev@example.com after signup
LOGIN=$(curl -s -X POST "$API/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@localhost","password":"dev"}')
TOKEN=$(echo "$LOGIN" | jq -r '.access_token // empty')
USER_ID=$(echo "$LOGIN" | jq -r '.user.id // empty')
TENANT_ID=$(echo "$LOGIN" | jq -r '.user.tenant_id // empty')

if [[ -z "$TOKEN" || -z "$USER_ID" ]]; then
  echo "Login failed. Response: $LOGIN"
  exit 1
fi
echo "Logged in: user_id=$USER_ID tenant_id=$TENANT_ID"

echo ""
echo "=== 2. Ingest with JWT ==="
INGEST=$(curl -s -w "\n%{http_code}" -X POST "$API/api/v1/ingest" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Verify user_id from JWT"}')
BODY=$(echo "$INGEST" | sed '$d')
CODE=$(echo "$INGEST" | tail -n1)
echo "Ingest response: HTTP $CODE"
echo "$BODY" | jq . 2>/dev/null || echo "$BODY"

if [[ "$CODE" != "200" ]]; then
  echo "Ingest failed (expected 200)"
  exit 1
fi

echo ""
echo "=== 3. Check processor logs ==="
echo "Run: docker logs kirp-agent-processor 2>&1 | tail -20"
echo "Expected: [INGEST] event created: ... tenant=$TENANT_ID user=$USER_ID"
echo "          [INGEST] event processed: ... tenant=$TENANT_ID user=$USER_ID"
docker logs kirp-agent-processor 2>&1 | tail -20
