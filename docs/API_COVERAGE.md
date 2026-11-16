# API coverage criteria — computed by `tools/api_coverage.py` from the real run (1811 logged requests, 213 executed generated cases)

## C1 Endpoint and C2 operation coverage
| Operation | Requests |
|---|---|
| POST `/api/stock/add/` | 136 |
| POST `/api/stock/remove/` | 114 |
| GET `/api/stock/{id}/` | 477 |
| GET `/api/audit/` | 810 |

## C3 Documented status-code coverage
| Operation | Documented | Observed | Missing |
|---|---|---|---|
| POST `/api/stock/add/` | 201, 400, 401, 403, 405, 415, 500 | 201, 400, 401, 403, 415, 500 | 405 |
| POST `/api/stock/remove/` | 201, 400, 401, 403, 405, 415, 500 | 201, 400, 401, 403, 415, 500 | 405 |
| GET `/api/stock/{id}/` | 200, 404 | 200, 404, 500 | — (undocumented observed: 500) |
| GET `/api/audit/` | 200 | 200, 400 | — (undocumented observed: 400) |

Status classes observed: 2xx: 1636, 4xx: 162, 5xx: 13.

## C4 Role / authentication coverage
| Operation | admin | manager | viewer | anonymous |
|---|---|---|---|---|
| POST `/api/stock/add/` | — | ✔ | ✔ | ✔ |
| POST `/api/stock/remove/` | — | ✔ | ✔ | ✔ |
| GET `/api/stock/{id}/` | — | ✔ | ✔ | — |
| GET `/api/audit/` | — | ✔ | — | — |

## C5 Input-parameter coverage (EP and BVA cases executed per input)
| Operation | Input | Where | EP executed/generated | BVA executed/generated | mismatches vs contract |
|---|---|---|---|---|---|
| auditList | `event_type` | query | 4/4 | 0/0 | 1 |
| auditList | `limit` | query | 1/10 | 2/3 | 0 |
| auditList | `offset` | query | 10/10 | 3/3 | 10 |
| stockAdd | `items` | body | 4/4 | 3/3 | 3 |
| stockAdd | `items[].batch` | body | 7/7 | 3/3 | 0 |
| stockAdd | `items[].merge` | body | 8/8 | 0/0 | 2 |
| stockAdd | `items[].packaging` | body | 7/7 | 3/3 | 0 |
| stockAdd | `items[].pk` | body | 12/12 | 3/3 | 1 |
| stockAdd | `items[].quantity` | body | 13/13 | 6/6 | 1 |
| stockAdd | `items[].status` | body | 10/10 | 0/0 | 0 |
| stockAdd | `notes` | body | 7/7 | 3/3 | 0 |
| stockItemRead | `id` | path | 9/9 | 3/3 | 0 |
| stockRemove | `items` | body | 4/4 | 3/3 | 3 |
| stockRemove | `items[].batch` | body | 7/7 | 3/3 | 0 |
| stockRemove | `items[].merge` | body | 8/8 | 0/0 | 2 |
| stockRemove | `items[].packaging` | body | 7/7 | 3/3 | 0 |
| stockRemove | `items[].pk` | body | 12/12 | 3/3 | 1 |
| stockRemove | `items[].quantity` | body | 13/13 | 9/9 | 2 |
| stockRemove | `items[].status` | body | 10/10 | 0/0 | 0 |
| stockRemove | `notes` | body | 7/7 | 3/3 | 0 |

**C6:** 213/223 generated cases executed; 187 matched the contract, 26 mismatched (each mismatch is a documented baseline defect/weakness: DEF-01, DEF-02, DEF-04, W-08, W-09 — strict xfail).

## C7 Content-type coverage (write endpoints; JSON documented, text/plain = unsupported probe)
| Path | application/json | text/plain |
|---|---|---|
| `/api/stock/add/` | 134 | 2 |
| `/api/stock/remove/` | 112 | 2 |

## C8 Negative-method coverage (405)
| Path | GET | PUT | PATCH | DELETE |
|---|---|---|---|---|
| `/api/stock/add/` | 405 ✔ | 405 ✔ | 405 ✔ | 405 ✔ |
| `/api/stock/remove/` | 405 ✔ | 405 ✔ | 405 ✔ | 405 ✔ |

## C9 Response-schema validation
Every response whose status has a schema in the spec is validated against it inside the HTTP client (a violation fails the test): **1392** responses validated, 1394 had a schema in the spec.

## C10 Sequence / dependency coverage (tests tagged `@pytest.mark.seq`)
| Sequence | Result |
|---|---|
| S1-add-remove-add | passed |
| S2-deplete-restock | passed |
| S3-deplete-delete | passed |
| S4-delete-then-adjust | passed |
| S5-reject-retry | passed |
| S6-repeat-valid | passed |
| S7-atomic-multi | passed |

## Summary
| Criterion | Covered | Total | % |
|---|---|---|---|
| C1 endpoints exercised | 4 | 4 | 100 |
| C2 operations exercised | 4 | 4 | 100 |
| C3 documented status codes observed | 15 | 17 | 88 |
| C3b status classes 2xx/4xx/5xx observed | 3 | 3 | 100 |
| C4 required roles per operation (write: manager/viewer/anonymous; reads: manager) | 8 | 8 | 100 |
| C5 inputs with ALL generated EP and BVA cases executed | 19 | 20 | 95 |
| C6 parameter-value coverage: generated cases executed | 213 | 223 | 96 |
| C7 content types per write endpoint | 4 | 4 | 100 |
| C8 unsupported methods rejected with 405 | 8 | 8 | 100 |
| C9 responses with a spec schema that were validated | 1392 | 1394 | 100 |
| C10 operation sequences passing | 7 | 7 | 100 |
