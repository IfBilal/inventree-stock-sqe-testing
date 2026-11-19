# AREA OWNERSHIP (per member) — rerun and explain in your own words
The viva checks every component: each member reruns a selected test and explains its assertions; a live task changes a business rule or an API spec and asks you to predict which tests and which pipeline gate fail, make the change and show the result. **If you cannot explain a component, its marks can drop to zero.** Everything below is reproducible from a clean clone: `scripts/install.sh`, then the commands shown.

## Common ground (all members)
- **System:** InvenTree 1.8.0 dev, Stock module. **Workflows:** WF-A Add stock, WF-B Remove stock; **shared record:** `StockItem.quantity` (`docs/TEST_BASIS.md`).
- **Rules:** BR-1 limits (0 < N ≤ max; removal ≤ available), BR-2 adjustability (5 conditions), BR-3 deletion on depletion, BR-4 role permission. **Roles:** `stock_manager` (view/add/change/delete), `stock_viewer` (view only).
- **Reset/start:** `scripts/reset.sh` then `scripts/start.sh`; accounts `admin/admin12345`, `manager/manager12345`, `viewer/viewer12345`.
- **Defects found:** DEF-01…06, SEC-01…03, A11Y-01/02, UX-01 (`docs/DEFECTS.md`); release decision **HOLD** (`docs/COMPLETION_REPORT.md`).
- **AI use:** AI tooling was used and is disclosed in `docs/AI_USE_RECORD.md` — you are responsible for everything submitted.

## Member 1 — 24I-3166 — Area 1: static analysis, white-box, mutation, CI
| Topic | Rerun | Be ready to explain |
|---|---|---|
| SonarQube + hand CFG | `scripts/sonar_scan.sh` (server per `docs/STATIC_ANALYSIS.md`) | each metric; V(G)=6 for `validate_pk` (E−N+2 = 14−10+2); why Sonar says 5 (it does not count `elif`) |
| Unit tests + coverage | `scripts/coverage_unit.sh` | what "in scope" means (`tools/scope_coverage.py SCOPE`, 33 functions), why 100 %/99–100 %, the single justified branch |
| MCC / MC/DC | `python tools/mcdc.py`; `scripts/test_unit.sh unit/test_validate_pk_mcc.py` | BR-2 truth table (32 rows), independence pairs, minimal set {1,2,3,5,9,18}; masked conditions |
| Mutation | `python tools/mutate.py --only stock/models.py::StockItem.take_stock` | operators (standard + 4 custom CBR-1…4), surviving/equivalent mutants (`docs/MUTATION.md`), how mutmut was set up (`scripts/mutmut_run.sh`, newline lists, migrated DB) and why the custom operators need our own runner |
| CI | `.github/workflows/quality-gate.yml`, `docs/CI_QUALITY_GATE.md` | each gate, thresholds and why, the blocked PR and the fix PR |
**Live-task playbook (business-rule change):** e.g. "removal limit becomes 90 % of available" → predicted failures: unit `test_boundaries.py` (limit BVA), `test_mcc_other_decisions.py` BR1 rows, API generated `limit-*` cases, E2E UC02/UC03/UC06, and the **mutation gate** if surviving mutants appear; coverage gate if the new branch is not covered. Make the change in `StockRemoveSerializer.validate`, rerun `scripts/coverage_unit.sh` and show which test goes red.

## Member 2 — 24I-3015 — Area 2: API testing and test-data generation
| Topic | Rerun | Be ready to explain |
|---|---|---|
| OpenAPI contract | open `openapi/stock.yaml`; validate: `python -c "from openapi_spec_validator import validate_spec;import yaml;validate_spec(yaml.safe_load(open('openapi/stock.yaml')))"` | why we wrote our own spec (InvenTree's allows negatives, no bounds), `x-` extensions |
| Generator | `python tools/gen_testdata.py openapi/stock.yaml -o /tmp/t.json`; `scripts/test_unit.sh generator` | EP classes vs 3-point BVA, one mutation per case, grid snapping, exact decimals |
| Regeneration demo | `scripts/gen_demo.sh` | what changes when `maximum` or `notes.maxLength` or `exclusiveMinimum` or `minItems` changes (16 and 8 cases) |
| API tests | `scripts/test_api.sh api` (13 min) or one case: `scripts/test_api.sh "api/test_generated_ep_bva.py -k limit-above"` | read-back after success and rejection, atomicity, repeated requests, weaknesses W-01…W-13, API coverage criteria (`docs/API_COVERAGE.md`) |
**Live-task playbook (updated API spec):** edit `openapi/stock.yaml` (e.g. `quantity.maximum: 1000`), run `scripts/gen_demo.sh`/`python tools/gen_testdata.py`, state which generated cases change, run `API_SPEC=<file> scripts/test_api.sh api/test_generated_ep_bva.py`: the server still accepts 1000.00001? (it rejects only above 9999999999.99999) → the `max-above` case **fails** because the contract is stricter than the implementation.

## Member 3 — 24I-3106 — Area 3: use cases, usability, accessibility, security, performance
| Topic | Rerun | Be ready to explain |
|---|---|---|
| Use cases + Playwright | `scripts/test_e2e.sh` (3 min) or `cd tests/team && npx playwright test e2e/uc06_correct_rejected.spec.ts` | the 6 use cases, flows, how the flows that failed on the baseline (DEF-01, DEF-02) were marked until the fixes (PR #13, #17); today no flow is an expected failure |
| Usability + keyboard | `UC06-MAIN`, `UC06-AF2` | error message explains the correction; focus order; UX-01 (Enter does not submit) |
| Lighthouse + axe | `node a11y/lighthouse_run.mjs after`, `A11Y_PHASE=after npx playwright test e2e/a11y.spec.ts`, `python tools/a11y_report.py` | dedup rule (both tools = once), the fix (alt + main), before/after 78 → 85 |
| Security | `npx playwright test e2e/access.spec.ts`; ZAP/pip-audit in `docs/SECURITY.md` | access matrix (20 decisions), passive-only ZAP, cookie attributes, why csrftoken is not HttpOnly, dependency findings |
| Performance | `scripts/perf_run.sh` (9 min) | limits declared first, p95, 1 vs 5 users, the baseline 19.5 % failures = SQLite lock and the IMMEDIATE-transaction fix (PR #18, 0 % failures), why p95 is still 545–556 ms (EC-3 not met), Basic vs token authentication, recovery test |
**Live-task playbook:** change the deplete rule (BR-3) e.g. `delete_on_deplete` default → predicted failures: UC03-AF1/MAIN, API `test_depletion_*`, unit BR3 MCC rows; the pipeline gates `unit`, `api`, `e2e`, `mutation` (custom operator CBR-3).

## Test management (shared)
Plan/risks/estimates: `docs/TEST_PLAN.md`, `docs/RISK_REGISTER.md`; traceability (generated): `docs/TRACEABILITY.md`; defects/RCA: `docs/DEFECTS.md`, `docs/RCA.md`; weekly reports: `reports/weekly/`; completion report: `docs/COMPLETION_REPORT.md`.

## Personal verification checklist (each member ticks only what they have really done)
The AI assistant produced and ran most of the material; **you** must be able to explain and re-run your area.
| Item | M1 24I-3166 | M2 24I-3015 | M3 24I-3106 |
|---|---|---|---|
| I re-ran my area's commands from the tables above and saw the same results | ☐ | ☐ | ☐ |
| I can explain every assertion of two tests of my area | ☐ | ☐ | ☐ |
| I did a timed dry run of my live-task playbook (change → predicted failures → rerun) | ☐ | ☐ | ☐ |
| I confirmed or corrected my share of the human review hours (`docs/EFFORT_LOG.csv`) | ☐ | ☐ | ☐ |
| I can defend two or three mutation equivalence arguments (`docs/MUTATION.md` §5) | ☐ | ☐ | ☐ |

## Single-case commands for the live task (fast enough to demo)
- Unit: `scripts/test_unit.sh unit/test_boundaries.py` (seconds); `python tools/mcdc.py | head -60`; `python tools/mutate.py --only stock/models.py::StockItem.take_stock` (a few minutes).
- API: `scripts/test_api.sh "api/test_generated_ep_bva.py -k limit-above"`. Spec edit: change `quantity.maximum` in a copy of `openapi/stock.yaml`, run `python tools/gen_testdata.py <copy> -o /tmp/t.json` and compare with `evidence/generator/testdata_before.json` (`scripts/gen_demo.sh` does this for two constraints: 16 and 8 cases change); the `max-*` cases move, and a server that was not changed still fails `max-above` of the new limit.
- Browser: `cd tests/team && npx playwright test e2e/uc03_deplete_item.spec.ts` (about 40 s).
- Performance: after `scripts/reset.sh` and `scripts/start.sh`, `VUS=5 k6 run --duration 20s tests/team/perf/remove_stock.js` (a short run; the full protocol `scripts/perf_run.sh` takes 9 minutes).
