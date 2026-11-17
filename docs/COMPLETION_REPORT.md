# TEST COMPLETION REPORT AND RELEASE / HOLD DECISION

System under test: InvenTree 1.8.0 dev, Stock module (WF-A Add stock, WF-B Remove stock), upstream commit `1f51dfe64bf4717fd95df51f1055ffb7a991a01d`, MIT. Repository: https://github.com/IfBilal/inventree-stock-sqe-testing. Team: 24I-3166, 24I-3015, 24I-3106.

## 1. Decision
> # **HOLD** — the build is **not recommended for release** as it stands.

Reasons (evidence-based): exit criteria **EC-1 (functional) and EC-3 (performance) are not met**, EC-2 (security) is met on the tested scope. Open Critical/High defects: DEF-03, DEF-06 (see §4). The over-removal data-loss defect DEF-01 was fixed through a pull request (§6) and verified by the unit, API and browser levels, but DEF-03 (overflow makes an item unreadable and breaks the whole stock list) and DEF-06 (concurrent adjustments fail with HTTP 500 on SQLite) remain. A release would be justified after those are fixed and the performance test is repeated on the production database (PostgreSQL).

### 1.1 Release criteria — actual versus target (the three exit criteria of the test plan, `docs/TEST_PLAN.md` §7)
| ID | Category | Target | Actual (evidence) | Met? |
|---|---|---|---|---|
| EC-1 | Functional (risks PR-01, PR-03, PR-06) | 100 % of own business-rule tests pass on the fixed build; **0 open Critical/High defects**; 0 unjustified uncovered lines (in-scope statements 100 %, branches 100 % with justification); all 6 basis paths and MC/DC pairs of `validate_pk` pass; retried request yields 0 duplicates | Tests pass on the fixed build (unit/API/E2E, §2). In-scope coverage statements **100.0 %**, branches **99.2 %** (1 unreachable branch justified: `docs/COVERAGE_JUSTIFICATION.md`). MCC rows 32/32, MC/DC set and 6 basis paths pass. Recovery tests: 0 duplicates. **Open Critical/High defects: 2 (DEF-03, DEF-06)** | **NO** (open Critical/High) |
| EC-2 | Security (risks PR-02, PR-10) | all access-matrix decisions (≥ 4, ≥ 1 allowed, ≥ 1 denied) match; 0 unresolved High/Critical in the audited dependency set | **20/20** access decisions match (allowed and denied). Backend: 166 packages, 0 vulnerabilities. Frontend: 1 High advisory (`zod`, build tooling only, not in the served bundle) — dispositioned (accepted, SEC-03 / `docs/SECURITY.md` §4.2); 2 moderate `react-router` advisories in the shipped bundle (SEC-03, open, Medium) | **YES** on the tested scope (with dispositions) |
| EC-3 | Performance (risk PR-08) | `POST /api/stock/remove/` at 5 users: p95 ≤ 500 ms and unexpected failures < 1 % | 1 user: p95 299 / 298 ms, failures 0.0 % / 0.0 % (met). **5 users: p95 518 / 522 ms, failures 19.3 % / 19.7 %** (both runs miss both limits) — DEF-06 | **NO** |

**Conditions to move from HOLD to RELEASE:** (1) fix DEF-03 and DEF-06 (or accept PR-08 for single-user deployments and run on PostgreSQL), (2) re-run EC-1 and EC-3, (3) address SEC-03 (`react-router`) and SEC-01 (CSP) in the deployment, (4) re-run the full pipeline green.

## 2. Results per testing activity (what was tested)
| Activity | Result | Evidence |
|---|---|---|
| Static analysis (SonarQube) | bugs 0, smells 0, vulnerabilities 0, ratings A, duplication 0.6 %, coverage 40.2 % (whole module); V(G) of `validate_pk` hand = 6 (radon 6, Sonar 5: `elif` not counted) | `docs/STATIC_ANALYSIS.md` |
| White-box unit tests | 279 passed, 8 strict-xfail (defects); in-scope coverage statements 100.0 % / branches 99.2 % over 31 functions; complete MCC for 12 decisions, MC/DC sets, BR-2 32 rows | `docs/UNIT_TESTING.md`, `docs/MCC_MCDC.md`, `docs/COVERAGE_SCOPE.md` |
| Test-data generation | OpenAPI 3.0.3 contract (validated), generator with 29 tests, 223 cases, two constraint-change demos | `docs/TEST_DATA_GENERATION.md` |
| API / integration | 244 passed, 35 strict-xfail; API coverage criteria all 100 % (endpoint, operation, status codes, roles, inputs, content types, methods, response schemas, sequences) | `docs/API_TESTING.md`, `docs/API_COVERAGE.md` |
| Browser E2E (6 use cases, 30 flows) + usability | Playwright: 33 as expected, 0 unexpected, 0 flaky (flows annotated as expected failures expose the still-open defects) | `docs/USE_CASES.md`, `docs/USABILITY.md` |
| Accessibility | Lighthouse accessibility 78 → 85 and SEO 75 → 83 on the fixed screen; image-alt and landmark-one-main resolved; remaining issues logged | `docs/ACCESSIBILITY.md` |
| Security | access matrix 20/20; ZAP passive (1599 messages): 1 Medium (no CSP), 4 Low; pip-audit 0/166; yarn audit 9 advisories (1 high build-time) | `docs/SECURITY.md` |
| Performance and recovery | targets declared first; 1 vs 5 users × 2 runs; failure-and-recovery test with test double (rollback, retry, no duplicates) | `docs/PERFORMANCE.md` |
| Mutation | 248 mutants, raw 96.0 %, adjusted **100.0 %** (10 survivors proven equivalent, 16 killed by added tests over two rounds); 4 custom operators | `docs/MUTATION.md` |
| CI quality gate | 8-job pipeline, branch protection, no escape hatches, fix PR red→green, blocked PR | `docs/CI_QUALITY_GATE.md` |
| Requirements coverage | tested 16/16, verified passing 15/16 | `docs/TRACEABILITY.md` |

## 3. Tested / not tested (scope and residual gaps)
| Tested | Not tested (and why) |
|---|---|
| Both workflows (add/remove), BR-1…BR-4, FR-01…FR-11, roles manager/viewer/anonymous, UI + API + model level, SQLite, Basic/session auth | transfer, count, serialization, merge, disassemble workflows (out of scope); purchase/sales/build orders; plugins; PostgreSQL/MySQL behaviour and true row locking (no server available — assumption A-4); OAuth2 token authentication; mobile/barcode UIs; i18n; ZAP **active** scanning (statement requires passive only); frontend unit tests |

## 4. Open defects (GitHub Issues; triage in `docs/DEFECTS.md`)
| ID | Issue | Title | Severity | Priority | Status |
|---|---|---|---|---|---|
| DEF-01 | [#1](https://github.com/IfBilal/inventree-stock-sqe-testing/issues/1) | Over-removal silently clamped (data loss) | Critical | P1 | Closed (fixed) |
| DEF-02 | [#2](https://github.com/IfBilal/inventree-stock-sqe-testing/issues/2) | Quantity 0 accepted as silent no-op | Medium | P2 | Open |
| DEF-03 | [#3](https://github.com/IfBilal/inventree-stock-sqe-testing/issues/3) | Resulting quantity overflow: item unreadable, stock list returns 500 | Critical | P1 | Open |
| DEF-04 | [#4](https://github.com/IfBilal/inventree-stock-sqe-testing/issues/4) | Malformed items (null/string/int) -> HTTP 500 | Medium | P2 | Open |
| DEF-05 | [#5](https://github.com/IfBilal/inventree-stock-sqe-testing/issues/5) | First login after server start silently fails | Medium | P3 | Open |
| DEF-06 | [#6](https://github.com/IfBilal/inventree-stock-sqe-testing/issues/6) | Concurrent adjustments fail with HTTP 500 (SQLite lock), ~20% at 5 users | High | P2 | Open |
| SEC-01 | [#7](https://github.com/IfBilal/inventree-stock-sqe-testing/issues/7) | No Content-Security-Policy header | Medium | P3 | Open |
| SEC-02 | [#8](https://github.com/IfBilal/inventree-stock-sqe-testing/issues/8) | Session cookie without SameSite (default config) | Low | P3 | Open |
| SEC-03 | [#9](https://github.com/IfBilal/inventree-stock-sqe-testing/issues/9) | react-router 6.30.6 advisories in the shipped bundle | Medium | P3 | Open |
| A11Y-01 | [#10](https://github.com/IfBilal/inventree-stock-sqe-testing/issues/10) | Item page: images without alt, no main landmark | Medium | P2 | Closed (fixed) |
| A11Y-02 | [#11](https://github.com/IfBilal/inventree-stock-sqe-testing/issues/11) | Remaining a11y issues (contrast, button names, ARIA) | Medium | P3 | Open |
| UX-01 | [#12](https://github.com/IfBilal/inventree-stock-sqe-testing/issues/12) | Enter in quantity field does not submit the dialog | Low | P3 | Open |

Pareto and root-cause analyses: `docs/DEFECTS.md`, `docs/RCA.md`. Reopen rate: 0 of 2 closed defects reopened (target ≤ 10 %).

## 5. Residual risk per risk (register `docs/RISK_REGISTER.md`; re-assessed from evidence)
| Risk | Initial L×I | Evidence-based residual L×I | Rationale | Linked defects |
|---|---|---|---|---|
| PR-01 | 25 | 1×5 = 5 | over-removal rejected after the fix; limit BVA at 3 levels; CBR-1 mutants 2/2 killed | DEF-01 (fixed), DEF-03 |
| PR-02 | 10 | 1×5 = 5 | access matrix 20/20; no side effect on denied calls; SameSite/CSP hardening open | SEC-01, SEC-02 |
| PR-03 | 12 | 1×4 = 4 | complete MCC 32/32 + MC/DC; CBR-2 mutants 5/5 killed | — |
| PR-04 | 12 | 4×3 = 12 (High) | zero accepted, overflow and malformed items still open | DEF-02, DEF-03, DEF-04 |
| PR-05 | 8 | 1×4 = 4 | atomicity verified at unit, API and recovery level | — |
| PR-06 | 12 | 2×4 = 8 (Medium) | recovery test: retry after failure is safe; no idempotency key remains (W-03) | — |
| PR-07 | 12 | 2×4 = 8 (Medium) | history read back after success and rejection; W-01, W-06 weaknesses | — |
| PR-08 | 9 | 5×3 = 15 (High) | measured: 19.5 % failures at 5 users on SQLite | DEF-06 |
| PR-09 | 8 | 3×2 = 6 (Medium) | one screen fixed (78→85); other findings open | A11Y-01/02, UX-01, DEF-05 |
| PR-10 | 12 | 2×4 = 8 (Medium) | backend 0/166; frontend moderate advisories open | SEC-03 |
| PJ-01 | 16 | 1×4 = 4 | all tools ran (SonarQube via zip, ZAP, k6, mutation, CI) | — |
| PJ-02 | 15 | 2×5 = 10 (High) | depends on the team preparing for the viva (`docs/VIVA_PREP.md`) | — |
| PJ-03 | 12 | 1×3 = 3 | full mutation run took 25 min on 5 workers | — |

## 6. Pull requests and pipeline evidence (from the GitHub API)
| PR | Title | Branch | State | Pipeline result |
|---|---|---|---|---|
| [#13](https://github.com/IfBilal/inventree-stock-sqe-testing/pull/13) | Fix DEF-01: reject removal larger than the available quantity (issue #1) | `fix/def-01-over-removal` | MERGED (merged) | hygiene: SUCCESS, unit: SUCCESS, api: SUCCESS, e2e: SUCCESS, mutation: SUCCESS, sonar: SUCCESS, gate: SUCCESS, deploy: SKIPPED |
| [#14](https://github.com/IfBilal/inventree-stock-sqe-testing/pull/14) | Allow adjusting stock items that are installed in another item | `bad/relax-adjustability-rule` | OPEN | hygiene: SUCCESS, unit: FAILURE, api: FAILURE, e2e: SUCCESS, mutation: FAILURE, sonar: SKIPPED, gate: SKIPPED, deploy: SKIPPED |
| [#15](https://github.com/IfBilal/inventree-stock-sqe-testing/pull/15) | a11y: alt text on item images and a main landmark on the stock item page (issue #10) | `fix/a11y-stock-item-page` | MERGED (merged) | hygiene: SUCCESS, unit: SUCCESS, api: SUCCESS, e2e: SUCCESS, mutation: SUCCESS, sonar: SUCCESS, gate: SUCCESS, deploy: SKIPPED |
| [#16](https://github.com/IfBilal/inventree-stock-sqe-testing/pull/16) | Remove redundant-looking tests (test_mutation_killers.py) | `bad/remove-mutation-killing-tests` | OPEN | hygiene: SUCCESS, unit: SUCCESS, api: SUCCESS, e2e: SUCCESS, mutation: FAILURE, sonar: SUCCESS, gate: SKIPPED, deploy: SKIPPED |

| Run | Event | Branch | Conclusion | Link |
|---|---|---|---|---|
| 44007547805 | push | `main` | success | https://github.com/IfBilal/inventree-stock-sqe-testing/actions/runs/44007547805 |
| 44007531207 | push | `main` | cancelled | https://github.com/IfBilal/inventree-stock-sqe-testing/actions/runs/44007531207 |
| 43952435670 | push | `main` | success | https://github.com/IfBilal/inventree-stock-sqe-testing/actions/runs/43952435670 |
| 43951957664 | push | `main` | cancelled | https://github.com/IfBilal/inventree-stock-sqe-testing/actions/runs/43951957664 |
| 43949292832 | push | `main` | cancelled | https://github.com/IfBilal/inventree-stock-sqe-testing/actions/runs/43949292832 |
| 43943448899 | pull_request | `fix/a11y-stock-item-page` | success | https://github.com/IfBilal/inventree-stock-sqe-testing/actions/runs/43943448899 |
| 43939159652 | push | `main` | success | https://github.com/IfBilal/inventree-stock-sqe-testing/actions/runs/43939159652 |
| 43938002471 | pull_request | `fix/a11y-stock-item-page` | success | https://github.com/IfBilal/inventree-stock-sqe-testing/actions/runs/43938002471 |
| 43937961734 | push | `main` | cancelled | https://github.com/IfBilal/inventree-stock-sqe-testing/actions/runs/43937961734 |
| 43933840489 | pull_request | `bad/remove-mutation-killing-tests` | failure | https://github.com/IfBilal/inventree-stock-sqe-testing/actions/runs/43933840489 |
| 43933792483 | push | `main` | cancelled | https://github.com/IfBilal/inventree-stock-sqe-testing/actions/runs/43933792483 |
| 43933770510 | push | `main` | cancelled | https://github.com/IfBilal/inventree-stock-sqe-testing/actions/runs/43933770510 |

## 7. Deviations from the plan and honest limitations
- SonarQube ran from the zip distribution (no Docker daemon on the machine; JDK 21, data on tmpfs); in CI it runs as a service container.
- mutmut 3.8 could not run on this Django project (evidence kept); an own AST runner with the standard and four custom operators was used (disclosed).
- Database: SQLite (no PostgreSQL available): concurrency results are specific to it (assumption A-4).
- Open defects other than DEF-01 were **logged and analysed but not fixed** (the statement requires one documented fix); this is the reason for HOLD.
- Effort: agent hours are logged; **human review hours must be filled in by the members** (`docs/EFFORT_NOTE.md`); commits are authored by the repository owner account — each member must commit their own work before submission (statement §6).
