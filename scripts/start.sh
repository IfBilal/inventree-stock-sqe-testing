#!/usr/bin/env bash
# Start the server (background) and wait until /api/ answers.
set -euo pipefail
. "$(dirname "$0")/env.sh"
mkdir -p "$ROOT/data"
nohup $MANAGE runserver 127.0.0.1:8000 --noreload > "$ROOT/data/server.log" 2>&1 &
for i in $(seq 1 60); do curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/ | grep -q 200 && { echo "SERVER_UP"; exit 0; }; sleep 2; done
echo "SERVER_FAILED"; exit 1
