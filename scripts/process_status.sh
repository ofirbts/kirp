#!/usr/bin/env bash
# Show Python/Node/Uvicorn processes with CPU/RAM and optional tree.
# Usage: ./scripts/process_status.sh [--tree]
# Works on Linux (WSL2) and macOS.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

_ok()  { echo -e "${GREEN}[OK]${NC} $*"; }
_warn(){ echo -e "${YELLOW}[WARN]${NC} $*"; }

SHOW_TREE=false
[ "$1" = "--tree" ] && SHOW_TREE=true

echo "Relevant processes (python, node, uvicorn, streamlit):"
echo "------------------------------------------------------"
if command -v ps >/dev/null 2>&1; then
  # Linux: ps aux --sort=-%cpu; macOS: ps -eo pid,pcpu,pmem,comm
  if ps aux 2>/dev/null | grep -v grep | grep -qE 'python|node|uvicorn|streamlit'; then
    ps aux 2>/dev/null | grep -E 'python|node|uvicorn|streamlit' | grep -v grep | awk '{printf "%-10s %6s %5s%% %5s%% %s\n", $1, $2, $3, $4, substr($0, index($0,$11))}'
  else
    _warn "No matching processes found"
  fi
else
  _warn "ps not available"
fi

if [ "$SHOW_TREE" = true ]; then
  echo ""
  echo "Process tree (python/node):"
  echo "---------------------------"
  if command -v pstree >/dev/null 2>&1; then
    pstree -p 2>/dev/null | grep -E 'python|node|uvicorn' || true
  else
    # macOS often doesn't have pstree; show parent PID
    ps -eo pid,ppid,comm | grep -E 'python|node' | grep -v grep | head -20
  fi
fi
