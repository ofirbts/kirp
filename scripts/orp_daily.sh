#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
export KIRP_API_URL="${KIRP_API_URL:-http://127.0.0.1:8000}"
export SKIP_AUTH=0
export STAGING_SMOKE_POLL_SEC="${STAGING_SMOKE_POLL_SEC:-180}"
exec python3 scripts/orp_program.py daily "$@"
