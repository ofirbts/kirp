#!/usr/bin/env bash
# List all listening ports with process owner, PID, command.
# Usage: ./scripts/ports.sh [optional port number to filter]
# Works on Linux (WSL2) and macOS.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

_ok()  { echo -e "${GREEN}[OK]${NC} $*"; }
_fail(){ echo -e "${RED}[FAIL]${NC} $*"; }
_warn(){ echo -e "${YELLOW}[WARN]${NC} $*"; }

FILTER="$1"

if ! command -v lsof >/dev/null 2>&1; then
  _fail "lsof not installed. Install with: sudo apt-get install lsof (Linux) or brew install lsof (macOS)"
  exit 1
fi

echo "Listening ports (process, PID, port):"
echo "-------------------------------------"

if [ -n "$FILTER" ]; then
  if ! [[ "$FILTER" =~ ^[0-9]+$ ]]; then
    _warn "Filter must be a port number; showing all."
    FILTER=""
  fi
fi

if [ -n "$FILTER" ]; then
  lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | awk -v p="$FILTER" 'NR==1 {print} $9 ~ ":"p"$" || $9 ~ ":"p"/" {print}' | awk 'NR==1 {print "COMMAND\tPID\tUSER\tNODE\tNAME"; next} {printf "%s\t%s\t%s\t%s\t%s\n", $1, $2, $3, $9, $10}'
else
  lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | awk 'NR==1 {print "COMMAND\tPID\tUSER\tNODE\tNAME"; next} {printf "%s\t%s\t%s\t%s\t%s\n", $1, $2, $3, $9, $10}'
fi

echo ""
echo "If a port is blocked: run ./scripts/kill_port.sh <port> to free it."
echo "Example: ./scripts/kill_port.sh 8000"
