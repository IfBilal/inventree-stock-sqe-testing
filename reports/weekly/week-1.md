# WEEKLY PROGRESS REPORT 1 of 2 — build-up and measurement (checkpoint 2026-11-16 21:48, commit "Defect log with Pareto…") against the plan (`docs/TEST_PLAN.md` v0.2, the version valid at that checkpoint)
*Reporting period note:* the whole project ran inside two working days, so the two "weekly" reports are the two checkpoints of the real commit timeline (`git log`): report 1 = everything up to the first complete measurement of all test levels (Phases 0–13, first pass), report 2 = the corrective and closure work that followed. Figures below are those valid at the checkpoint (taken from the commits and evidence files of that time).

## 1. Progress against the plan (v0.2 schedule)
| Phase | Planned | Actual (commit time) | Status at checkpoint | Control action |
|---|---|---|---|---|
| 0 environment/baseline | 11-16 | 11-16 17:58 | done | reset determinism verified (mutate → reset → compare) |
| 1 scope/basis/use cases | 11-16 | 11-16 17:51, fixed 18:06 | done after review | docs corrected after the empirical audit (history model, BR-2 wording) |
| 2 test management | 11-16 | 11-16 17:59, v0.2 18:32 | done | exit criteria re-tied to the highest risks after review |
| 3 static analysis | 11-17 | 11-16 18:28 (ahead) | done | Sonar-vs-hand complexity discrepancy investigated experimentally |
| 4 unit/white-box | 11-17…18 | 11-16 18:38, widened 18:59, 20:01 | done, 3 review rounds | scope widened (can_delete, tracking, permissions); BR-3 3-condition MCC added |
| 5–6 generator and API | 11-18…19 | 11-16 18:42, 19:31 | done | generator rewritten after review (valid spec, all keywords, response validation) |
| 7–8 E2E, usability, accessibility | 11-19…20 | 11-16 20:50, 21:00 | done | DEF-05 found and handled visibly; first accessibility fix on a branch |
| 9 security | 11-20 | 11-16 21:10 | done | passive scan only; SEC-01…03 logged |
| 10 performance/recovery | 11-21 | 11-16 21:22 | done | EC-3 missed → DEF-06, HOLD |
| 11 mutation | 11-21…22 | 11-16 22:17 (first analysis) | done | first mutmut attempt failed (set-up errors, fixed in report 2), own AST runner with custom operators used; 9 killing tests added |
| 12 CI gate | 11-22…23 | 11-16 21:38 | done | threshold chosen from measured scores |
| 13 defects/RCA/reports | 11-23…24 | 11-16 21:48 | done | RCA-1 (DEF-01), RCA-2 (DEF-06) |

## 2. GQM metrics at the checkpoint (definitions/targets: `docs/GQM.md`)
| Goal | Metric | Value | Target | Reading |
|---|---|---|---|---|
| G1 Find defects effectively | Defect density = functional defects (DEF-01…06) ÷ KLOC (ncloc 5.114) | 6 ÷ 5.114 = **1.17/KLOC** (all 12 findings: 2.35) | reported; > 1.0 triggers extra exploratory testing | above 1.0 → input-boundary tests for zero, overflow and malformed items kept as strict-xfail pins (DEF-02…04) |
| G2 Cover requirements | Requirements coverage | tested **16/16**; verified passing 15/16 (FR-03b only as strict-xfail; FR-07 verified only for the allowed range, its over-removal rule failing on the baseline) | 100 % tested | met for "tested"; FR-03b only demonstrates a defect |
| G3 Healthy defect process | Reopen rate = reopened ÷ closed | 0 closed, 0 reopened (no data yet) | ≤ 10 % | not yet meaningful |
| G4 Effective tests | Mutation score, first analysis | raw **88.9 %** (244 mutants, 27 survivors) → 93.9 % after 9 killing tests | ≥ 85 % at the time | met; survivors classified as equivalent / missing test / weak assertion |

## 3. Control actions taken in this period
- After every phase two or more independent reviewer agents graded the work against the rubric (`reviews/README.md`); every finding was fixed before moving on.
- First mutation run discarded and repeated on a clean export after a working-tree mistake (no false numbers reported).
- Performance risk PR-08 re-scored Medium → High after measurement; DEF-03 re-triaged High → Critical when one corrupted item was shown to break the whole stock list.
- Open Critical/High at the checkpoint: DEF-01, DEF-03, DEF-06 → release decision HOLD.

## 4. Effort (estimate vs actual, `docs/EFFORT_LOG.csv`)
Agent hours logged for all areas except "Final PDF + package": **12.05 h** against the three-point estimate 64.7 h for the same areas (estimate = human effort; human review hours to be added by the members).

## 5. Plan for the next period
Fix DEF-01 through a pull request with a failing-then-passing pipeline; show one blocked pull request; fix the accessibility finding; re-run the full mutation analysis on the final code; complete traceability for E2E; final review round; build the PDF and zip.
