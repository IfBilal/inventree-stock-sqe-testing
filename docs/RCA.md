# ROOT-CAUSE ANALYSIS (two major defects) — 5 Whys + fishbone, corrective and preventive actions
Statements are marked **[verified]** (read in source / observed in a run) or **[hypothesis]** (not verifiable from the code; stated so the viva answer is honest).

---
## RCA-1 — DEF-01 (Issue #1, Critical, risk PR-01): removing more than the available quantity succeeds and silently discards the excess
**Problem statement.** `POST /api/stock/remove/ {pk, quantity: 100}` on an item holding 10 returns **201**, the item ends at 0 (or is deleted when `delete_on_deplete`), and the history entry records `removed: 10`. Evidence: `evidence/phase1/over_removal.txt`; unit/API/E2E tests.

### 5 Whys
| # | Why? | Answer |
|---|---|---|
| 1 | Why did the over-removal succeed? | `StockItem.take_stock` clamps the amount: `quantity = min(quantity, self.quantity)` (`stock/models.py` ~L3477) instead of refusing. **[verified]** |
| 2 | Why does the model clamp instead of fail? | The source comment says the clamp "ensures the recorded history matches the actual removal" after the row lock refreshed the quantity — a defensive choice for stale in-memory values and concurrent adjustments. **[verified]** |
| 3 | Why did nothing reject the request before reaching the model? | The serializer layer validates only type, range (`min_value=0`), precision and adjustability; it has **no stock-dependent rule** (`quantity ≤ available`) for removal (`StockAdjustmentItemSerializer`, `StockRemoveSerializer`). **[verified]** |
| 4 | Why is that rule missing? | The feature documentation states only that stock is "decreased by the given amount" (`docs/docs/stock/adjust.md`); the limit was never written down as a requirement, so no layer owns it. **[verified: doc text]**; the intent of the original authors is a **[hypothesis]** |
| 5 | Why was the gap not caught by review/tests? | The clamp turns an invalid input into a *successful* response, so happy-path tests and a status-code check pass; a boundary test just above the limit (3-point BVA) is what exposes it. Whether upstream tests assert the clamp is **[not verified]**. |
**Root cause:** a missing business requirement (removal limit) combined with a defensive silent clamp in the model that converts invalid input into success. (Category: requirements gap + design.)

### Fishbone (Ishikawa)
| Category | Contributing factors |
|---|---|
| Requirements | limit "removal ≤ available" not stated; docs minimal |
| Design | validation split between serializer and model; model-level silent clamp; no explicit error path |
| Code | `StockRemoveSerializer` lacks a state-dependent validation; `min()` hides the violation |
| Test | boundary just above the limit not tested; success-path assertions only (**[hypothesis]** for upstream) |
| Process / review | silent clamp not flagged as a risk in review; no data-loss threat analysis |
| Environment/data | none (reproducible on every item) |

### Corrective actions
1. **Fix** (pull request on branch `fix/def-01-over-removal`): `StockRemoveSerializer.validate` rejects a removal larger than the available quantity (entries for the same item are summed), message names the available quantity; our strict-xfail tests become normal tests (the PR first shows the failing pipeline, then the passing one — `docs/CI_QUALITY_GATE.md`).
2. Re-run unit, API (generated BVA `limit-above`), E2E (UC02-EF1, UC03-EF2, UC06-AF1) after the fix.
### Preventive actions
1. Record the rule as BR-1/FR-07 in the test basis and in the OpenAPI contract (`x-quantity-limit-from`), so the generator always produces the limit BVA (done).
2. Keep the 3-point limit BVA at three levels and a **custom mutation operator `LIMIT_CLAMP`** (`min`↔`max`) in CI (done).
3. Review checklist item: "a defensive clamp/default must not turn invalid input into success".
4. Decision-table/MCC of `take_stock` guards (done, `docs/MCC_MCDC.md`).

---
## RCA-2 — DEF-06 (Issue #6, High, risk PR-08): ~20 % of concurrent adjustments fail with HTTP 500
**Problem statement.** With 5 simulated users the remove operation returns HTTP 500 for 19.3 % / 19.7 % of requests (two k6 runs); p95 518/522 ms against a 500 ms limit. Data stays consistent (final quantity = initial − successes, `concurrency_probe.txt`). Evidence: `docs/PERFORMANCE.md`, `reports/performance/`.

### 5 Whys
| # | Why? | Answer |
|---|---|---|
| 1 | Why do requests fail? | The server raises `django.db.utils.OperationalError: database is locked` — in the probe 38 HTTP 500 correspond to exactly 38 log lines (`reports/performance/concurrency_probe.txt`). **[verified]** |
| 2 | Why is the database locked? | SQLite allows a single writer; concurrent adjustments of one item queue on the write lock and exceed the busy timeout. **[verified symptom; mechanism is standard SQLite behaviour]** |
| 3 | Why do writers hold the lock long enough to collide? | Each remove performs the quantity update **and** audit/history writes in one transaction; a single request takes ≈ 290 ms with one user (`reports/performance/summary_1vu_*.json`). **[verified timing; breakdown by step is a hypothesis]** |
| 4 | Why is the failure surfaced as a 500 rather than handled? | The lock error is not caught/retried; the generic exception handler returns the exception class as an HTTP 500 body (`InvenTree.exceptions.exception_handler`); `select_for_update` gives no row lock on SQLite. **[verified]** |
| 5 | Why was this not designed out? | No non-functional requirement for concurrency existed in the documentation, and the default/dev backend is SQLite (assumption A-4); load behaviour was not tested. **[hypothesis for the process; the backend choice is verified]** |
**Root cause:** SQLite single-writer locking combined with a long write transaction and no retry/error mapping, with no declared concurrency requirement. (Category: environment/design + requirements gap.)

### Fishbone (Ishikawa)
| Category | Contributing factors |
|---|---|
| Environment | SQLite backend; Django `runserver` (single process); busy timeout default |
| Design | long transaction (quantity + audit entries + events); no idempotency/retry; error mapped to 500 |
| Code | `OperationalError` not caught; no 503/409 contract for transient failures |
| Requirements | no concurrency NFR or response-time target stated |
| Test | no load/concurrency test in the project; first measured in Phase 10 |
| Process | performance risk (PR-08) was scored Medium; evidence now raises it to High |

### Corrective actions
1. Production configuration: **PostgreSQL** (row-level locking) and several gunicorn workers (not tested here — recommendation).
2. Return a retriable **503/409** for lock timeouts and add bounded retry with back-off in the adjustment path.
3. Shorten the write transaction (move non-essential event work after commit).
### Preventive actions
1. Performance targets declared before measuring (`docs/PERF_TARGETS.md`, done) and a k6 smoke run (1 vs 5 users) as a release check (`scripts/perf_run.sh`).
2. Add the concurrency requirement to the test basis; keep PR-08 at High until the production database is tested.
3. Recovery test (`tests/team/unit/test_recovery.py`) already proves a failed attempt leaves no partial state, so a client retry is safe.

### Implementation status of RCA-2 (update after pull request #18)
| Action | Status | Evidence |
|---|---|---|
| Corrective 1 — PostgreSQL / several workers | **Partly tested, not adopted:** gunicorn with 4 workers was measured on SQLite and does not help (p95 681–687 ms: writers are serialised); PostgreSQL is not available on this machine | `docs/PERFORMANCE.md` §7 |
| **New corrective action (implemented)** — take the SQLite write lock at the start of the transaction (`IMMEDIATE`) and wait up to 30 s | **Done** (PR #18): unexpected failures at 5 users 19.3/19.7 % → 0 % in all re-measurements | `reports/performance/`, `tests/team/unit/test_security_headers.py::test_sqlite_uses_immediate_transactions_with_a_busy_timeout` |
| Corrective 2 — 503/409 with retry | not needed after the fix (no lock errors observed); remains a recommendation for PostgreSQL deployments | — |
| Corrective 3 — shorten the write transaction | open (would address the remaining p95 gap, EC-3) | — |
| Preventive 1 — performance targets declared first, k6 release check | **Done and used** (the re-measurement followed the same protocol) | `scripts/perf_run.sh` |
| Preventive 2 — keep PR-08 elevated until the production database is tested | PR-08 re-assessed to Medium (failures gone, latency gap remains) | `docs/RISK_REGISTER.md` |
| Preventive 3 — recovery test | **Done** | `tests/team/unit/test_recovery.py` |
