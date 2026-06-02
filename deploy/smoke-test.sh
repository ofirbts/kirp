#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.prod.yml"
ENV_FILE="${ROOT_DIR}/.env.prod"
BASE_URL="http://localhost:8080"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Create it with STRIPE_SECRET_KEY, STRIPE_PRICE_ID, STRIPE_WEBHOOK_SECRET, DATABASE_URL, REDIS_URL." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

docker compose -f "${COMPOSE_FILE}" up -d --build

echo "Waiting for API health..."
for i in $(seq 1 60); do
  code=$(curl -sS -o /tmp/kirp_health.json -w "%{http_code}" "${BASE_URL}/health" || true)
  if [[ "${code}" == "200" ]]; then
    echo "health: 200"
    cat /tmp/kirp_health.json
    break
  fi
  sleep 2
  if [[ "${i}" == "60" ]]; then
    echo "API did not become healthy in time" >&2
    docker compose -f "${COMPOSE_FILE}" logs kirp-api | tail -n 120
    exit 1
  fi
done

TENANT_NAME="acme-smoke-$(date +%s)"
ONBOARD_PAYLOAD="{\"tenant_name\":\"${TENANT_NAME}\",\"email\":\"user@acme.com\"}"
ONBOARD_CODE=$(curl -sS -o /tmp/kirp_onboard.json -w "%{http_code}" \
  -X POST "${BASE_URL}/api/v1/onboarding" \
  -H "Content-Type: application/json" \
  -d "${ONBOARD_PAYLOAD}")
echo "onboarding: ${ONBOARD_CODE}"
cat /tmp/kirp_onboard.json
[[ "${ONBOARD_CODE}" == "201" ]]

TENANT_ID=$(python3 - <<'PY'
import json
with open('/tmp/kirp_onboard.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(data.get('tenant_id',''))
PY
)

if [[ -z "${TENANT_ID}" ]]; then
  echo "Missing tenant_id from onboarding response" >&2
  exit 1
fi

if [[ -z "${STRIPE_WEBHOOK_SECRET:-}" ]]; then
  echo "Missing STRIPE_WEBHOOK_SECRET in .env.prod" >&2
  exit 1
fi

WEBHOOK_PAYLOAD="{\"id\":\"evt_smoke_1\",\"object\":\"event\",\"type\":\"customer.subscription.created\",\"data\":{\"object\":{\"id\":\"sub_smoke_1\",\"object\":\"subscription\",\"metadata\":{\"tenant_id\":\"${TENANT_ID}\"}}}}"
TS="$(date +%s)"
SIGNED_PAYLOAD="${TS}.${WEBHOOK_PAYLOAD}"
SIG=$(printf "%s" "${SIGNED_PAYLOAD}" | openssl dgst -sha256 -hmac "${STRIPE_WEBHOOK_SECRET}" -hex | awk '{print $2}')
HEADER="t=${TS},v1=${SIG}"

WEBHOOK_CODE=$(curl -sS -o /tmp/kirp_webhook.json -w "%{http_code}" \
  -X POST "${BASE_URL}/api/v1/stripe/webhook" \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: ${HEADER}" \
  -d "${WEBHOOK_PAYLOAD}")
echo "stripe_webhook: ${WEBHOOK_CODE}"
cat /tmp/kirp_webhook.json
[[ "${WEBHOOK_CODE}" == "200" ]]

echo "SMOKE_OK: health=200 onboarding=201 webhook=200"
