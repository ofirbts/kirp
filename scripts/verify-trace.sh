#!/usr/bin/env bash
# PASS/FAIL: one trace_id must appear in all expected ingest pipeline JSON log lines.
#
# Usage:
#   TRACE_ID=tr_abc123 ./scripts/verify-trace.sh combined.log
#   docker compose ... logs api worker 2>&1 | TRACE_ID=tr_abc123 ./scripts/verify-trace.sh
#
# Host-side runs: use KAFKA_BOOTSTRAP_SERVERS pointing at a listener that advertises a
# host-reachable address (e.g. localhost:9093). See docs/TRACE_VERIFICATION.md.

set -euo pipefail

TRACE_ID="${TRACE_ID:-}"

if [[ -z "$TRACE_ID" ]]; then
  echo "FAIL: set TRACE_ID (returned by POST /api/v1/ingest)" >&2
  exit 1
fi

if [[ $# -ge 1 && "$1" != "-" ]]; then
  LOG_FILE="$1"
else
  LOG_FILE=$(mktemp)
  trap 'rm -f "$LOG_FILE"' EXIT
  cat >"$LOG_FILE"
fi

line_has_event() {
  local ev="$1"
  grep -F "\"trace_id\": \"$TRACE_ID\"" "$LOG_FILE" | grep -Fq "\"event\": \"$ev\""
}

MISS=()
for ev in ingest_api_received kafka_emit_success kafka_processor_received \
          pipeline_started pipeline_completed kafka_processor_completed; do
  if ! line_has_event "$ev"; then
    MISS+=("$ev")
  fi
done

if [[ ${#MISS[@]} -gt 0 ]]; then
  echo "FAIL: trace_id=$TRACE_ID — no log line with both trace_id and event for: ${MISS[*]}" >&2
  echo "Failing stage(s): ${MISS[*]}" >&2
  echo "Sample grep: grep -F \"\\\"trace_id\\\": \\\"$TRACE_ID\\\"\" \"$LOG_FILE\" | head -20" >&2
  echo "Fix: if API logs exist but worker logs do not, check KAFKA_BOOTSTRAP_SERVERS / advertised.listeners (environment)." >&2
  exit 1
fi

echo "PASS: trace_id=$TRACE_ID present for ingest_api_received, kafka_emit_success, kafka_processor_received, pipeline_started, pipeline_completed, kafka_processor_completed"

if grep -F "\"trace_id\": \"$TRACE_ID\"" "$LOG_FILE" | grep -Fq "\"event\": \"kafka_processor_retrying\""; then
  echo "NOTE: kafka_processor_retrying also present for this trace_id (retry path exercised)."
fi
