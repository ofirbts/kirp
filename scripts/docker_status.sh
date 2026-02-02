#!/usr/bin/env bash
# Docker containers: status, ports, health, memory. Optional restart.
# Usage: ./scripts/docker_status.sh [restart <container_name>]
# Works on Linux (WSL2) and macOS.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

_ok()  { echo -e "${GREEN}[OK]${NC} $*"; }
_fail(){ echo -e "${RED}[FAIL]${NC} $*"; }
_warn(){ echo -e "${YELLOW}[WARN]${NC} $*"; }

if ! command -v docker >/dev/null 2>&1; then
  _fail "Docker not installed or not in PATH"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  _fail "Docker daemon not running"
  exit 1
fi

if [ "$1" = "restart" ] && [ -n "$2" ]; then
  _warn "Restarting container: $2"
  docker restart "$2" && _ok "Restarted $2" || _fail "Failed to restart $2"
  exit 0
fi

echo "Docker containers (all):"
echo "------------------------"
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

echo ""
echo "Docker stats (running, sample):"
echo "--------------------------------"
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}' 2>/dev/null | head -20

echo ""
echo "To restart a container: ./scripts/docker_status.sh restart <container_name>"
echo "Example: ./scripts/docker_status.sh restart kirp-api"
