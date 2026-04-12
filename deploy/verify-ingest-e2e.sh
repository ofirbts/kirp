#!/usr/bin/env bash
# Prove one real path: signup → JWT → POST /api/v1/ingest → Kafka → processor → pipeline → run status.
# Works with the FULL stack (repo root: docker compose up) — API :8000, Kafka + kirp-agent-processor running.
# Minimal deploy (deploy/docker-compose.prod.yml) has NO Kafka: ingest returns 503 — script explains that.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="${KIRP_VERIFY_API_URL:-http://localhost:8000}"
BASE_URL="${BASE_URL%/}"
POLL_SEC="${VERIFY_INGEST_POLL_SEC:-90}"
SLEEP_SEC="${VERIFY_INGEST_SLEEP_SEC:-2}"

TS="$(date +%s)"
VERIFY_EMAIL="${VERIFY_EMAIL:-kirp-ingest-${TS}@example.com}"
VERIFY_PASSWORD="${VERIFY_PASSWORD:-IngestE2E9${TS}!}"
VERIFY_NAME="${VERIFY_NAME:-KIRP ingest E2E}"

echo "== KIRP ingest E2E verify =="
echo "API: ${BASE_URL}"
echo ""

code=$(curl -sS -o /tmp/kirp_ingest_signup.json -w "%{http_code}" \
  -X POST "${BASE_URL}/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${VERIFY_EMAIL}\",\"password\":\"${VERIFY_PASSWORD}\",\"name\":\"${VERIFY_NAME}\"}" || true)
echo "signup: HTTP ${code}"
if [[ "${code}" != "201" ]]; then
  cat /tmp/kirp_ingest_signup.json 2>/dev/null || true
  echo "" >&2
  echo "Fix: use a new VERIFY_EMAIL or ensure API is up (curl ${BASE_URL}/healthz)." >&2
  exit 1
fi

TOKEN=$(python3 - <<'PY'
import json
with open("/tmp/kirp_ingest_signup.json", "r", encoding="utf-8") as f:
    d = json.load(f)
print(d.get("access_token") or "")
PY
)
if [[ -z "${TOKEN}" ]]; then
  echo "Missing access_token" >&2
  exit 1
fi

ing_code=$(curl -sS -o /tmp/kirp_ingest_post.json -w "%{http_code}" \
  -X POST "${BASE_URL}/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d "{\"content\":\"KIRP E2E verify ${TS} — one line ingest\",\"source\":\"e2e_verify\"}" || true)
echo "ingest: HTTP ${ing_code}"
cat /tmp/kirp_ingest_post.json
echo ""

if [[ "${ing_code}" == "503" ]]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "מה קרה? השרת אומר: אין אוטובוס אירועים (Kafka לא מחובר)."
  echo ""
  echo "מה לעשות (פשוט):"
  echo "  1) פתח טרמינל בתיקיית הפרויקט (איפה יש את הקובץ docker-compose.yml)."
  echo "  2) הרץ:  docker compose up -d"
  echo "  3) חכה 1–2 דקות עד שהכל ירוק."
  echo "  4) הרץ שוב את הסקריפט הזה (בלי לשנות כלום)."
  echo ""
  echo "אם אתה בכוונה על stack מינימלי (deploy בלבד) — שם אין Kafka;"
  echo "  אז ingest לא יכול לעבוד שם; זה צפוי."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 3
fi

if [[ "${ing_code}" != "200" ]]; then
  echo "ingest failed" >&2
  exit 1
fi

RUN_ID=$(python3 - <<'PY'
import json
with open("/tmp/kirp_ingest_post.json", "r", encoding="utf-8") as f:
    d = json.load(f)
print(d.get("run_id") or "")
PY
)
if [[ -z "${RUN_ID}" ]]; then
  echo "No run_id in ingest response" >&2
  exit 1
fi

echo "Polling run status: ${RUN_ID} (max ${POLL_SEC}s) ..."
start_ts=$(date +%s)
end_ts=$((start_ts + POLL_SEC))
ok=0
while (( $(date +%s) < end_ts )); do
  st_code=$(curl -sS -o /tmp/kirp_ingest_status.json -w "%{http_code}" \
    "${BASE_URL}/api/v1/run/${RUN_ID}/status" \
    -H "Authorization: Bearer ${TOKEN}" || true)
  if [[ "${st_code}" == "200" ]]; then
    if python3 - <<'PY'
import json

with open("/tmp/kirp_ingest_status.json", "r", encoding="utf-8") as f:
    d = json.load(f)
steps = d.get("timeline") or []
state = (d.get("state") or "").lower()
done = state in ("completed", "failed")
pipe_done = any(
    (s.get("step") == "pipeline_complete" and (s.get("status") or "").lower() == "completed")
    for s in steps
    if isinstance(s, dict)
)
reg_done = any(
    (s.get("step") == "registry_dispatch" and (s.get("status") or "").lower() == "completed")
    for s in steps
    if isinstance(s, dict)
)
if pipe_done or (done and reg_done):
    raise SystemExit(0)
raise SystemExit(1)
PY
    then
      ok=1
      break
    fi
  fi
  sleep "${SLEEP_SEC}"
done

if [[ "${ok}" != "1" ]]; then
  echo "Timeout: pipeline did not complete in time." >&2
  echo "Last status:" >&2
  cat /tmp/kirp_ingest_status.json 2>/dev/null || true
  echo "" >&2
  echo "Check: docker logs kirp-agent-processor   (Kafka consumer + pipeline)" >&2
  exit 4
fi

echo ""
echo "INGEST_E2E_OK: run_id=${RUN_ID}"
python3 - <<'PY'
import json
with open("/tmp/kirp_ingest_status.json", "r", encoding="utf-8") as f:
    d = json.load(f)
print("state:", d.get("state"))
print("steps:", len(d.get("timeline") or []))
PY
echo ""
echo "UI login (same user as signup):"
echo "  ${VERIFY_EMAIL} / ${VERIFY_PASSWORD}"
