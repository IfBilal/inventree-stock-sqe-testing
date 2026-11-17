# MASTER IMPLEMENTATION PLAN — SE3002 SQE Final Project

Target: InvenTree Stock module. Requirement IDs (R-xx) refer to `docs/REQUIREMENTS.md`.
Working rules:
- **Evidence is real.** Every number/report in the final PDF comes from a tool run stored under `evidence/`. Nothing is hand-edited (R-56).
- **Every phase ends with a gate**, then 2–3 strict reviewer subagents grade the phase against the rubric. Fix → re-review until all say PASS. Review verdicts saved in `reviews/phaseNN-roundK.md`.
- **AI-use record** (`docs/AI_USE_RECORD.md`) is appended to at every phase (tool, purpose, output, what was checked/changed). Prompts kept in `docs/prompts/`.
- Repo layout: `upstream/` (pinned InvenTree checkout, untouched baseline), `tests/team/` (all our tests), `tools/` (generator, scripts), `openapi/`, `evidence/`, `reports/`, `docs/`, `.github/workflows/`.

---
## PHASE 0 — Environment, baseline and reproducibility (R-01..R-03, R-11, R-12, R-49)
Tasks
1. Create repo skeleton; `git init`; configure three author identities (24I-3166, 24I-3015, 24I-3106).
2. Clone InvenTree at pinned commit into `upstream/`; record URL, licence (MIT), commit hash in `docs/BASELINE.md`.
3. Install in venv (Python 3.12), SQLite DB (no Postgres available locally; justified), run migrations, create superuser + test roles.
4. Scripts: `scripts/install.sh`, `start.sh`, `seed.sh` (synthetic data: categories, parts, locations, stock), `reset.sh` (drop DB, remigrate, reseed — deterministic).
5. Verify UI loads in Chrome, API responds at `/api/`, OpenAPI schema retrievable (`/api/schema/`).
6. Commit baseline with tag `baseline`.
Gate: fresh clone → `install.sh && seed.sh && start.sh` works; `reset.sh` restores identical state (count checks); UI + API respond. Disk budget checked (<3 GB used).

## PHASE 1 — System, scope, workflows, test basis (R-04..R-10, R-26)
1. Explore Stock module docs + source; confirm which endpoints implement Add/Remove stock (`/api/stock/add/`, `/api/stock/remove/`, adjust).
2. Define Workflow A (Add stock) and B (Remove stock): starting condition, action, expected outcome. Shared record = StockItem.quantity.
3. ≥ 8 functional requirements (≥ 3 per workflow) with IDs FR-01...
4. 4 business rules: BR1 limit (remove ≤ quantity), BR2 multi-condition decision, BR3 state-change rule, BR4 role permission rule. 2 roles with different permissions (verify in source/UI).
5. Shared records read/changed per workflow table. Justified assumptions recorded.
6. `docs/TEST_BASIS.md`, `docs/USE_CASES.md` (6 use cases: 2 per member, each ≥ 2 alt + ≥ 2 exception flows, preconditions, postconditions).
7. Google Sheet entry text (URL, description) in `docs/SHEET_ENTRY.md`.
Gate: every FR/BR traced to source file/doc or recorded assumption; roles verified empirically against running system.

## PHASE 2 — Test management foundation (R-15..R-19, R-21)
1. `docs/TEST_PLAN.md` (all required sections; living — version history).
2. Risk register (≥ 8 product + ≥ 2 project, L×I 1–5, 5×5 matrix) → technique/depth mapping.
3. Exit criteria ≥ 3 measurable, ≥ 2 tied to the highest risks.
4. Three-point estimates per area (O/M/P); actual-effort log started (`docs/EFFORT_LOG.csv`).
5. Traceability matrix skeleton (FR/BR → risk → test IDs); later filled automatically from test markers.
6. Weekly report template + GQM table (goal, question, metric).
Gate: risk IDs referenced in plan; exit criteria measurable; matrix has no orphan requirement.

## PHASE 3 — Static analysis: SonarQube + hand CFG (R-13, R-14)
1. Run SonarQube Community in Docker (check disk; limit memory), scan `upstream/` backend stock code + our tests.
2. Capture metrics via API (complexity, duplication, smells, bugs, vulnerabilities, coverage, debt, ratings) into `evidence/sonar/`.
3. Write interpretation per metric.
4. Select one business-rule function; draw CFG; compute V(G) = E−N+2P and predicate count+1; compare with Sonar's cognitive/cyclomatic.
Gate: screenshots/JSON from real scan; hand calc matches or discrepancy explained.

## PHASE 4 — White-box unit tests (R-23, R-27) — 16 marks
1. Define the business-logic scope list (files/functions) in TEST_BASIS.
2. Write pytest tests in `tests/team/unit/` exercising Django models/serializers directly (not upstream tests).
3. Measure coverage with coverage.py (branch on), only upstream code in scope; iterate to 100% statement + branch; document any justified uncovered lines.
4. Critical module (adjustment/remove logic): build truth table of the multi-condition decisions → complete MCC → derive MC/DC pairs → tests mapped to pairs.
5. Cover all four business rules; apply EP/BVA/decision table/state transition where they fit.
Gate: coverage report shows 100%/100% for scope; MC/DC table with test-ID mapping; strict review.

## PHASE 5 — OpenAPI spec and test-data generator (R-28..R-30) — 7 marks
1. OpenAPI spec for the used endpoints (verify project's own is accurate; write/curate `openapi/stock.yaml`).
2. `tools/gen_testdata.py`: reads spec → EP classes (valid/invalid per field) + 3-point BVA (min−1/min/min+1 style: below, at, just above, etc.) → JSON.
3. Generator unit-tested; outputs deterministic.
4. Demo: change two constraints (e.g. quantity minimum, reason max length), regenerate, show diff (`evidence/generator/`).
Gate: API tests import generator output only (no hard-coded values).

## PHASE 6 — API and integration tests (R-24, R-27) — 10 marks
1. pytest + requests against running server (fixtures seed/reset per test).
2. EP + 3-point BVA on every input of both endpoints; auto-parameterised from generator.
3. API coverage criteria (all endpoints, methods, status codes, params, content types) tracked in a coverage table.
4. Rule rejections, invalid state transitions, repeated requests (no duplicates), read-back of shared records after success and rejection, cross-workflow checks.
5. Endpoint weaknesses report (real findings only).
Gate: criteria table complete; zero hard-coded boundary values; findings evidenced.

## PHASE 7 — Use cases and Playwright E2E (R-25, R-26, R-35..R-37) — 9 marks
1. 6 use cases (2/member), each ≥ 2 alt + ≥ 2 exception flows; every flow automated; assert UI result and postconditions via API/DB.
2. Two usability tests: confirmation assertion; rule-rejection → error explains → correct → success; keyboard-order test.
Gate: all flows pass; flow-to-test traceability table.

## PHASE 8 — Accessibility: Lighthouse + axe-core (R-38..R-40) — 5 marks
1. Lighthouse on each use case key screen (logged in); axe full scan through Playwright.
2. Merge findings (dedupe); table element/impact/fix.
3. Fix one screen (own HTML page or patch); rerun; before/after.
Gate: raw reports stored; dedupe documented.

## PHASE 9 — Defensive security (R-41..R-43) — 6 marks
1. Routes/data inventory; access matrix; Playwright verifies ≥ 4 decisions (≥ 1 allow, ≥ 1 deny).
2. ZAP passive (Docker) proxying Playwright runs; review ≥ 2 controls (cookie flags, role checks) + source/config corroboration.
3. pip-audit (and/or Dependency-Check); record packages/versions; findings table + passing controls.
Gate: passive only; evidence reports.

## PHASE 10 — Performance and recovery (R-44..R-47) — 5 marks
1. Choose operation (e.g., POST stock remove). Declare p95 and failure thresholds with rationale before running.
2. k6: 1 VU and 5 VUs, 60 s after ramp, twice each, same build/data (reset between runs).
3. Recovery test with test double (patch DB/dependency failure mid-write) → retry → assert no duplicates.
Gate: 4 raw outputs; limits compared.

## PHASE 11 — Mutation analysis (R-31) — within 8 marks
1. mutmut 3.8.1 and the own runner (custom operators) on the business-rule module; baseline score.
2. ≥ 2 custom operators from business rules (e.g., flip `>` limit comparison; swap role check) implemented via custom mutation script; report.
3. Analyse ≥ 15 surviving mutants (equivalent / missing test / weak assertion); kill killable ones; final score.

## PHASE 12 — CI quality gate (R-32, R-33)
1. GitHub repo (public); workflow: Sonar, tests, mutation on every PR; thresholds justified; no escape hatches (lint check for `continue-on-error`/`|| true`); branch protection requires checks.
2. PR #1: documented fix (fails before, passes after). PR #2: deliberately blocked by pipeline.
Gate: real Actions run links.

## PHASE 13 — Defect management, RCA, monitoring (R-20..R-22)
1. GitHub Issues for real defects (severity, priority, status, triage); labels.
2. RCA (5 Whys + fishbone) ≥ 2 major defects; corrective + preventive; Pareto by category.
3. Weekly progress reports; GQM metrics computed from data.
4. Test completion report and release/hold decision with actual vs target for 3 criteria.

## PHASE 14 — Final package (R-48..R-54)
1. PDF report (all required sections + AI-use record + evidence links); findings each with root cause, fix, risk link.
2. Zip with `.git`; names `Project_24I-3166_24I-3015_24I-3106_<Section>.zip/.pdf` (Section **B**, confirmed by the team).
3. Viva preparation sheet per member area; rerun scripts documented.
4. Final audit: 5–6 strict rubric subagents (varying strictness); loop until all PASS with max marks.

## Review protocol (after each phase and at the end)
- 2–3 reviewers, strict teacher persona, grade against the rubric rows and the R-xx list; return “done / missing / fix list”.
- Loop until all PASS; final stage 5–6 graders at escalating strictness.
