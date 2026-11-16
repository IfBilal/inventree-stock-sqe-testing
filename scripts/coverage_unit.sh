#!/usr/bin/env bash
# Run the unit suite with branch coverage over upstream stock code, export XML (for Sonar) + JSON, and check in-scope per-function coverage.
set -euo pipefail
. "$(dirname "$0")/env.sh"
export INVENTREE_DB_NAME="$ROOT/data/unit_test.sqlite3" TESTING=1
mkdir -p "$ROOT/evidence/coverage"
cd "$ROOT/tests/team"
"$ROOT/.venv/bin/python" -m coverage run --branch --rcfile="$ROOT/tests/team/.coveragerc" -m pytest unit "$@"
"$ROOT/.venv/bin/python" -m coverage xml --rcfile="$ROOT/tests/team/.coveragerc" -o "$ROOT/evidence/coverage/coverage.xml"
"$ROOT/.venv/bin/python" -m coverage json --rcfile="$ROOT/tests/team/.coveragerc" -o "$ROOT/evidence/coverage/coverage.json"
"$ROOT/.venv/bin/python" -m coverage report --rcfile="$ROOT/tests/team/.coveragerc" > "$ROOT/evidence/coverage/coverage_report.txt" || true
cd "$ROOT" && "$ROOT/.venv/bin/python" tools/scope_coverage.py evidence/coverage/coverage.json --md docs/COVERAGE_SCOPE.md
