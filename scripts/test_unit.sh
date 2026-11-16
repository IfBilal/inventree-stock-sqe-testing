#!/usr/bin/env bash
# Run own unit tests with branch coverage over the in-scope business logic. Usage: scripts/test_unit.sh [pytest args]
set -euo pipefail
. "$(dirname "$0")/env.sh"
export INVENTREE_DB_NAME="$ROOT/data/unit_test.sqlite3"   # never touch the app DB
export TESTING=1
cd "$ROOT/tests/team"
exec "$ROOT/.venv/bin/python" -m pytest unit "$@"
