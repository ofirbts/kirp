# Trace verification (post E2E)

Goal: follow one event across API → Kafka emit → worker → pipeline, with one `trace_id` end to end.

## 0) Bootstrap / networking (environment)

If the API runs on the host and Kafka inside Docker, the broker often advertises `kafka:9092`. The host then cannot reach the broker for consuming, so **`kafka_processor_*` and `pipeline_*` logs never appear** even when emit succeeds.

**Fix (pick one):**

- Point the client at a listener that advertises a host-reachable address, e.g. set `KAFKA_BOOTSTRAP_SERVERS=localhost:9093` when your compose maps a `PLAINTEXT_HOST` (or equivalent) port.
- Or align broker `advertised.listeners` with where API/worker processes run (ops change, not app code).

## 1) Emit one ingest

Use the token from `/tmp/kirp_saas_e2e_state.json`:

```bash
python3 - <<'PY'
import json,subprocess
s=json.load(open('/tmp/kirp_saas_e2e_state.json'))
api=s['api_base']; tok=s['token']
out=subprocess.check_output([
  'curl','-sS','-X','POST',f'{api}/api/v1/ingest',
  '-H',f'Authorization: Bearer {tok}',
  '-H','Content-Type: application/json',
  '-d','{"content":"trace verification event","source":"trace_verify"}'
],text=True)
print(out)
PY
```

Take the returned `trace_id`.

## 2) Automated PASS/FAIL (single trace)

Capture API + worker logs into one file, then:

```bash
export TRACE_ID='tr_...'   # from ingest response
./scripts/verify-trace.sh /path/to/combined.log
```

Or pipe:

```bash
docker compose -f deploy/docker-compose.prod.yml logs api worker 2>&1 \
  | TRACE_ID='tr_...' ./scripts/verify-trace.sh
```

The script requires **one JSON log line per stage** that includes **both** `"event": "<name>"` and `"trace_id": "<same id>"`.

If **FAIL**, the script prints the missing `event` name(s). Typical causes:

| Symptom | Likely layer | Fix |
|--------|----------------|-----|
| Only `ingest_*` / `kafka_emit_*` | Worker not consuming | Bootstrap / advertised listeners (environment) |
| `kafka_processor_failed` / retries | Processing | `reason` / `step` in JSON (code or deps) |
| No `stripe_webhook_*` | Not applicable to ingest trace | Use webhook flow separately |

## 3) Expected structured JSON logs (ingest path)

Happy path (each line includes `tenant_id`, `run_id`, `trace_id`):

- `ingest_api_received`
- `kafka_emit_success`
- `kafka_processor_received`
- `pipeline_started`
- `pipeline_completed`
- `kafka_processor_completed`

**Stripe webhook** path uses Stripe `event.id` as `trace_id` for correlation; `run_id` is JSON `null` (no KIRP run). Success: `stripe_webhook_received`, `stripe_webhook_processed`. Failures: `stripe_webhook_failed` with `step` and `reason`.

## 4) Failure visibility (structured)

| Failure | `event` | Notes |
|---------|---------|--------|
| Ingest API (non-HTTP) | `ingest_api_failed` | `tenant_id` / `trace_id` when known; `run_id` may be null |
| Kafka emit | `kafka_emit_failed` | `reason` |
| Processor | `kafka_processor_failed` | `step` (`tenant_validate`, `kafka_process`, `run_creation`, …), `reason` |
| Webhook | `stripe_webhook_failed` | `step`; `trace_id` null on signature failure |

Kafka processor retries:

- `kafka_processor_retrying` — same `trace_id` / `run_id` / `tenant_id` as the original attempt; `retry_attempt`, `retry_max`
- `kafka_processor_max_retries_exceeded` — after retries exhausted

**Controlled retry test (no broker):** `python3 -m pytest tests/test_kafka_processor_retry.py -v` — simulates `registry.dispatch` failing once, asserts second attempt succeeds and `kafka_processor_retrying` is logged with the same `trace_id`.

## 5) Manual grep (same trace_id through retries)

If a transient error triggers a retry, you should still see **one** `trace_id` on:

1. `kafka_processor_failed` (`retry_count`: 0, then 1, …)
2. `kafka_processor_retrying` between attempts
3. Final `kafka_processor_completed` (or `kafka_processor_max_retries_exceeded`)

Example:

```bash
grep -F "\"trace_id\": \"$TRACE_ID\"" combined.log | grep -E 'kafka_processor_(failed|retrying|completed|max_retries_exceeded)'
```
