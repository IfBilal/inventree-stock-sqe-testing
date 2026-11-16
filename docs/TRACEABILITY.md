# TRACEABILITY MATRIX (skeleton — Phase 2; filled automatically in Phase 13 from `@pytest.mark.req` / E2E tags)
Requirements coverage = requirements with ≥ 1 **passing** test ÷ 16. **Current: 0 / 16 (0 %)** — updated at every phase gate.
| Req | Workflow | Description (short) | Source | Risk | Planned technique / level | Test IDs | Status | Covered |
|---|---|---|---|---|---|---|---|---|
| FR-01 | A | add N → quantity +N | DOC+CODE | PR-01 | EP/BVA; unit, API, E2E (UC01) | TBD | planned | N |
| FR-02 | A | add records history | CODE | PR-07 | read-back; unit, API, E2E | TBD | planned | N |
| FR-03a | A | negative/non-numeric/over-precision rejected | CODE | PR-04 | EP + 3-pt BVA; API (generated), unit | TBD | planned | N |
| FR-03b | A | zero rejected (assumption A-2, DEF-02) | ASSUMPTION | PR-04 | BVA; API, E2E (UC01-EF1) | TBD | planned | N |
| FR-04 | A | non-adjustable item rejected | CODE | PR-03 | decision table, MCC/MC/DC; unit, API | TBD | planned | N |
| FR-05 | B | remove N ≤ available → −N | DOC+CODE | PR-01 | EP/BVA; unit, API, E2E (UC02) | TBD | planned | N |
| FR-06 | B | remove records history | CODE | PR-07 | read-back; unit, API, E2E | TBD | planned | N |
| FR-07 | B | remove > available rejected (A-1, DEF-01) | ASSUMPTION | PR-01 | 3-pt BVA, state transition; unit, API, E2E (UC02-EF1) | TBD | planned | N |
| FR-08 | B | removing all depletes the item | CODE | PR-01 | state transition; unit, API, E2E (UC03) | TBD | planned | N |
| FR-09 | A,B | role without add right → 403 | CODE | PR-02 | access matrix; API, E2E (UC05) | TBD | planned | N |
| FR-10 | A,B | multi-item request atomic | CODE | PR-05 | API with mixed items + read-back | TBD | planned | N |
| FR-11 | A,B | serialized item unchanged | CODE | PR-05 | EP; unit, API | TBD | planned | N |
| BR-1 | A,B | boundary: 0 < N ≤ limit / ≤ available / result representable | CODE+A-1 | PR-01, PR-04 | 3-pt BVA; unit, API, mutation | TBD | planned | N |
| BR-2 | A,B | adjustability decision (5 conditions) | CODE | PR-03 | complete MCC + MC/DC; unit | TBD | planned | N |
| BR-3 | B/A | state change: deplete / restock | CODE | PR-01 | state transition; unit, API, E2E (UC03, UC04) | TBD | planned | N |
| BR-4 | A,B | role permission | CODE | PR-02 | access matrix; API, E2E | TBD | planned | N |
