#!/bin/bash
# Hook 6: After editing db/init.sql, remind to check SQLAlchemy models for drift

f=$(jq -r '.tool_input.file_path // empty')
echo "$f" | grep -q 'db/init\.sql$' || exit 0

echo "Reminder: db/init.sql changed — check backend/models/ for SQLAlchemy model drift. TimescaleDB schema and ORM models must stay in sync."
