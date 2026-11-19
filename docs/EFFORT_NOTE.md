# Effort-log note (read with `docs/EFFORT_LOG.csv`)
- `agent_hours` = working time of the AI assistant derived from Git commit timestamps and the session clock (approximate; several agents ran in parallel, so the sum can exceed wall-clock time).
- `human_review_hours` holds **estimates** (see the last section): only the team members can state how long they really spent, so each member confirms or corrects them for the owned areas.
- Variance (estimate E vs actual) is computed in the completion report from these two columns per estimate row.

## Reading the estimate-versus-actual comparison (important caveat)
The three-point estimate in `docs/TEST_PLAN.md` §9 (70 h) is **human effort** for a team of three. The "actual" column is the **AI-agent wall-clock time** measured from commit timestamps (16.55 h, all areas), because the work was executed by an AI assistant under the instructor's AI-use permission. The two are therefore **not comparable as a variance**; the table shows them side by side only so that the members can add their own review/verification hours (`human_review_hours` in `docs/EFFORT_LOG.csv`, currently blank) and then compute the true variance per area. Mutation rows in the log were counted for the first analysis (244 mutants); the final analysis has 263 mutants (`docs/MUTATION.md`; 248 was an intermediate round).

## Human review hours (estimate recorded for the team)
"Human review hours" = time the members spend reading, re-running, verifying and understanding the AI-produced work. The values in `docs/EFFORT_LOG.csv` are **estimates** made from the size and difficulty of each area, not stopwatch measurements; each member confirms or corrects them for the areas they own before submission. Total estimated: **32.0 h** (about 11 h per member) on top of 16.6 h of AI-agent time, against a human-only three-point estimate of 70 h. AI assistance cuts the human share mainly in writing and tooling; review, re-running and explaining remain human work.
| Member | Owned areas (rows of the log) | Estimated review hours | What this member re-runs |
|---|---|---|---|
| 24I-3166 (M1) | Setup, test management, static analysis, unit tests/MCC, mutation, CI | 13.5 | `scripts/coverage_unit.sh`, `tools/mcdc.py`, `tools/mutate.py --only …` |
| 24I-3015 (M2) | OpenAPI + generator, API tests, defects/RCA | 7.5 | `scripts/gen_demo.sh`, `scripts/test_api.sh api` |
| 24I-3106 (M3) | Use cases/E2E, usability, accessibility, security, performance | 8.0 | `scripts/test_e2e.sh`, `scripts/perf_run.sh` |
| shared | Scope/basis/use cases, final package | 3.0 | read all documents |
