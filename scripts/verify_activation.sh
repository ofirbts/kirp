#!/usr/bin/env bash
# Post-activation verification: auth + JWT-backed v1 endpoints (steps 6–8).
# Usage: API_URL=http://localhost:8000 ./scripts/verify_activation.sh
# Or:   ./scripts/verify_activation.sh   (uses default API_URL)

set -e
API_URL="${API_URL:-http://localhost:8000}"

echo "=== KIRP post-activation verify (API: $API_URL) ==="

# Login and get token
RESP=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@localhost","password":"devdevdev"}' 2>/dev/null || true)
TOKEN=$(echo "$RESP" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
if [ -z "$TOKEN" ]; then
  echo "FAIL: Login did not return access_token. Check API and dev user seed."
  exit 1
fi
echo "OK: Login returned token"

# Endpoints that must use JWT (tenant/user from context)
for path in "/api/v1/history?limit=5" "/api/v1/notifications" "/api/v1/graph?limit_nodes=10" "/api/v1/reminders/upcoming" "/api/v1/connections"; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API_URL$path")
  if [ "$CODE" = "200" ]; then
    echo "OK: $path → $CODE"
  else
    echo "FAIL: $path → $CODE (expected 200)"
    exit 1
  fi
done

echo "=== All checks passed ==="
