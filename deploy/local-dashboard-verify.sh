#!/usr/bin/env bash
# One-shot: signup a fresh dashboard user → JWT → /me → /stats (deploy stack on :8080).
# Does NOT run docker compose (use after: docker compose -f deploy/docker-compose.prod.yml up -d).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="${KIRP_VERIFY_API_URL:-http://localhost:8080}"
BASE_URL="${BASE_URL%/}"

# Override with your own test identity:
#   VERIFY_EMAIL=you@company.com VERIFY_PASSWORD='yourStrongPass1' VERIFY_NAME='Your Name' ./deploy/local-dashboard-verify.sh
TS="$(date +%s)"
# @example.com is valid for pydantic EmailStr; .local/.test are often rejected as reserved.
VERIFY_EMAIL="${VERIFY_EMAIL:-kirp-verify-${TS}@example.com}"
VERIFY_PASSWORD="${VERIFY_PASSWORD:-VerifyLocal9${TS}!}"
VERIFY_NAME="${VERIFY_NAME:-KIRP local verify}"

echo "== KIRP local dashboard verify =="
echo "API: ${BASE_URL}"
echo "User: ${VERIFY_EMAIL} (${VERIFY_NAME})"
echo ""

code=$(curl -sS -o /tmp/kirp_verify_signup.json -w "%{http_code}" \
  -X POST "${BASE_URL}/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${VERIFY_EMAIL}\",\"password\":\"${VERIFY_PASSWORD}\",\"name\":\"${VERIFY_NAME}\"}" || true)
echo "signup: HTTP ${code}"
if [[ "${code}" != "201" ]]; then
  cat /tmp/kirp_verify_signup.json 2>/dev/null || true
  echo "" >&2
  echo "If you see 'Email already registered', set VERIFY_EMAIL to a new address or delete the user in Mongo." >&2
  exit 1
fi

TOKEN=$(python3 - <<'PY'
import json
with open("/tmp/kirp_verify_signup.json", "r", encoding="utf-8") as f:
    d = json.load(f)
print(d.get("access_token") or "")
PY
)
if [[ -z "${TOKEN}" ]]; then
  echo "Missing access_token in signup response" >&2
  exit 1
fi

me_code=$(curl -sS -o /tmp/kirp_verify_me.json -w "%{http_code}" \
  "${BASE_URL}/api/v1/auth/me" \
  -H "Authorization: Bearer ${TOKEN}" || true)
echo "auth/me: HTTP ${me_code}"
cat /tmp/kirp_verify_me.json
echo ""

if [[ "${me_code}" != "200" ]]; then
  exit 1
fi

stats_code=$(curl -sS -o /tmp/kirp_verify_stats.json -w "%{http_code}" \
  "${BASE_URL}/api/v1/stats" \
  -H "Authorization: Bearer ${TOKEN}" || true)
echo "stats: HTTP ${stats_code}"
cat /tmp/kirp_verify_stats.json
echo ""

if [[ "${stats_code}" != "200" ]]; then
  exit 1
fi

echo ""
echo "VERIFY_OK: signup=201 me=200 stats=200"
echo ""
echo "Login to the UI with:"
echo "  Email:    ${VERIFY_EMAIL}"
echo "  Password: ${VERIFY_PASSWORD}"
echo ""
echo "Next:"
echo "  1. http://localhost:3100/login"
echo "  2. Or re-run with your own identity: VERIFY_EMAIL=... VERIFY_PASSWORD=... VERIFY_NAME=... $0"
