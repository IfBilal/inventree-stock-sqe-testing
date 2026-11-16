#!/usr/bin/env bash
# One-time install from a fresh clone: venv, backend deps, DB, static, frontend, seed. Needs python3.12, node>=20, yarn(or npx).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/pip install -q -r upstream/src/backend/requirements.txt
.venv/bin/pip install -q -r tests/team/requirements.txt
scripts/build_frontend.sh
. scripts/env.sh
mkdir -p data/media data/static data/backup; touch data/plugins.txt
scripts/reset.sh
$MANAGE collectstatic --noinput >/dev/null 2>&1
(cd tests/team && npm ci && npx playwright install chromium)
echo "INSTALL_OK"
