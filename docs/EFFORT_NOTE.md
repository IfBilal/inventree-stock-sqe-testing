# Effort-log note (read with `docs/EFFORT_LOG.csv`)
- `agent_hours` = working time of the AI assistant derived from Git commit timestamps and the session clock (approximate; several agents ran in parallel, so the sum can exceed wall-clock time).
- `human_review_hours` is intentionally **empty**: only the team members can state how long they spent reading, running and understanding each area. They must fill it in before submission (the viva checks understanding of the owned area).
- Variance (estimate E vs actual) is computed in the completion report from these two columns per estimate row.

## Reading the estimate-versus-actual comparison (important caveat)
The three-point estimate in `docs/TEST_PLAN.md` §9 (70 h) is **human effort** for a team of three. The "actual" column is the **AI-agent wall-clock time** measured from commit timestamps (12.55 h), because the work was executed by an AI assistant under the instructor's AI-use permission. The two are therefore **not comparable as a variance**; the table shows them side by side only so that the members can add their own review/verification hours (`human_review_hours` in `docs/EFFORT_LOG.csv`, currently blank) and then compute the true variance per area. Mutation rows in the log were counted for the first analysis (244 mutants); the final analysis has 248 mutants (`docs/MUTATION.md`).
