#!/bin/bash
set -e

echo "== Running backend tests =="
pytest -q tests/test_core.py tests/test_alerting.py tests/test_run_controller.py tests/test_api_run_status.py

echo "== Lint frontend =="
npm run lint

echo "== Build frontend =="
npm run build

echo "== Running E2E ingest =="
KIRP_VERIFY_API_URL=http://localhost:8080 bash deploy/verify-ingest-e2e.sh

echo "✅ ALL CHECKS PASSED"
