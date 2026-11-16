#!/usr/bin/env bash
# Reset + start the server, then run the Playwright E2E / usability / accessibility specs. Usage: scripts/test_e2e.sh [playwright args]
set -euo pipefail
. "$(dirname "$0")/env.sh"
"$ROOT/scripts/stop.sh"; sleep 1; "$ROOT/scripts/reset.sh" >/dev/null; "$ROOT/scripts/start.sh" >/dev/null
# warm up the freshly started server (first requests import lazily and are slow)
for u in /web/login /api/ /static/web/index.html; do
  if ! curl -s -o /dev/null "http://127.0.0.1:8000$u"; then echo "warm-up request $u failed (continuing: the tests report real failures)"; fi
done
cd "$ROOT/tests/team"
mkdir -p "$ROOT/reports"
exec npx playwright test "$@"
