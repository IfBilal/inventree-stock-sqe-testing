# API coverage criteria — computed by `tools/api_coverage.py` from `evidence/api/request_log.jsonl` (968 logged requests)

## C1 Endpoint coverage
| Endpoint | Requests |
|---|---|
| `/api/stock/add/` | 79 |
| `/api/stock/remove/` | 74 |
| `/api/stock/{id}/` | 232 |
| `/api/audit/` | 444 |

## C2 Operation (method + path) and C3 documented status-code coverage
| Operation | Documented status codes | Observed | Missing |
|---|---|---|---|
| POST `/api/stock/add/` | 201, 400, 401, 403 | 201, 400, 401, 403, 415, 500 | — |
| POST `/api/stock/remove/` | 201, 400, 401, 403 | 201, 400, 401, 403, 415, 500 | — |
| GET `/api/stock/{id}/` | 200, 404 | 200, 404 | — |
| GET `/api/audit/` | 200 | 200 | — |

## C4 Role / authentication coverage (POST add/remove)
| Operation | admin | manager | viewer | anonymous |
|---|---|---|---|---|
| POST `/api/stock/add/` | — | ✔ | ✔ | ✔ |
| POST `/api/stock/remove/` | — | ✔ | ✔ | ✔ |

## C5 Input-parameter coverage (every input of every request body, EP and 3-point BVA cases executed)
| Operation | Input | EP cases | BVA cases |
|---|---|---|---|
| stockAdd | `items` | 3 | 3 |
| stockAdd | `items[].batch` | 3 | 3 |
| stockAdd | `items[].merge` | 3 | 0 |
| stockAdd | `items[].packaging` | 3 | 3 |
| stockAdd | `items[].pk` | 8 | 1 |
| stockAdd | `items[].quantity` | 8 | 6 |
| stockAdd | `notes` | 3 | 3 |
| stockRemove | `items` | 3 | 3 |
| stockRemove | `items[].batch` | 3 | 3 |
| stockRemove | `items[].merge` | 3 | 0 |
| stockRemove | `items[].packaging` | 3 | 3 |
| stockRemove | `items[].pk` | 8 | 1 |
| stockRemove | `items[].quantity` | 8 | 9 |
| stockRemove | `notes` | 3 | 3 |

All 103 generated cases are executed by `tests/team/api/test_generated_ep_bva.py` (one test per case).

## C6 Content-type coverage (POST)
| Path | Content-Type | Requests |
|---|---|---|
| `/api/part/` | application/json | 1 |
| `/api/stock/` | application/json | 138 |
| `/api/stock/add/` | application/json | 74 |
| `/api/stock/add/` | text/plain | 1 |
| `/api/stock/remove/` | application/json | 69 |
| `/api/stock/remove/` | text/plain | 1 |

## C7 Negative-method coverage (405)
| Path | GET | PUT | PATCH | DELETE |
|---|---|---|---|---|
| `/api/stock/add/` | 405 ✔ | 405 ✔ | 405 ✔ | 405 ✔ |
| `/api/stock/remove/` | 405 ✔ | 405 ✔ | 405 ✔ | 405 ✔ |

## C8 Sequence / state coverage
Covered by `test_business_rules_api.py`: add→remove→add with ordered history (cross-workflow), depletion (retained and deleted), restock of depleted, repeated valid and rejected requests, atomic multi-item request, read-back of `StockItem.quantity` and history after **success and rejection** in every test.

## Summary
| Criterion | Covered | Total | % |
|---|---|---|---|
| C1 endpoints exercised | 4 | 4 | 100 |
| C3 documented status codes observed | 11 | 11 | 100 |
| C2 operations exercised | 4 | 4 | 100 |
| C4 roles (manager/viewer/anonymous) per write endpoint | 6 | 6 | 100 |
| C5 inputs with >= 1 executed EP case (generated) | 14 | 14 | 100 |
| C6 content types per write endpoint (JSON + unsupported) | 4 | 4 | 100 |
| C7 unsupported methods rejected with 405 | 8 | 8 | 100 |
