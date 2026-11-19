# TEST PLAN — InvenTree Stock Module (Add Stock / Remove Stock)  · v0.4
Living document, updated at each phase gate (version history at the end).

## 1. Purpose and scope
Verify the quality of the Stock adjustment workflows of InvenTree 1.8.0 dev (commit `1f51dfe64bf4717fd95df51f1055ffb7a991a01d`) as defined in `docs/TEST_BASIS.md`.
- **In scope:** WF-A Add stock, WF-B Remove stock; roles `stock_manager` and `stock_viewer`; API `/api/stock/add/`, `/api/stock/remove/`, read-backs `GET /api/stock/{id}/` and audit history; browser stock actions; BR-1..BR-4; FR-01..FR-11.
- **Out of scope:** transfer/count/serialization workflows, purchase/sales/build orders, plugins, multi-node/PostgreSQL behaviour, email, mobile apps, load beyond the chosen operation.
- **Items under test:** `stock/serializers.py`, `stock/models.py`, `stock/api.py` (function list in TEST_BASIS §7), the React stock dialogs, the HTTP API.

## 2. Test approach by risk level (risk register: `docs/RISK_REGISTER.md`)
| Level | Risks | Test levels | Techniques |
|---|---|---|---|
| Critical | PR-01 | Unit, API, E2E, mutation, CI gate | EP, 3-point BVA, decision table, state transition, **MCC + MC/DC**, mutation |
| High | PR-02, PR-03, PR-04, PR-06, PR-07, PR-10, PJ-01..03 | Unit/API with read-back, access matrix, dependency audit | EP, BVA, decision table, **MCC + MC/DC for the multi-condition decision (PR-03)**, recovery test |
| Medium | PR-05, PR-08, PR-09 | API/E2E/tool-based | API integration with mixed items, k6, Lighthouse + axe |
| Low | — | not applicable | no risk scored ≤ 5, so no technique/depth is defined for this level |
Levels from the project statement: Unit (pytest + coverage.py), API/integration (pytest + requests, generated EP/BVA), Browser E2E (Playwright, 6 use cases), usability/accessibility (Playwright, Lighthouse, axe-core), security (access matrix, ZAP passive, pip-audit), performance/recovery (k6, test double), static analysis (SonarQube), mutation (own AST runner with standard + 4 custom operators; mutmut attempted and unusable), CI (GitHub Actions).

## 3. Roles and responsibilities
| Member | Roll | Owned area | Management role |
|---|---|---|---|
| M1 | 24I-3166 | Area 1: static analysis, white-box unit tests, mutation, CI | **Plan and risk-register owner** |
| M2 | 24I-3015 | Area 2: API testing, OpenAPI spec and test-data generation | **Defect-triage owner** (severity/priority decisions) |
| M3 | 24I-3106 | Area 3: use cases, usability, accessibility, security, performance | **Progress/completion-report owner** |
Test management documents are reviewed by all three; the owner is accountable for keeping the document current.

## 4. Environment
Linux 7.0, Python 3.12.3, Django 5.2.19, SQLite, Node 24.11.1, Playwright 1.65.1 (Chromium), k6 2.3.0, SonarQube Community Build 26.10 run from the zip distribution on JDK 21 (the Docker daemon is not running on this machine, so Docker is **not** used), server `127.0.0.1:8000`. Exact versions: `docs/TOOL_VERSIONS.md`. 12 CPUs, 15 GB RAM, ~5 GB free disk (risk PJ-01).

## 5. Test data
Synthetic only. `scripts/reset.sh` seeds users admin/manager/viewer, Keyboard (10), Mouse (25), Monitor (0), all `delete_on_deplete=False`. Unit/API tests create their own data in a throw-away DB or reset per test. Boundary/EP values for API tests are produced by `tools/gen_testdata.py` from `openapi/stock.yaml` (produced in Phase 5).

## 6. Schedule (internal targets; the official deadline is set by the instructor) — updated v0.2
| Phase | Planned window | Actual | Responsible |
|---|---|---|---|
| 0 environment, baseline | 11-16 | 11-16 done | M1 (shared) |
| 1 scope, basis, use cases | 11-16 | 11-16 done | all |
| 2 test management | 11-16 | 11-16 done (v0.2 after review) | M1 owner |
| 3 static analysis | 11-17 → pulled forward | 11-16 done | M1 |
| 4 unit/white-box | 11-17 – 11-18 | 11-16 done (3 review rounds) | M1 |
| 5–6 generator and API | 11-18 – 11-19 | 11-16 done | M2 |
| 7–8 E2E, usability, accessibility | 11-19 – 11-20 | 11-16 done | M3 + each member's own use cases |
| 9 security | 11-20 | 11-16 done | M3 |
| 10 performance/recovery | 11-21 | 11-16 done | M3 |
| 11–12 mutation and CI | 11-21 – 11-23 | 11-16 done | M1 |
| 13 defects, monitoring, completion | 11-23 – 11-24 | first pass 11-16; defect fixes, re-measurement and closure 11-17/18 (done) | M2 (defects), M3 (reports) |
| 14 final package | 11-24 – 11-26 | 11-18 done (PDF + zip rebuilt after each review round) | all |

## 7. Entry, exit, suspension, resumption criteria
**Entry criteria (all levels):** `scripts/reset.sh` reproducible; server answers `/api/`; seed counts match; previous phase gate passed.
| Level | Additional entry criteria |
|---|---|
| Unit | in-scope function list frozen (TEST_BASIS §7); throw-away test DB works (`scripts/test_unit.sh`) |
| API | `openapi/stock.yaml` reviewed; generator unit-tested |
| E2E / usability | use-case flows frozen (`docs/USE_CASES.md`); Playwright Chromium installed; UI built |
| Security | Phase 6 API tests green; ZAP runtime available |
| Performance | targets declared and committed (`docs/PERF_TARGETS.md`) before the first k6 run |
| Mutation / CI | unit suite passes on the fixed build; coverage at target |

**Exit (release) criteria** — exactly three; they are also the release criteria in the completion report. "Highest risks" = Critical + High.
| ID | Category | Criterion (measurable) | Target | Tied to risk |
|---|---|---|---|---|
| EC-1 | Functional | On the fixed build: 100 % of own business-rule tests pass; **0 open Critical/High defects**; **0 unjustified uncovered lines** (each uncovered statement/branch listed with reason in `docs/COVERAGE_JUSTIFICATION.md`) in the in-scope logic: 100 % statements and ≥ 99 % branches (the one unreachable branch is justified); all 6 basis paths and all MC/DC pairs of `validate_pk` pass; repeated/retried request test yields 0 duplicate adjustments | 100 % pass, 0 open C/H, 100 % statements / ≥ 99 % branches with justification, 0 duplicates after a retry (no idempotency key exists, W-03; the test shows a retry after a FAILED attempt is safe) | **PR-01 (Critical)**, **PR-03 (High)**, **PR-06 (High)** |
| EC-2 | Security | All access-matrix decisions (≥ 4, ≥ 1 allowed, ≥ 1 denied) match the matrix, **and** 0 unresolved High/Critical findings in the audited dependency set (each finding listed with disposition) | 100 % decisions correct, 0 unresolved High/Critical | **PR-02 (High)**, **PR-10 (High)** |
| EC-3 | Performance | `POST /api/stock/remove/` at 5 users: p95 ≤ **500 ms** and unexpected failures < **1 %** (declared in `docs/PERF_TARGETS.md`) | p95 ≤ 500 ms, failures < 1 % | PR-08 (Medium) |
CI quality-gate thresholds (coverage, mutation score, Sonar) are separate and justified in Phase 12.
**Suspension:** server cannot start or seed differs from baseline; CI cannot run; > 3 blocker defects in the same area. **Resumption:** environment restored via `scripts/reset.sh`, seed check passes, blocker defects triaged.

## 8. Risks
Product and project risks with L×I, matrix, basis, owners and status: `docs/RISK_REGISTER.md` (10 product, 3 project).

## 9. Estimation (three-point, hours; E = (O + 4M + P) / 6; row E rounded to 1 dp, total computed from the column sums)
Basis: author experience with the tools plus the observed effort for completed phases; assumptions: tools install without blockers (optimistic), one tooling blocker per area (pessimistic). Actual effort is logged in `docs/EFFORT_LOG.csv` and compared in the completion report.
| Area | O | M | P | E | Actual (filled at end) |
|---|---|---|---|---|---|
| Setup, environment, baseline | 1 | 1.5 | 3 | 1.7 | 0.75 h (agent) · variance E−actual = +0.9 h |
| Scope, basis, use cases | 1 | 2 | 4 | 2.2 | 0.40 h agent + 1.5 h human (est.) = 1.90 h · variance E−actual = +0.3 h |
| Test management docs | 2 | 3 | 6 | 3.3 | 0.50 h agent + 2.0 h human (est.) = 2.50 h · variance E−actual = +0.8 h |
| Static analysis + hand CFG | 2 | 3 | 5 | 3.2 | 0.80 h agent + 1.5 h human (est.) = 2.30 h · variance E−actual = +0.9 h |
| Unit tests, MCC, MC/DC | 5 | 8 | 14 | 8.5 | 1.20 h agent + 4.0 h human (est.) = 5.20 h · variance E−actual = +3.3 h |
| OpenAPI + generator | 2 | 4 | 7 | 4.2 | 0.60 h agent + 2.0 h human (est.) = 2.60 h · variance E−actual = +1.6 h |
| API/integration tests | 4 | 6 | 10 | 6.3 | 1.30 h agent + 3.0 h human (est.) = 4.30 h · variance E−actual = +2.0 h |
| Use cases + E2E | 4 | 7 | 12 | 7.3 | 1.00 h agent + 3.0 h human (est.) = 4.00 h · variance E−actual = +3.3 h |
| Usability + accessibility | 2 | 4 | 7 | 4.2 | 0.80 h agent + 2.0 h human (est.) = 2.80 h · variance E−actual = +1.4 h |
| Security | 2 | 3 | 6 | 3.3 | 0.60 h agent + 1.5 h human (est.) = 2.10 h · variance E−actual = +1.2 h |
| Performance + recovery | 2 | 4 | 8 | 4.3 | 0.70 h agent + 1.5 h human (est.) = 2.20 h · variance E−actual = +2.1 h |
| Mutation + custom operators | 3 | 6 | 12 | 6.5 | 4.60 h agent + 3.0 h human (est.) = 7.60 h · variance E−actual = -1.1 h |
| CI quality gate + PRs | 2 | 4 | 8 | 4.3 | 1.00 h agent + 2.0 h human (est.) = 3.00 h · variance E−actual = +1.3 h |
| Defects, RCA, reports | 3 | 5 | 9 | 5.3 | 0.80 h agent + 2.5 h human (est.) = 3.30 h · variance E−actual = +2.0 h |
| Final PDF + package | 3 | 5 | 9 | 5.3 | 1.50 h agent + 1.5 h human (est.) = 3.00 h · variance E−actual = +2.3 h |
| **Total** | 38 | 65.5 | 120 | **70.0** = (38 + 4×65.5 + 120)/6 | **16.55 h agent + 32.0 h human review (estimated) = 48.55 h** (variance E−actual = +21.5 h; `docs/EFFORT_NOTE.md`) |

## 10. Control, reporting and traceability
- Weekly progress reports (`reports/weekly/`) against this plan with control actions and GQM metrics with targets (`docs/GQM.md`).
- Defects live in GitHub Issues of **this** repository (never upstream).
- **Traceability matrix:** `docs/TRACEABILITY.md` (requirement → risk → technique/level → test IDs → status). Requirements coverage = requirements with ≥ 1 passing test ÷ total (16 items: FR-01, FR-02, FR-03a, FR-03b, FR-04…FR-11, BR-1…BR-4 — i.e. 11 FR + FR-03 split + 4 BR). Current value (generated): **tested 16 / 16 (100 %), verified passing 16 / 16 (100 %)** (every requirement has at least one passing test; `docs/TRACEABILITY.md`); updated at every gate.

## 11. Version history
| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-11-16 | Initial plan after Phase 1 |
| 0.2 | 2026-11-16 | After review of Phases 2–3: estimate total corrected (67.9 → 70.0 with a Setup row); Docker claim removed (SonarQube ran from zip on JDK 21); exit criteria re-tied to the highest risks and given numeric targets; per-level entry criteria; owners and responsibility columns; Low row; actual schedule dates; traceability skeleton and tool-version document added |
| 0.3 | 2026-11-16 | After Phases 4–12: schedule actuals (all phases done on 11-16), estimate table completed with actual agent hours and variance per area, requirements coverage generated from test results, exit criteria evaluated in `docs/COMPLETION_REPORT.md` (EC-1 and EC-3 not met → HOLD), risk statuses re-assessed from evidence |
| 0.4 | 2026-11-18 | After the defect fixes (PRs #13, #15, #17, #18): exit criteria re-evaluated (EC-1 met, EC-2 met, EC-3 p95 not met), human review hours estimated, risk statuses updated (risk register v0.4), real mutmut run added |
