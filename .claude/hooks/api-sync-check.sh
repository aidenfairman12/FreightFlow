#!/bin/bash
# Hook 1: After editing backend/api/routes/*.py, check that route paths exist in frontend/src/lib/api.ts

f=$(jq -r '.tool_input.file_path // empty')
echo "$f" | grep -qE 'backend/api/routes/[^/]+\.py$' || exit 0

REPO=/Users/Aiden/Desktop/PlaneLogistics
API_TS="$REPO/frontend/src/lib/api.ts"

echo "=== API Route ↔ Frontend Sync ==="
grep -oE '@router\.(get|post|put|delete|patch)\("[^"]*"' "$f" 2>/dev/null \
  | grep -oE '"[^"]*"' | tr -d '"' | sort -u \
  | while IFS= read -r path; do
      count=$(grep -c "$path" "$API_TS" 2>/dev/null || echo 0)
      if [ "$count" -eq 0 ]; then
        echo "  MISSING in api.ts: $path"
      else
        echo "  OK ($count ref): $path"
      fi
    done
