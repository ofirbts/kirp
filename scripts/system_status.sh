#!/usr/bin/env bash
# Master system status: ports, Docker, processes, CPU/RAM, health checks.
# Usage: ./scripts/system_status.sh
# Works on Linux (WSL2) and macOS.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

_ok()  { echo -e "${GREEN}[OK]${NC} $*"; }
_fail(){ echo -e "${RED}[FAIL]${NC} $*"; }
_warn(){ echo -e "${YELLOW}[WARN]${NC} $*"; }
_info(){ echo -e "${BLUE}[INFO]${NC} $*"; }

echo ""
echo "========== KIRP / Brand OS — System Status =========="
echo ""

# --- Active ports (listening) ---
_info "Listening ports (relevant):"
if command -v lsof >/dev/null 2>&1; then
  PORTS=$(lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | awk 'NR==1 || $9 ~ /:(8000|8001|8002|3000|3001|8501|6379|5432|8080|8081|9092|6333)(\/|$)/ {print $1, $2, $9}' | column -t 2>/dev/null || true)
  if [ -n "$PORTS" ]; then
    echo "$PORTS" | while read -r line; do echo "  $line"; done
  else
    # Fallback: show all listening ports with port numbers we care about
    lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | awk 'NR==1 {print} $9 ~ /:[0-9]+$/ {split($9,a,":"); p=a[length(a)]; if(p+0>=8000 && p+0<=9000 || p+0>=3000 && p+0<=3010 || p==6379 || p==5432) print}' | head -30
  fi
else
  _warn "lsof not installed; run: scripts/ports.sh for port list"
fi
echo ""

# --- Docker ---
_info "Docker containers:"
if command -v docker >/dev/null 2>&1; then
  if docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null | head -25; then
    _ok "Docker available"
  else
    _warn "Docker not running or no containers"
  fi
else
  _warn "Docker not installed"
fi
echo ""

# --- Processes: Python / Node / Uvicorn ---
_info "Relevant processes (python, node, uvicorn):"
if command -v ps >/dev/null 2>&1; then
  ps aux 2>/dev/null | grep -E 'uvicorn|python.*api\.main|node.*next|streamlit' | grep -v grep | awk '{printf "  %-8s %5s %4s%% %4s%% %s\n", $1, $2, $3, $4, $11}' | head -15
  if [ ${PIPESTATUS[0]} -ne 0 ] 2>/dev/null || ! ps aux 2>/dev/null | grep -qE 'uvicorn|node.*next'; then
    _warn "No uvicorn/node (api/ui) processes found"
  fi
else
  _warn "ps not available"
fi
echo ""

# --- CPU / RAM top ---
_info "Top CPU usage (first 5):"
if command -v ps >/dev/null 2>&1; then
  ps aux --sort=-%cpu 2>/dev/null | head -6 | awk 'NR==1 {print "  " $0} NR>1 {printf "  %-12s %5s %5s%% %5s%% %s\n", $1, $2, $3, $4, substr($0, index($0,$11))}' || \
  ps -eo pid,pcpu,pmem,comm -r 2>/dev/null | head -6
else
  _warn "ps not available"
fi
echo ""

_info "Top memory usage (first 5):"
if command -v ps >/dev/null 2>&1; then
  ps aux --sort=-%mem 2>/dev/null | head -6 | awk 'NR==1 {print "  " $0} NR>1 {printf "  %-12s %5s %5s%% %5s%% %s\n", $1, $2, $3, $4, substr($0, index($0,$11))}' || \
  ps -eo pid,pcpu,pmem,comm -r 2>/dev/null | head -6
fi
echo ""

# --- Health checks ---
_info "Health checks:"
check_http() {
  local url=$1
  local name=$2
  if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "$url" 2>/dev/null | grep -q 200; then
    _ok "$name ($url)"
  else
    _fail "$name ($url)"
  fi
}

check_http "http://127.0.0.1:8000/health" "KIRP API (8000)"
check_http "http://127.0.0.1:8002/health" "Brand OS API (8002)"
check_http "http://127.0.0.1:8001/metrics" "Monitoring (8001)"
check_http "http://localhost:3001" "Brand OS UI (3001)"
check_http "http://127.0.0.1:8501" "Streamlit dashboard (8501)"

echo ""
echo "========== End system status =========="
echo ""
