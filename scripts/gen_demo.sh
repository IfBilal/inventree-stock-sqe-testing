#!/usr/bin/env bash
# Change two constraints in the OpenAPI spec, regenerate, and show the effect (project statement: "Change two constraints, regenerate and show the effect").
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; OUT=evidence/generator
$PY tools/gen_testdata.py openapi/stock.yaml -o $OUT/testdata_before.json
# Constraint 1: quantity.maximum 9999999999.99999 -> 1000 ; Constraint 2: notes.maxLength 512 -> 100
sed -e 's/maximum: 9999999999.99999/maximum: 1000/' -e '/^        notes:/,/maxLength/ s/maxLength: 512/maxLength: 100/' openapi/stock.yaml > $OUT/stock_changed.yaml
diff -u openapi/stock.yaml $OUT/stock_changed.yaml > $OUT/spec_changes.diff || true
$PY tools/gen_testdata.py $OUT/stock_changed.yaml -o $OUT/testdata_after.json
$PY tools/gen_diff.py $OUT/testdata_before.json $OUT/testdata_after.json > $OUT/effect.md
cat $OUT/spec_changes.diff | grep '^[+-] ' ; cat $OUT/effect.md
