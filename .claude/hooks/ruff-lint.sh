#!/bin/bash
# Hook 4: After editing any .py file, run ruff check on that file

f=$(jq -r '.tool_input.file_path // empty')
echo "$f" | grep -q '\.py$' || exit 0

RUFF=$(command -v ruff 2>/dev/null \
  || ls /Users/Aiden/Desktop/PlaneLogistics/backend/.venv/bin/ruff 2>/dev/null \
  || true)

if [ -z "$RUFF" ]; then
  echo "  (ruff not found — install with: pip install ruff)"
  exit 0
fi

cd /Users/Aiden/Desktop/PlaneLogistics/backend && "$RUFF" check "$f" 2>&1 || true
