#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m pip install --upgrade pip -q
python3 -m pip install -q -r requirements.txt -r requirements-dev.txt
python3 -c "import pytest_asyncio"
python3 -m pytest tests/ -q --tb=short
npm ci
npm run lint
npm run build
echo "ci_local: ALL PASSED"
