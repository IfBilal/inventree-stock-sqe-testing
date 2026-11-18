# FINAL RELEASE / HOLD DECISION AND EVIDENCE LINKS

## Decision: **HOLD**

The three exit criteria of the test plan (`docs/TEST_PLAN.md` §7), actual versus target (the PDF ends with the decision, as the project statement requires):

| ID | Category | Target | Actual (evidence) | Met? |
|---|---|---|---|---|
| EC-1 | Functional (risks PR-01, PR-03, PR-06) | 100 % of own business-rule tests pass on the fixed build; **0 open Critical/High defects**; 0 unjustified uncovered lines (in-scope statements 100 %, branches 100 % with justification); all 6 basis paths and MC/DC pairs of `validate_pk` pass; retried request yields 0 duplicates | Tests pass on the fixed build (unit/API/E2E, §2). In-scope coverage statements **100.0 %**, branches **99.3 %** (1 unreachable branch justified: `docs/COVERAGE_JUSTIFICATION.md`). MCC rows 32/32, MC/DC set and 6 basis paths pass. Recovery tests: 0 duplicates. **Open Critical/High defects: 0 (none)** | **YES** |
| EC-2 | Security (risks PR-02, PR-10) | all access-matrix decisions (≥ 4, ≥ 1 allowed, ≥ 1 denied) match; 0 unresolved High/Critical in the audited dependency set | **20/20** access decisions match (allowed and denied). Backend: 166 packages, 0 vulnerabilities. Frontend: 1 High advisory (`zod`, build tooling only, not in the served bundle) — dispositioned (accepted, SEC-03 / `docs/SECURITY.md` §4.2); 2 moderate `react-router` advisories in the shipped bundle (SEC-03, accepted risk: no patched 6.x release) | **YES** on the tested scope (with dispositions) |
| EC-3 | Performance (risk PR-08) | `POST /api/stock/remove/` at 5 users: p95 ≤ 500 ms and unexpected failures < 1 % | 1 user: p95 301 / 308 ms, failures 0.0 % / 0.0 % (met). **5 users (token auth, after the DEF-06 fix): p95 556 / 545 ms, failures 0.0 % / 0.0 %** — the failure criterion is met, the p95 criterion is not. Baseline before the fix: p95 518 / 522 ms, failures 19.3 % / 19.7 %. Variants (Basic auth, gunicorn) in `docs/PERFORMANCE.md` §7 | **NO** |

## Evidence links (repository https://github.com/IfBilal/inventree-stock-sqe-testing)
| What | Where |
|---|---|
| Source, tests, tools, scripts | `tests/team/`, `tools/`, `scripts/`, `.github/workflows/quality-gate.yml` |
| Raw evidence per phase | `evidence/` (sonar, coverage, generator, api, traceability, a11y, security, mutation, ci), `reports/performance/`, `reports/playwright-report.json` |
| Defects (GitHub Issues) | https://github.com/IfBilal/inventree-stock-sqe-testing/issues (12 issues, labels for severity, priority, status, triage); log in `docs/DEFECTS.md` |
| Pull requests | #13 (DEF-01, red to green), #14 and #16 (blocked by the pipeline), #15 (accessibility), #17 (DEF-02/03/04), #18 (DEF-06, SEC-01/02) — https://github.com/IfBilal/inventree-stock-sqe-testing/pulls?q=is%3Apr |
| Pipeline runs | https://github.com/IfBilal/inventree-stock-sqe-testing/actions (table in `docs/CI_QUALITY_GATE.md` and §6 of the completion report) |
| Traceability matrix | `docs/TRACEABILITY.md` (generated from the test results) |
| Weekly reports | `reports/weekly/week-1.md`, `reports/weekly/week-2.md` |
| Review log of the independent graders | `reviews/README.md` |
| AI-use record and effort | `docs/AI_USE_RECORD.md`, `docs/EFFORT_LOG.csv`, `docs/EFFORT_NOTE.md` |
