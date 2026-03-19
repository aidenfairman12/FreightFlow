#!/bin/bash
# Hook 7: Before running bash commands that may expose .env credentials, warn the user

cmd=$(jq -r '.tool_input.command // empty')
echo "$cmd" | grep -qE '(printenv| env$|echo \$)' || exit 0

printf '{"systemMessage": "Warning: this command may expose .env credentials (OPENSKY_CLIENT_ID, OPENSKY_CLIENT_SECRET, etc.). Proceed only if intentional."}'
