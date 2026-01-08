#!/bin/bash
echo "=== TREE ==="
tree -I "venv|__pycache__|.git|data" app

echo
echo "=== GIT STATUS ==="
git status

echo
echo "=== RECENT COMMITS ==="
git log --oneline -5
