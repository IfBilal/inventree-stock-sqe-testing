# Performance targets (declared BEFORE any load measurement — committed to Git before the k6 runs; see commit history)

**Operation chosen:** `POST /api/stock/remove/` (WF-B, state-changing) on one item, quantity 1 per request, by user `manager`.
**Measure:** p95 response time (95 of every 100 measured requests complete within the limit).
| Workload | p95 limit | Unexpected-failure limit | Why |
|---|---|---|---|
| 1 simulated user | ≤ 500 ms | < 1 % of requests | A user-facing stock correction should feel immediate; 500 ms is the usual interactive threshold and is the example used by the project statement. A single user has no contention, so the limit should be comfortable. |
| 5 simulated users | ≤ 500 ms | < 1 % of requests | We do not relax the limit under concurrency: five clerks adjusting stock at once is a normal peak for a small warehouse, and SQLite write locking (risk PR-08) is exactly what we want to expose. |
"Unexpected failure" = HTTP status other than 201, or a network error. Expected rejections (400/403) are not part of this workload (only valid requests are sent, with enough stock: the item is seeded with a large quantity before each run).
Run protocol: same build, machine and starting data (`scripts/reset.sh`); ≥ 60 s per run after the target number of users is reached; each setup run twice. Results and comparison with these limits: `reports/performance/`.

**Provenance note:** this file was committed (`1354eb1`, 2026-11-16 18:32) **before** the k6 script and `scripts/perf_run.sh` existed; the script, the runs and the results were committed afterwards (`2288f6e`). The numbers 500 ms and 1 % were fixed first and were not adjusted after seeing results. *Why they suit this operation:* a stock clerk adjusting quantities scans an item, enters a number and confirms; each correction is part of a loop of many items, so a sub-second response keeps the loop from feeling blocked, and a 1 % failure budget (about one failed correction per 100) is the most a clerk would tolerate before re-checking every entry. The 1-user baseline was unknown when the limit was set (it turned out to be ≈ 300 ms, leaving a 1.7× margin).
