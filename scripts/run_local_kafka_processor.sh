#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
export ENV="${ENV:-development}"
export MONGO_URI="${MONGO_URI:-mongodb://root:example@localhost:27017/kirp?authSource=admin}"
export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9093}"
export QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
export POSTGRES_URI="${POSTGRES_URI:-postgresql+asyncpg://kirp_user:kirp_password@127.0.0.1:5432/kirp}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
unset OPA_URL
export KIRP_REQUIRE_OPA=0
exec python3 -m src.workers.kafka_processor "$@"
