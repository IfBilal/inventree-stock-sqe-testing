#!/usr/bin/env bash
# Run the real mutmut 3.x on the business-rule functions (isolated copy of the backend; nothing in upstream/ is modified).
# Root cause of the earlier failure (docs/MUTATION.md §1): (1) mutmut reads list options from setup.cfg ONE PER LINE, comma lists were taken as one string and nothing was copied;
# (2) InvenTree's startup check `ensure_migrations_done()` calls sys.exit(1) on an un-migrated database, which mutmut reported only as "Child exited with code 1".
# Hence the database below is a migrated copy of the development database.
set -euo pipefail
. "$(dirname "$0")/env.sh"
"$ROOT/scripts/mutation_setup.sh" | tail -1
cp "$ROOT/data/inventree.sqlite3" "$ROOT/mutation/mm.sqlite3"
export INVENTREE_DB_NAME="$ROOT/mutation/mm.sqlite3"
cd "$ROOT/mutation/work" && rm -rf mutants
"$PY" -m mutmut run "$@"
"$PY" -m mutmut results > "$ROOT/evidence/mutation/mutmut_results.txt" || true
