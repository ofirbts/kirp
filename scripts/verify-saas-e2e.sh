#!/usr/bin/env bash
# End-to-end SaaS payment verification (see docs/SAAS_E2E_PAYMENT.md).
# Usage:
#   ./scripts/verify-saas-e2e.sh              # signup → trial → checkout URL → wait for browser checkout → poll active
#   ./scripts/verify-saas-e2e.sh --stripe-trigger   # same + Stripe CLI trigger instead of waiting (needs stripe listen)
set -euo pipefail

API_BASE="${API_BASE_URL:-http://localhost:8000}"
API_BASE="${API_BASE%/}"
STATE_FILE="${KIRP_SAAS_E2E_STATE:-/tmp/kirp_saas_e2e_state.json}"
USE_TRIGGER=0
if [[ "${1:-}" == "--stripe-trigger" ]]; then
  USE_TRIGGER=1
fi
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  sed -n '2,6p' "$0"
  exit 0
fi

die() { echo "ERROR: $*" >&2; exit 1; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }

need_cmd curl
need_cmd python3

json_get() {
  local expr=$1
  python3 -c "import json,sys; d=json.load(sys.stdin); print(d${expr})"
}

http_get() {
  local url=$1
  shift
  curl -sS "$url" "$@"
}

signup_and_checkout() {
  local suffix
  suffix=$(python3 -c "import time; print(int(time.time()))")
  local email="saas-e2e-${suffix}@kirp-e2e.test"
  local password="${E2E_PASSWORD:-KirpE2EPass123456}"
  local name="SaaS E2E"

  echo "==> POST /api/v1/auth/signup ($email)"
  local signup_body
  signup_body=$(curl -sS -X POST "${API_BASE}/api/v1/auth/signup" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${email}\",\"password\":\"${password}\",\"name\":\"${name}\"}") || die "signup curl failed"

  local token tenant_id
  token=$(printf '%s' "$signup_body" | json_get "['access_token']") || die "signup: no access_token (body: $signup_body)"
  tenant_id=$(printf '%s' "$signup_body" | json_get "['user']['tenant_id']") || die "signup: no tenant_id"

  echo "    tenant_id=$tenant_id"
  python3 -c "import json, pathlib, sys; pathlib.Path(sys.argv[1]).write_text(json.dumps({'api_base':sys.argv[2],'email':sys.argv[3],'password':sys.argv[4],'token':sys.argv[5],'tenant_id':sys.argv[6]}))" \
    "$STATE_FILE" "$API_BASE" "$email" "$password" "$token" "$tenant_id"

  echo "==> GET /api/v1/tenant/${tenant_id}/usage/details (expect trial)"
  local ubody
  ubody=$(http_get "${API_BASE}/api/v1/tenant/${tenant_id}/usage/details" \
    -H "Authorization: Bearer ${token}") || die "usage/details curl failed"
  local life
  life=$(printf '%s' "$ubody" | json_get "['lifecycle']") || die "usage: no lifecycle"
  [[ "$life" == "trial" ]] || die "expected lifecycle=trial after signup, got: $life (body: $ubody)"
  echo "    OK lifecycle=trial"

  echo "==> POST /api/v1/tenant/${tenant_id}/stripe/checkout-session"
  local cbody
  cbody=$(curl -sS -X POST "${API_BASE}/api/v1/tenant/${tenant_id}/stripe/checkout-session" \
    -H "Authorization: Bearer ${token}" \
    -H "Content-Type: application/json" \
    -d '{}') || die "checkout-session curl failed"

  if ! printf '%s' "$cbody" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('url') else 1)"; then
    die "checkout-session failed (set STRIPE_SECRET_KEY + STRIPE_PRICE_ID on API): $cbody"
  fi

  local surl
  surl=$(printf '%s' "$cbody" | json_get "['url']") || die "no checkout url in: $cbody"
  echo "    Checkout URL:"
  echo "    $surl"
  echo ""
  echo "    Open the URL, pay with test card 4242 4242 4242 4242 (Stripe test mode)."
  echo "    Ensure: stripe listen --forward-to ${API_BASE}/api/v1/stripe/webhook"
  echo "    and STRIPE_WEBHOOK_SECRET matches the whsec_ from that command."
}

poll_active() {
  local token tenant_id api_b
  token=$(python3 -c "import json, pathlib; j=json.loads(pathlib.Path('${STATE_FILE}').read_text()); print(j['token'])")
  tenant_id=$(python3 -c "import json, pathlib; j=json.loads(pathlib.Path('${STATE_FILE}').read_text()); print(j['tenant_id'])")
  api_b=$(python3 -c "import json, pathlib; j=json.loads(pathlib.Path('${STATE_FILE}').read_text()); print(j['api_base'])")
  api_b="${api_b%/}"

  echo "==> Polling GET .../usage/details until lifecycle=active (max ~3 min)"
  local i=0
  while [[ $i -lt 60 ]]; do
    local ubody life
    ubody=$(http_get "${api_b}/api/v1/tenant/${tenant_id}/usage/details" \
      -H "Authorization: Bearer ${token}") || die "poll failed"
    life=$(printf '%s' "$ubody" | json_get "['lifecycle']") || true
    if [[ "$life" == "active" ]]; then
      echo "    OK lifecycle=active"
      echo ""
      echo "PASS: tenant is active (API). Open /dashboard logged in as this user to confirm UI."
      echo "State file: ${STATE_FILE}"
      exit 0
    fi
    echo "    ... lifecycle=$life (attempt $((i + 1))/60)"
    sleep 3
    i=$((i + 1))
  done
  die "timeout waiting for lifecycle=active (last lifecycle may still be trial — check webhook forwarding)"
}

stripe_trigger_path() {
  need_cmd stripe
  local tenant_id
  tenant_id=$(python3 -c "import json, pathlib; print(json.loads(pathlib.Path('${STATE_FILE}').read_text())['tenant_id'])")

  echo "==> stripe trigger customer.subscription.created (metadata.tenant_id=$tenant_id)"
  stripe trigger customer.subscription.created \
    --override "subscription:metadata.tenant_id=${tenant_id}" \
    || die "stripe trigger failed (is 'stripe listen' running and logged in?)"
}

signup_and_checkout

if [[ "$USE_TRIGGER" == 1 ]]; then
  stripe_trigger_path
  poll_active
else
  echo ""
  read -r -p "Press Enter after you have completed Checkout in the browser (webhook delivered)... " _
  poll_active
fi
