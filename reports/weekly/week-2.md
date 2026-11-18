# WEEKLY PROGRESS REPORT 2 of 2 — corrective actions and closure (2026-11-16 22:17 … 2026-11-17) against the plan (`docs/TEST_PLAN.md` v0.3)

Continues `reports/weekly/week-1.md` (checkpoint 2026-11-16 21:48). Same note: the two reports are the two checkpoints of the real commit timeline.

## 1. Progress against the plan
| Planned item (from report 1 §5) | Actual (commit/PR time) | Status | Control action |
|---|---|---|---|
| Fix DEF-01 with a red → green pipeline | PR #13: tests-only 22:17 (red), fix 22:28 (red on a depleted-item test), corrected 22:35 (green), merged 22:57 | **done** | the pipeline caught my own over-reach (removal from a depleted item); fixed before merge |
| One blocked pull request | PR #14 (BR-2 violation, run 43916978299) and PR #16 (killing tests removed, run 43933840489) | **done** | PR #16 passed a 90 % mutation gate at 90.4 % → gate raised to 95 % and the PR re-blocked (94.3 %) |
| Fix the accessibility finding | PR #15, merged 11-17 01:23 after a green run | **done** | first version (`alt=""`) introduced an axe rule; corrected to use the aria-label; Lighthouse 78 → 85 |
| Re-run mutation on the final code | 11-16 23:54: 248 mutants, 238 killed, 10 equivalents | **done** | 7 more killing tests; equivalents keyed by function + mutation + original code |
| E2E in traceability | 11-17 01:38 (`tools/gen_traceability.py` reads the Playwright report) | **done** | — |
| Final review round | 4 independent graders 11-17 | **done** | contradictions between documents reconciled (test counts, access matrix 20/20, mutation figures) |
| Complete MCC for all four business rules | BR-4 added 11-17 08:04 | **done** | 13 decisions now covered |
| Final PDF and zip | 11-17 08:04 | **done** | section B; human review hours estimated and recorded |

## 2. GQM metrics now (definitions and targets: `docs/GQM.md`)
| Goal | Metric | Value | Target | Reading |
|---|---|---|---|---|
| G1 Find defects effectively | Defect density = functional defects (DEF-01…06) ÷ KLOC (module ncloc 5114) | 6 ÷ 5.114 = **1.17/KLOC** (all 12 findings: 2.35) | reported; > 1.0 triggers extra exploratory testing | unchanged: no new functional defect was found after report 1, so detection has saturated for this scope |
| G2 Cover requirements | Requirements coverage | tested **16/16**, verified passing 16/16 | 100 % tested | FR-07's over-removal rule is now passing (DEF-01 fixed); FR-03b stays unverified until DEF-02 is fixed |
| G3 Healthy defect process | Reopen rate = reopened ÷ closed | 0 ÷ 2 = **0 %** (DEF-01, A11Y-01 closed) | ≤ 10 % | met, on a small sample |
| G4 Effective tests | Mutation score (adjusted) | **100.0 %** (raw 96.6 %) | ≥ 85 % (CI gate 95 %) | met; the gate itself was tightened after PR #16 |

## 3. Control actions taken in this period
- Mutation gate 85 → 90 → **95 %** (evidence: PR #16 run 43927877708 passed at 90.4 %, run 43933840489 blocked at 94.3 %).
- Merge of PR #15 by admin bypass was not used; the branch was updated and the pipeline re-run to green instead (strict branch protection).
- Keyboard test made independent of the focus-trap start state after it failed in CI only (run 43931016096).
- Open Critical/High at the end: DEF-03, DEF-06 → release decision stays **HOLD** (`docs/COMPLETION_REPORT.md`).

## 4. Effort (estimate vs actual, `docs/EFFORT_LOG.csv`)
Agent hours logged for the whole project: **16.55 h** against a three-point estimate of 70.0 h (the estimate assumed human effort; human review hours are estimated at 32.0 h in `docs/EFFORT_NOTE.md`). The corrective work of this period (review rounds, PR fixes, final package) is part of the rows "CI quality gate + PRs", "Defects, RCA, reports" and "Final PDF + package".

## 5. Plan for the next period (after submission)
Reduce the per-request cost of the write path or move to PostgreSQL and re-run the k6 protocol (EC-3); migrate to react-router 7 (SEC-03); keyboard Enter-to-submit and contrast fixes (UX-01, A11Y-02); investigate the first-login failure (DEF-05).
