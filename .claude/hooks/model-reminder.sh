#!/bin/bash
# Hook 3: After editing backend/models/*.py, remind to update frontend/src/types/index.ts

f=$(jq -r '.tool_input.file_path // empty')
echo "$f" | grep -qE 'backend/models/[^/]+\.py$' || exit 0

echo "Reminder: Pydantic model changed — check frontend/src/types/index.ts for matching TypeScript type updates (StateVector, EnrichedFlight, ApiResponse, etc.)."
