#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.prod.yml"

cp "${SCRIPT_DIR}/.env.prod.example" "${ROOT_DIR}/.env.prod"
echo "Copied deploy/.env.prod.example -> .env.prod"

docker compose -f "${COMPOSE_FILE}" up -d --build
"${SCRIPT_DIR}/smoke-test.sh"
