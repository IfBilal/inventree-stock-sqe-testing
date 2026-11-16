#!/usr/bin/env bash
# "Change two constraints, regenerate and show the effect" (project statement). Two demos:
#  demo 1: quantity.maximum 9999999999.99999 -> 1000 and notes.maxLength 512 -> 100  (+ re-run of the API tests against the changed spec: needs the server, see scripts/test_api.sh)
#  demo 2: quantity exclusiveMinimum true -> false and items.minItems 1 -> 2
# Usage: scripts/gen_demo.sh [--with-api]   (--with-api re-runs the generated API tests against the changed spec of demo 1)
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; OUT=evidence/generator; mkdir -p $OUT
S=components.schemas
$PY tools/gen_testdata.py openapi/stock.yaml -o $OUT/testdata_before.json
# ---- demo 1
$PY tools/spec_mutate.py openapi/stock.yaml $OUT/stock_changed1.yaml $S.StockAdjustmentItem.properties.quantity.maximum=1000 $S.StockAdjustment.properties.notes.maxLength=100 | tee $OUT/spec_changes1.txt
$PY tools/gen_testdata.py $OUT/stock_changed1.yaml -o $OUT/testdata_after1.json
$PY tools/gen_diff.py $OUT/testdata_before.json $OUT/testdata_after1.json > $OUT/effect1.md
# ---- demo 2
$PY tools/spec_mutate.py openapi/stock.yaml $OUT/stock_changed2.yaml $S.StockAdjustmentItem.properties.quantity.exclusiveMinimum=false $S.StockAdjustment.properties.items.minItems=2 | tee $OUT/spec_changes2.txt
$PY tools/gen_testdata.py $OUT/stock_changed2.yaml -o $OUT/testdata_after2.json
$PY tools/gen_diff.py $OUT/testdata_before.json $OUT/testdata_after2.json > $OUT/effect2.md
tail -3 $OUT/effect1.md; tail -3 $OUT/effect2.md
if [ "${1:-}" = "--with-api" ]; then
  . scripts/env.sh
  API_SPEC="$ROOT/$OUT/stock_changed1.yaml" scripts/test_api.sh api/test_generated_ep_bva.py -q -p no:randomly 2>&1 | tail -25 | tee $OUT/effect1_api_run.txt
fi
