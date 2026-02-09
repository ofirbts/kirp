#!/bin/bash
# Verify WebSocket and History pipeline
# Run with: ./scripts/verify_ws_and_history.sh
# Prerequisites: API running on localhost:8000, user dev@localhost/dev seeded

set -e
API="${API:-http://localhost:8000}"
echo "=== KIRP WebSocket & History Verification ==="
echo "API: $API"
echo ""

# 1. WebSocket: GET without Upgrade -> 426; with Upgrade -> 101. 404 = route missing.
echo "1. WebSocket /ws/notifications"
echo "   Path: $API/ws/notifications?tenant_id=default&user_id=dev"
RESP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  -H "Sec-WebSocket-Version: 13" \
  "$API/ws/notifications?tenant_id=default&user_id=dev" 2>/dev/null || echo "000")
if [[ "$RESP" == "404" ]]; then
  echo "   FAIL: WebSocket returns 404 (route not found)"
elif [[ "$RESP" == "426" ]] || [[ "$RESP" == "101" ]]; then
  echo "   OK: WebSocket endpoint exists (HTTP $RESP)"
else
  echo "   Response: HTTP $RESP (000=connection failed)"
fi
echo ""

# 2. Login
echo "2. Login dev@localhost / dev"
LOGIN=$(curl -s -X POST "$API/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@localhost","password":"dev"}')
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null)
if [ -z "$TOKEN" ]; then
  echo "   FAIL: No token. Response: $LOGIN"
  exit 1
fi
echo "   OK: Token obtained"
echo ""

# 3. Ingest
echo "3. Ingest"
INGEST=$(curl -s -X POST "$API/api/v1/ingest" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Verify history pipeline test at '"$(date -Iseconds)"'"}')
if echo "$INGEST" | grep -q '"ok":true'; then
  echo "   OK: Ingest accepted"
else
  echo "   FAIL: $INGEST"
  exit 1
fi
echo ""

# 4. Wait for processor
echo "4. Waiting 5s for Kafka processor..."
sleep 5
echo ""

# 5. History
echo "5. History API"
HIST=$(curl -s "$API/api/v1/history?limit=10" -H "Authorization: Bearer $TOKEN")
COUNT=$(echo "$HIST" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null)
if [ -z "$COUNT" ]; then COUNT=0; fi
if [ "$COUNT" -gt 0 ]; then
  echo "   OK: History returns $COUNT entries"
  echo "$HIST" | python3 -c "import sys,json; d=json.load(sys.stdin); print('   First:', d[0].get('title','')[:60] if d else '')" 2>/dev/null
else
  echo "   WARN: History empty. Response: $HIST"
fi
echo ""
echo "=== Done ==="
