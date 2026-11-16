#!/usr/bin/env bash
# Reset + start the server, then run the API/integration tests (live HTTP). Usage: scripts/test_api.sh [pytest args]
set -euo pipefail
. "$(dirname "$0")/env.sh"
"$ROOT/scripts/stop.sh"; sleep 1; "$ROOT/scripts/reset.sh" >/dev/null; "$ROOT/scripts/start.sh" >/dev/null
cd "$ROOT/tests/team"
if [ "$#" -eq 0 ]; then set -- api; fi
exec "$ROOT/.venv/bin/python" -m pytest "$@"
