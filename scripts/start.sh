#!/usr/bin/env bash
# Start the server (background) and wait until /api/ answers.
set -euo pipefail
. "$(dirname "$0")/env.sh"
mkdir -p "$ROOT/data"
if [ "${SERVER_MODE:-dev}" = "gunicorn" ]; then
  # production-style WSGI server (the project ships gunicorn.conf.py); worker processes run Python in parallel
  ( cd "$ROOT/upstream/src/backend/InvenTree" && nohup "$PY" -m gunicorn InvenTree.wsgi -c gunicorn.conf.py --bind 127.0.0.1:8000 --workers "${GUNICORN_WORKERS:-4}" --timeout 120 > "$ROOT/data/server.log" 2>&1 & )
else
  nohup $MANAGE runserver 127.0.0.1:8000 --noreload > "$ROOT/data/server.log" 2>&1 &
fi
for i in $(seq 1 60); do curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/ | grep -q 200 && { echo "SERVER_UP"; exit 0; }; sleep 2; done
echo "SERVER_FAILED"; exit 1
