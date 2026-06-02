#!/usr/bin/env bash
# Restart a Docker container or suggest how to restart a local service.
# Usage: ./scripts/restart_service.sh <service_name>
# Examples: ./scripts/restart_service.sh kirp-api
#           ./scripts/restart_service.sh brand-os-api
# Works on Linux (WSL2) and macOS.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

_ok()  { echo -e "${GREEN}[OK]${NC} $*"; }
_fail(){ echo -e "${RED}[FAIL]${NC} $*"; }
_warn(){ echo -e "${YELLOW}[WARN]${NC} $*"; }

SERVICE="$1"
if [ -z "$SERVICE" ]; then
  echo "Usage: $0 <service_name>"
  echo "  Docker: kirp-api, kirp-worker, kirp-dashboard, kirp-agent-processor, etc."
  echo "  Local:  brand-os-api (hint only), monitoring, ui (hint only)"
  exit 1
fi

# Docker restart
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  # Match container name (exact or partial)
  CONTAINER=$(docker ps -a --format '{{.Names}}' | grep -E "^${SERVICE}$|^.*${SERVICE}.*$" | head -1)
  if [ -n "$CONTAINER" ]; then
    _warn "Restarting Docker container: $CONTAINER"
    docker restart "$CONTAINER" && _ok "Restarted $CONTAINER" || _fail "Failed to restart $CONTAINER"
    exit 0
  fi
fi

# Local service hints (no actual restart of background processes from here)
case "$SERVICE" in
  brand-os-api)
    _warn "Brand OS API is a local process. Stop it (Ctrl+C) and run: uvicorn api.main:app --reload --port 8002"
    ;;
  monitoring)
    _warn "Monitoring is a local process. Stop it and run: uvicorn brand_os_monitoring.app:app --port 8001 --reload"
    ;;
  ui)
    _warn "UI is a local process. Stop it and run: npm run dev"
    ;;
  *)
    _fail "Unknown service: $SERVICE. Use a Docker container name (e.g. kirp-api) or: brand-os-api, monitoring, ui"
    exit 1
    ;;
esac
