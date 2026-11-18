# PERFORMANCE AND RECOVERY (Phase 10)

## 1. Operation and limits (declared BEFORE any measurement: `docs/PERF_TARGETS.md`, committed in `1354eb1`, earlier than every k6 run)
Operation: `POST /api/stock/remove/` (WF-B, state-changing), quantity 1 per request, user `manager`, one item with 5 000 000 in stock (so every request is valid). Measure: **p95** response time. Limits (same for 1 and 5 users): **p95 ≤ 500 ms** and **unexpected failures < 1 %** (any status other than 201 counts as unexpected). Rationale in PERF_TARGETS.md (interactive threshold; no relaxation under concurrency because 5 clerks at once is a normal small-warehouse peak and SQLite write locking, risk PR-08, is what we want to expose).

## 2. Method (`scripts/perf_run.sh`, `tests/team/perf/remove_stock.js`, Grafana k6 v2.3.0 OSS)
- 1 simulated user, then 5 simulated users; **each setup run twice** (4 runs). All N users start together; a 10 s warm-up phase is tagged `warmup`; the **60 s measured phase** (`phase=hold`) follows at the same user count — measurements are taken only after the workload has reached the chosen number of users and last 60 s per run.
- **Same build, machine and starting data for every run:** before each run the server is stopped, the DB is reset (`scripts/reset.sh`), the server restarted and warmed up, and a fresh item is created in k6 `setup()`.
- Environment: `reports/performance/environment.txt` (commit 66a9d10, Linux 7.0, 12th-gen Core i5-1235U ×12, 15 GB, Python 3.12.3, Django `runserver` single process threaded, SQLite, DEBUG False). Raw k6 output: `reports/performance/raw_*.txt`; summaries: `summary_*.json`.

## 3. Results (measured phase, 60 s each)
| Run | Requests (60 s hold) | Requests/s (= count ÷ 60 s) | avg ms | p90 ms | **p95 ms** | p99 ms | max ms | **Unexpected failures** |
|---|---|---|---|---|---|---|---|---|
| 1 user, run 1 | 207 | 3.45 | 289.6 | 295.3 | **298.8** | 320.8 | 331.1 | **0.00 %** |
| 1 user, run 2 | 208 | 3.47 | 289.3 | 295.2 | **297.6** | 312.5 | 318.6 | **0.00 %** |
| 5 users, run 1 | 658 | 10.97 | 458.1 | 502.7 | **517.7** | 565.5 | 737.8 | **19.30 %** |
| 5 users, run 2 | 656 | 10.93 | 457.7 | 509.9 | **521.8** | 548.2 | 595.8 | **19.66 %** |

## 4. Comparison with the declared limits
| Workload | p95 limit | Observed p95 | Failure limit | Observed failures | Verdict |
|---|---|---|---|---|---|
| 1 user | ≤ 500 ms | 298.8 / 297.6 ms | < 1 % | 0 % / 0 % | **met** (both runs) |
| 5 users | ≤ 500 ms | 517.7 / 521.8 ms | < 1 % | 19.3 % / 19.7 % | **NOT met** (both runs, both criteria) |
Run-to-run variation is small (1 user: 1.2 ms in p95; 5 users: 4.1 ms; failures 0.4 pt), so the verdict is stable. Throughput scales 3.2× from 1 to 5 users (3.45 → 10.95 req/s, count ÷ 60 s of the measured phase; k6 itself reports the rate over the whole 70 s test, which understates it by ~14 %) rather than 5×, and latency per request rises 58 % (290 → 458 ms avg).

## 5. Interpretation and root cause of the BASELINE failures (feeds RCA-2; the fix and its re-measurement are in §7)
- **What fails:** the failures are HTTP **500** `OperationalError`. Evidence preserved in `reports/performance/concurrency_probe.txt`: a separate 5-thread client (200 requests, same server and reset protocol) got **38 HTTP 500** and the server log holds **exactly 38 `database is locked` lines** (1:1). (The k6 run summaries do not break failures down by status; the attribution therefore rests on this probe plus the identical failure rate.) SQLite permits a single writer; concurrent adjustments of the same item queue on the write lock, and the busy timeout is exceeded (`select_for_update` is not a row lock on SQLite — assumption A-4).
- **What does not fail:** data integrity. In the probe the final quantity equals initial minus the number of 201 responses (99 838 = 100 000 − 162, `concurrency_probe.txt`). The loss is availability (client sees 500 and must retry), not correctness.
- **Baseline latency is already high:** ~290 ms for a single-row decrement with one user (`runserver`, history/audit write, SQLite fsync). The p95 margin to the 500 ms limit disappears at 5 users.
- Defect **DEF-06** (Issue #6, High/P2). Risk **PR-08** materialised (Medium → raised to High in the register). Recommended corrections: PostgreSQL in production (row locks; out of scope on this machine), a longer SQLite busy timeout plus a retriable `503`/`409` instead of `500`, gunicorn with several workers behind a proxy. These were **not** tested here and are stated as recommendations only.
- **Exit criterion EC-3 is not met on the baseline** (5 users: p95 and failure rate both over the limits) → the release recommendation (Phase 13) must be **HOLD** for the performance criterion unless the risk is accepted for single-user use.

## 6. Failure and recovery test (`tests/team/unit/test_recovery.py`)
State-changing operation: Remove stock through the real API view. **Test double:** the history writer (`StockItem.tracking_event`) is replaced by a double that becomes unavailable (a) before the write (`enter`) or (b) after the quantity was saved but before the transaction completes (`exit`).
| Step | Assertion | Result |
|---|---|---|
| 1 dependency unavailable | request answers HTTP 500 | passed (both variants) |
| 2 persisted state after the failure | quantity still 10, **0** history entries (atomic rollback; nothing half-written) | passed |
| 3 dependency restored, **same request retried** | HTTP 201 | passed |
| 4 final state | quantity 6 (removed exactly once), **exactly 1** history entry (no duplicates) | passed |
Raw output of the test run: `reports/performance/recovery_run.txt` (3 passed). A multi-item variant (`test_multi_item_request_failure_leaves_every_item_untouched_then_retry_applies_each_once`) shows all-or-nothing behaviour and a clean retry. Related risks: PR-05, PR-06, PR-07. **Weakness (W-03, API tests):** the API has no idempotency key, so a client retry *after a lost successful response* would apply twice — the recovery here is safe only because the failed attempt was rolled back.


## 7. Re-measurement after the DEF-06 fix (pull request #18)
**What was changed:** `InvenTree/setting/db_backend.py` — SQLite connections of the web server now use `IMMEDIATE` transactions (the code used `DEFERRED` for web requests) and a 30 s busy timeout (was 10 s). A request therefore takes the write lock when its transaction begins and waits for it instead of failing at the lock upgrade with `database is locked` (HTTP 500). The protocol is unchanged (`scripts/perf_run.sh`: DB reset and server restart before each run, 10 s warm-up, 60 s measured, 2 runs per setup). The baseline files were kept in `reports/performance/baseline/`.

**Method note on the authentication variant.** The original k6 script sends HTTP Basic credentials with **every** request, so the server verifies the password hash on each one — extra server work that a client with a session or API token does not cause. The script now has `AUTH=token` (token fetched once in `setup()`); `AUTH=basic` is the original behaviour. Both are reported; the token variant is used for EC-3 because it is how a client works after logging in. A third variant runs the project's production-style WSGI server (`gunicorn` with 4 workers, `SERVER_MODE=gunicorn`) to test whether the single-process dev server is the limit.

| Set | Run | Requests (60 s hold) | Requests/s | median ms | **p95 ms** | **Failures** |
|---|---|---|---|---|---|---|
| baseline (before the fix), Basic auth on every request, dev server | 1 user, run 1 | 207 | 3.5 | 288 | **299** | **0.00 %** |
| baseline (before the fix), Basic auth on every request, dev server | 1 user, run 2 | 208 | 3.5 | 289 | **298** | **0.00 %** |
| baseline (before the fix), Basic auth on every request, dev server | 5 users, run 1 | 658 | 11.0 | 452 | **518** | **19.30 %** |
| baseline (before the fix), Basic auth on every request, dev server | 5 users, run 2 | 656 | 10.9 | 449 | **522** | **19.66 %** |
| after the DEF-06 fix, Basic auth on every request (same script as the baseline), dev server | 1 user, run 1 | 206 | 3.4 | 291 | **298** | **0.00 %** |
| after the DEF-06 fix, Basic auth on every request (same script as the baseline), dev server | 1 user, run 2 | 203 | 3.4 | 291 | **302** | **0.00 %** |
| after the DEF-06 fix, Basic auth on every request (same script as the baseline), dev server | 5 users, run 1 | 583 | 9.7 | 515 | **589** | **0.00 %** |
| after the DEF-06 fix, Basic auth on every request (same script as the baseline), dev server | 5 users, run 2 | 583 | 9.7 | 512 | **594** | **0.00 %** |
| after the fix, **API token** auth (client logs in once), dev server — **the EC-3 measurement** | 1 user, run 1 | 207 | 3.5 | 290 | **301** | **0.00 %** |
| after the fix, **API token** auth (client logs in once), dev server — **the EC-3 measurement** | 1 user, run 2 | 206 | 3.4 | 290 | **308** | **0.00 %** |
| after the fix, **API token** auth (client logs in once), dev server — **the EC-3 measurement** | 5 users, run 1 | 628 | 10.5 | 477 | **556** | **0.00 %** |
| after the fix, **API token** auth (client logs in once), dev server — **the EC-3 measurement** | 5 users, run 2 | 635 | 10.6 | 469 | **545** | **0.00 %** |
| after the fix, Basic auth, **gunicorn with 4 worker processes** | 1 user, run 1 | 144 | 2.4 | 412 | **443** | **0.00 %** |
| after the fix, Basic auth, **gunicorn with 4 worker processes** | 1 user, run 2 | 250 | 4.2 | 240 | **248** | **0.00 %** |
| after the fix, Basic auth, **gunicorn with 4 worker processes** | 5 users, run 1 | 584 | 9.7 | 506 | **681** | **0.00 %** |
| after the fix, Basic auth, **gunicorn with 4 worker processes** | 5 users, run 2 | 583 | 9.7 | 506 | **687** | **0.00 %** |


**Reading:**
- **DEF-06 is fixed:** unexpected failures at 5 users fell from 19.3 % / 19.7 % to **0 %** in every re-measurement (basic, token, gunicorn); data integrity was never affected.
- **p95 rose from 518–522 ms to 545–594 ms at 5 users** although the failures vanished: before the fix about one request in five failed quickly with an error, which pulled the percentile down; now every request succeeds and waits for the single SQLite writer. Median latency is 470–515 ms.
- **Token vs Basic authentication:** token authentication saves about 40 ms at 5 users (p95 545–556 ms instead of 589–594 ms).
- **gunicorn with 4 workers does not help (681–687 ms):** the writers are serialised by SQLite, so more processes only add contention. The limit is the single-writer design plus about 100 ms of server work per adjustment (authentication, permission check, row lock, audit entry, event handling).
- **EC-3 verdict:** failure criterion **met** (0 % < 1 %), p95 criterion **not met** at 5 users (545–556 ms vs the declared 500 ms; 9–11 % over). 1 user: 301 / 308 ms (met). The target was declared before any measurement (`docs/PERF_TARGETS.md`) and was **not** adjusted. To meet it, either reduce the per-request work of the add/remove endpoint or run on a database with row-level locking (PostgreSQL, out of reach on this machine); neither is a small change.
- **Residual risk PR-08:** likelihood reduced (no failures), impact unchanged (slow, no data loss) → Medium (3×3).
