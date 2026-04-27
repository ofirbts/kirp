#!/usr/bin/env bash
set -euo pipefail

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Dirty tree detected. Commit or stash changes before release checks."
  git status --short
  exit 1
fi

echo "Working tree is clean."
