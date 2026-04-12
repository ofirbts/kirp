#!/usr/bin/env bash
# Layer 0 — local quality gate (non-interactive). Same commands intended for CI.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== pytest tests/ =="
python3 -m pytest tests/ -q

echo "== tsc =="
npx tsc --noEmit

echo "== eslint (CI=true) =="
CI=true NEXT_TELEMETRY_DISABLED=1 npm run lint

echo "== next build =="
npm run build

echo "== ci-local: OK =="
