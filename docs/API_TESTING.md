# API AND INTEGRATION TESTING (Phase 6)
Run: `scripts/test_api.sh api` (resets the DB, starts the server, runs pytest + requests against `http://127.0.0.1:8000`). Every test creates its own item (order-independent). Evidence: `evidence/api/request_log.jsonl` (all requests), `docs/API_COVERAGE.md`, `docs/TRACEABILITY.md`.
**Result (2026-11-16):** 136 passed, 8 strict xfail (each = a baseline defect, see below), 0 failed.

## What is tested
| File | Content |
|---|---|
| `test_generated_ep_bva.py` | 103 generated EP/BVA cases on every input of `POST /api/stock/add/` and `/remove/` (see `docs/TEST_DATA_GENERATION.md`); success → read-back of quantity and history; rejection → quantity and history unchanged |
| `test_business_rules_api.py` | BR-4 role matrix (manager/viewer/anonymous × add/remove, read-back), BR-2 installed item, BR-3 depletion (retained/deleted), restock, remove from depleted (rejected after the DEF-01 fix), cross-workflow sequence with ordered history, repeated valid/rejected requests (no duplicates), atomic multi-item, duplicate pk, serialized item |
| `test_endpoint_weaknesses.py` | method/content-type/auth probes and the weaknesses below |
## API coverage criteria (measured, `docs/API_COVERAGE.md`)
Endpoint 4/4, operation 4/4, documented status codes 11/11 (201, 400, 401, 403, 200, 404), roles per write endpoint 6/6, inputs with EP cases 14/14, content types 4/4, unsupported methods 8/8 (405), plus sequence/state coverage. All figures are computed from the logged requests.

## Defects exposed (strict xfail, GitHub Issues in this repository)
| Defect | Cases | Issue |
|---|---|---|
| DEF-01 over-removal clamped, not rejected | `stockRemove:…quantity:BVA:limit-above`; `test_duplicate_pk_entries_exceeding_available_are_rejected` | #1 |
| DEF-02 zero accepted as silent no-op | `…quantity:BVA:min-at` (add, remove) | #2 |
| DEF-03 resulting quantity overflow → 500 on read | unit tests (`test_add_with_total_just_above_max_is_rejected`) — not an API case because it corrupts the shared test data | #3 |
| DEF-04 `items` null / string → HTTP 500 | `stockAdd|stockRemove:items:EP:null|not-an-array` (found by the generator on its first run) | #4 |

## Endpoint weaknesses (observed behaviour, each asserted by a test)
| ID | Weakness | Risk | Recommended fix |
|---|---|---|---|
| W-01 | The 201 response only echoes the request; the new balance is not returned (client needs a second GET) | PR-07 | return the resulting quantity per item |
| W-02 | Unknown top-level fields (e.g. typo `note`) are silently accepted | PR-04 | reject unknown fields |
| W-03 | No idempotency key: a client retry after a lost response is applied twice | PR-06 | accept `Idempotency-Key` |
| W-04 | `pk` given as a numeric string is accepted (loose typing) | — | strict typing (low) |
| W-05 | 500 responses expose the Python exception class (`"error":"TypeError"`) | PR-10 | generic error body (see DEF-04) |
| W-06 | The audit endpoint silently ignores the `object_pk` filter and returns every item's history | PR-07 | support or reject the filter |
| W-07 | Add/remove on a serialized item or on a depleted item returns 201 although nothing changed | PR-05 | return 400/200 with a message |
