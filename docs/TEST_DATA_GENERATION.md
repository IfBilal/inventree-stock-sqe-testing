# AUTOMATED TEST-DATA GENERATION (Phase 5)
**Spec:** `openapi/stock.yaml` (OpenAPI 3.0.3 contract of the two workflows + read-backs). We wrote our own because InvenTree's generated schema (`/api/schema/`, v580) is inaccurate for testing: it allows negative quantities (regex `^-?\d{0,10}…`), has no numeric minimum/maximum, no `minItems` on `items` even though the server rejects an empty list, and documents only status 201.
**Generator:** `tools/gen_testdata.py` — reads the spec and emits, for **every input of every operation with a request body**, equivalence-partition classes (EP) and 3-point boundary values (BVA), with the expected outcome, as complete request bodies. Exact decimals (no float rounding), deterministic output, 223 cases for the current spec (`evidence/generator/testdata_before.json`).
Run: `.venv/bin/python tools/gen_testdata.py openapi/stock.yaml -o evidence/generator/testdata_before.json`.

## Constraints handled and cases produced
| Constraint (spec) | EP classes | 3-point BVA |
|---|---|---|
| `type: number`, `exclusiveMinimum: true`, `minimum: 0`, `maximum: 9999999999.99999`, `multipleOf: 0.00001` | valid-typical, not-a-number, null, empty-string, too-many-decimals, below-range, above-range, missing-required | min-below (−0.00001) invalid, min-at (0) invalid (exclusive), min-above (0.00001) valid; max-below (…99998) valid, max-at (…99999) valid, max-above (10000000000.00000) invalid |
| `x-quantity-limit-from: StockItem.quantity` (remove only, BR-1) | — | limit-below / limit-at (valid), limit-above (invalid), expressed relative to the item's available quantity (`{"$available": "±0.00001"}`) |
| `type: integer`, `minimum: 1`, `x-reference: StockItem` (`pk`) | valid-typical (`$ITEM`), not-a-number, fractional, null, empty-string, unknown-reference, negative, missing-required | below-minimum (0) |
| `type: string`, `maxLength` (`notes` 512, `batch` 100, `packaging` 50) | valid-typical, empty-string, wrong-type | maxlen-below / maxlen-at (valid), maxlen-above (invalid) |
| `type: array`, `minItems: 1` (`items`) | not-an-array, null, missing-required | minitems-below (0 items, invalid), minitems-at (1), minitems-above (2) |
| `type: boolean` (`merge`) | true, false, not-a-boolean | — |
Each case = a **valid template body with exactly one mutation**, so a rejection is attributable to that input ("one invalid value per test").

## API tests must use the generator output
`tests/team/api/test_generated_ep_bva.py` imports `gen_testdata.generate()` and parametrises **all 223 cases** (one test per case id, e.g. `stockAdd:items[].quantity:BVA:max-at`). No boundary value is hard-coded in that file; the initial state of the item is derived from the case (limit cases use quantity 10, remove cases use the maximum, add-near-max uses an empty item so the result stays representable).

## Constraint change demo (required by the project statement)
`scripts/gen_demo.sh` changes **two constraints** in a copy of the spec — `quantity.maximum` 9999999999.99999 → **1000** and `notes.maxLength` 512 → **100** — regenerates, and diffs (`evidence/generator/spec_changes1.txt`, `testdata_after1.json`, `effect1.md`) — **demo 1**:
- **16 of 223 cases changed**, and only those derived from the two constraints (quantity `max-below/at/above` and `above-range` for add and remove = 8; notes `maxlen-below/at/above` for add and remove = 8, incl. the `above-range` neighbours).
- **Demo 2** (`effect2.md`): `quantity.exclusiveMinimum` true → false and `items.minItems` 1 → 2 → **8 cases changed** (the zero-quantity boundary becomes valid; the one-item list becomes invalid).
- Example: `stockAdd:items[].quantity:BVA:max-at` `9999999999.99999 → valid` becomes `1000 → valid`; `notes maxlen-at` 512 chars → 100 chars.
Expect to regenerate and update the spec live in the viva (`scripts/gen_demo.sh`, then `scripts/test_api.sh api/test_generated_ep_bva.py`).

## Generator quality
15 unit tests (`tests/team/generator/test_gen_testdata.py`): exact decimals, 3-point BVA for exclusive minimum and maximum, inclusive minimum, string length BVA, EP classes, required/optional handling, one-mutation-per-case, determinism, remove-only limit BVA, reference-field classes, skipped read-only operations, constraint change changes output, CLI. One defect was found and fixed by these tests (integer YAML bounds emitted as numbers instead of decimal strings).
