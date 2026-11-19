# WEEKLY PROGRESS REPORT 2 of 2 — corrective actions and closure (2026-11-16 22:17 … 2026-11-18) against the plan (`docs/TEST_PLAN.md` v0.3)

Continues `reports/weekly/week-1.md` (checkpoint 2026-11-16 21:48). Same note: the two reports are the two checkpoints of the real commit timeline.

## 1. Progress against the plan
| Planned item (from report 1 §5) | Actual (commit/PR time) | Status | Control action |
|---|---|---|---|
| Fix DEF-01 with a red → green pipeline | PR #13: tests-only 22:17 (red), fix 22:28 (red on a depleted-item test), corrected 22:35 (green), merged 22:57 | **done** | the pipeline caught an over-reach of the first fix (removal from a depleted item); fixed before merge |
| One blocked pull request | PR #14 (BR-2 violation, run 43916978299) and PR #16 (killing tests removed, run 43933840489) | **done** | PR #16 passed a 90 % mutation gate at 90.4 % → gate raised to 95 % and the PR re-blocked (94.3 %) |
| Fix the accessibility finding | PR #15, merged 11-17 01:23 after a green run | **done** | first version (`alt=""`) introduced an axe rule; corrected to use the aria-label; Lighthouse 78 → 85 |
| Re-run mutation on the final code | 11-16 23:54: 248 mutants, 238 killed, 10 equivalents | **done** | 7 more killing tests; equivalents keyed by function + mutation + original code |
| E2E in traceability | 11-17 01:38 (`tools/gen_traceability.py` reads the Playwright report) | **done** | — |
| Final review round | 4 independent graders 11-17 | **done** | contradictions between documents reconciled (test counts, access matrix 20/20, mutation figures) |
| Complete MCC for all four business rules | BR-4 added 11-17 08:04 | **done** | 13 decisions now covered |
| Real mutmut run (the first attempt had failed because of our set-up) | 11-17/18: 652 mutants, all survivors classified | **done** | set-up fixed (newline lists, migrated DB); mutmut statuses went stale after tests were added, so every survivor was re-checked directly |
| Fix the remaining functional defects (not planned in report 1 beyond DEF-01) | PR #17 DEF-02/03/04, PR #18 DEF-06 + SEC-01/02 (11-18), each merged after a green pipeline | **done** | DEF-03 (Critical) and DEF-06 (High) closed: EC-1 is met now |
| Re-measure performance after DEF-06 | k6, 4 setups x 2 runs x 1/5 users (11-18) | **done** | failures 19.5 % -> 0 %; p95 545-556 ms is still above 500 ms: EC-3 stays NOT met; the Basic-auth artefact of the script was found and reported next to the token-auth result |
| Re-run the custom-operator mutation analysis on the final code | 263 mutants, 254 killed, 9 equivalent (11-18) | **done** | a missing per-item overflow test was found and added |
| Final PDF and zip | 11-18 | **done** | section B; human review hours estimated and recorded |

## 2. GQM metrics now (definitions and targets: `docs/GQM.md`)
| Goal | Metric | Value | Target | Reading |
|---|---|---|---|---|
| G1 Find defects effectively | Defect density = functional defects (DEF-01…06) ÷ KLOC (module ncloc 5165) | 6 ÷ 5.165 = **1.16/KLOC** (all 12 findings: 2.32) | reported; > 1.0 triggers extra exploratory testing | unchanged: no new functional defect was found after report 1, so detection has saturated for this scope |
| G2 Cover requirements | Requirements coverage | tested **16/16**, verified passing 16/16 | 100 % tested | all requirements have a passing test since DEF-01 and DEF-02 are fixed |
| G3 Healthy defect process | Reopen rate = reopened ÷ closed | 0 ÷ 8 = **0 %** (8 defects closed, none reopened) | ≤ 10 % | met |
| G4 Effective tests | Mutation score (adjusted) | **100.0 %** (raw 96.6 %) | ≥ 85 % (CI gate 95 %) | met; the gate itself was tightened after PR #16 |

## 3. Control actions taken in this period
- Mutation gate 85 → 90 → **95 %** (evidence: PR #16 run 43927877708 passed at 90.4 %, run 43933840489 blocked at 94.3 %).
- Merge of PR #15 by admin bypass was not used; the branch was updated and the pipeline re-run to green instead (strict branch protection).
- Keyboard test made independent of the focus-trap start state after it failed in CI only (run 43931016096).
- No Critical/High defect is open at the end; the release decision stays **HOLD** only because EC-3 (5-user p95) is not met (`docs/COMPLETION_REPORT.md`).

## 4. Effort (estimate vs actual, `docs/EFFORT_LOG.csv`)
Agent hours logged for the whole project: **16.55 h** against a three-point estimate of 70.0 h (the estimate assumed human effort; human review hours are estimated at 32.0 h in `docs/EFFORT_NOTE.md`). The corrective work of this period (review rounds, PR fixes, final package) is part of the rows "CI quality gate + PRs", "Defects, RCA, reports" and "Final PDF + package".

## 5. Plan for the next period (after submission)
Reduce the per-request cost of the write path or move to PostgreSQL and re-run the k6 protocol (EC-3); migrate to react-router 7 (SEC-03); keyboard Enter-to-submit and contrast fixes (UX-01, A11Y-02); investigate the first-login failure (DEF-05).
