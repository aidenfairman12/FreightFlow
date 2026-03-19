#!/bin/bash
# Hook 5: After editing backend/services/*.py, show all callers of functions defined in that file

f=$(jq -r '.tool_input.file_path // empty')
echo "$f" | grep -qE 'backend/services/[^/]+\.py$' || exit 0

BACKEND=/Users/Aiden/Desktop/PlaneLogistics/backend
echo "=== Service Function Callers ==="

grep -oE '^(async )?def [a-zA-Z_][a-zA-Z0-9_]+' "$f" 2>/dev/null | awk '{print $NF}' | while IFS= read -r fn; do
  hits=$(grep -rn "$fn" "$BACKEND" --include='*.py' 2>/dev/null \
    | grep -v "def $fn" \
    | grep -v "^$f:")
  if [ -n "$hits" ]; then
    echo "  $fn:"
    echo "$hits" | sed 's/^/    /'
  fi
done
