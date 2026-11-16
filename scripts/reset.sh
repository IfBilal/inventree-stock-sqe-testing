#!/usr/bin/env bash
# Reset the app to the deterministic seeded baseline (stops nothing; run with server stopped or it will reuse the file).
set -euo pipefail
. "$(dirname "$0")/env.sh"
rm -f "$INVENTREE_DB_NAME"; mkdir -p "$ROOT/data/media" "$ROOT/data/static" "$ROOT/data/backup"; touch "$INVENTREE_PLUGIN_FILE"
$MANAGE migrate --noinput >/dev/null 2>&1
$MANAGE shell < "$ROOT/scripts/seed_data.py" 2>&1 | grep SEED_OK
