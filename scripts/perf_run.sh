#!/usr/bin/env bash
# Performance protocol (project statement §5): 1 simulated user then 5, each setup run TWICE, same build/machine/starting data
# (DB reset + fresh server before every run). Raw k6 output and summaries go to reports/performance/. Usage: scripts/perf_run.sh
set -euo pipefail
. "$(dirname "$0")/env.sh"
OUT="${PERF_OUT:-$ROOT/reports/performance}"; mkdir -p "$OUT"
{ echo "date: $(date -Is)"; echo "commit: $(git -C "$ROOT" rev-parse HEAD)"; echo "kernel: $(uname -sr)"; echo "cpu: $(lscpu | awk -F: '/Model name/{gsub(/^ +/,"",$2);print $2}') x$(nproc)"; echo "memory: $(free -h | awk '/Mem:/{print $2}')"; echo "python: $($ROOT/.venv/bin/python --version)"; echo "k6: $(k6 version | head -1)"; echo "server: ${SERVER_MODE:-dev} (dev = Django runserver single process threaded; gunicorn = ${GUNICORN_WORKERS:-4} worker processes), SQLite, DEBUG=False"; echo "operation: POST /api/stock/remove/ quantity 1 (manager)"; } > "$OUT/environment.txt"
for VUS in 1 5; do
  for RUN in 1 2; do
    "$ROOT/scripts/stop.sh"; sleep 1; "$ROOT/scripts/reset.sh" >/dev/null; "$ROOT/scripts/start.sh" >/dev/null
    for u in /web/login /api/ /api/stock/; do
      if ! curl -s -o /dev/null -u admin:admin12345 "http://127.0.0.1:8000$u"; then echo "warm-up $u failed"; fi      # warm up lazy imports
    done
    echo "=== ${VUS} user(s), run ${RUN}"
    K6_EXIT=0
    VUS=$VUS k6 run --quiet --summary-export "$OUT/summary_${VUS}vu_run${RUN}.json" "$ROOT/tests/team/perf/remove_stock.js" > "$OUT/raw_${VUS}vu_run${RUN}.txt" 2>&1 || K6_EXIT=$?
    echo "k6 exit code ${K6_EXIT} (99 = a threshold was crossed, which is a RESULT, not a script error)" >> "$OUT/raw_${VUS}vu_run${RUN}.txt"
    if [ "$K6_EXIT" -ne 0 ] && [ "$K6_EXIT" -ne 99 ]; then echo "k6 failed unexpectedly (${K6_EXIT})"; exit 1; fi
    tail -n 25 "$OUT/raw_${VUS}vu_run${RUN}.txt" | awk '/http_req_duration\{phase:hold\}|http_req_failed\{phase:hold\}|http_reqs\{phase:hold\}|✓|✗/' | head -6
  done
done
echo PERF_DONE
