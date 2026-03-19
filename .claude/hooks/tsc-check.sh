#!/bin/bash
# Hook 2: After editing frontend/src/types/index.ts, run tsc --noEmit to catch type errors

f=$(jq -r '.tool_input.file_path // empty')
echo "$f" | grep -q 'frontend/src/types/index\.ts$' || exit 0

echo "=== TypeScript Check ==="
FRONTEND=/Users/Aiden/Desktop/PlaneLogistics/frontend
TSC="$FRONTEND/node_modules/.bin/tsc"
if [ ! -x "$TSC" ]; then
  echo "  (skipped — run 'npm install' in frontend/ first)"
  exit 0
fi
cd "$FRONTEND" && "$TSC" --noEmit 2>&1 | head -30
