# CI QUALITY GATE (Phase 12) — GitHub Actions on every pull request
Workflow: `.github/workflows/quality-gate.yml` (runs on every **pull request** to `main` and on every push to `main`). Repository: https://github.com/IfBilal/inventree-stock-sqe-testing — Actions: https://github.com/IfBilal/inventree-stock-sqe-testing/actions

## Gates (all required; branch protection on `main` requires every check, `strict` = branch must be up to date)
| Job (required check) | What it runs | Blocks when | Threshold and justification |
|---|---|---|---|
| `hygiene` | `tools/check_no_escape_hatches.py` | any `continue-on-error`, `\|\| true`, `\|\| exit 0`, `set +e`, `if: always()` in the workflows and CI scripts | **0 escape hatches** — the project statement forbids them; the check itself found two `\|\| true` in our own scripts during development and they were removed |
| `unit` | `scripts/coverage_unit.sh` (pytest + coverage.py branch mode) and `tools/scope_coverage.py`; generator tests | any failing test; any in-scope function with an uncovered **statement** or an **unjustified** uncovered branch | **100 % statements and 0 unjustified branches** of the 31 in-scope functions — the statement requires 100 %/100 %; the single unreachable branch is defended in `docs/COVERAGE_JUSTIFICATION.md` and in `JUSTIFIED` of the tool |
| `api` | `scripts/test_api.sh api` — live server, generated EP/BVA (223 cases), business rules, weaknesses, response-schema validation of every response | any failing test, any strict-xfail that unexpectedly passes | all tests pass; defects are pinned by strict xfail so that a fix forces removal of the marker (this is what makes PR #13 "red before, green after") |
| `e2e` | builds the UI, Playwright (30 use-case flows + usability + access matrix) | any failing test, any `test.fail` that unexpectedly passes | all pass |
| `sonar` | SonarQube Community Build started as a service container, scanner with the coverage report, `tools/sonar_gate.py` | bugs ≠ 0, vulnerabilities ≠ 0, security hotspots ≠ 0, code smells > 0, any rating worse than A, **whole-module coverage < 38 %**, duplication > 1 % | baseline measured 0/0/0/0, ratings A, duplication 0.6 %; **coverage 38 %** because the whole-module figure is 40.2 % (the module contains out-of-scope merge/disassemble code); 2 points of tolerance catch a real regression without flapping. In-scope logic is gated separately at 100 % by `unit` |
| `mutation` | isolated runner on a deterministic sample (3 workers, 7 mutants per function, all custom operators kept) and `tools/mutation_gate.py` | adjusted mutation score < **90 %** | final full-set adjusted score 100 % (raw 93.9 %, round 1 was 88.9 %); 90 % separates the improved suite from the pre-improvement one and leaves tolerance for sampling; every non-equivalent survivor counts against the score (`docs/MUTATION.md` §6) |
| `gate` | depends on all of the above (no `if: always()`) | any of the above failed or was skipped | — |
| `deploy` | on push to `main` only, `needs: gate`, environment `release`: builds the release-candidate bundle (docs, evidence, reports) | `gate` not green → **not executed** | deployment is impossible without a green gate |

## Merge and deployment are blocked
- **Merge:** branch protection on `main` (`gh api repos/IfBilal/inventree-stock-sqe-testing/branches/main/protection`): required status checks `hygiene, unit, api, e2e, sonar, mutation, gate`, `strict: true`, no force-push, no deletion.
- **Deployment:** the `deploy` job `needs: [gate]`; a red gate skips it.
- **No escape hatches:** enforced by the `hygiene` job on every run (and a local run in `scripts/`).

## Evidence of the required pull requests
| Requirement | Pull request | Evidence |
|---|---|---|
| **One documented fix that fails before and passes after** | **PR #13** "Fix DEF-01: reject removal larger than the available quantity" (closes issue #1). Commit 1 changes only the tests (defect still present) → pipeline **red**; commit 2 adds the fix → pipeline **green** | run links and results in the table below (generated from the GitHub API) |
| **One pull request the pipeline blocked** | **PR #14** "Relax the removal limit to 110 % of the available quantity" — a deliberate rule change that violates BR-1 / FR-07; the pipeline fails it (unit, api, e2e, mutation) and the PR cannot be merged | run link and the list of failing jobs below |
| Accessibility fix | PR "a11y: alt text and main landmark on the stock item page" (branch `fix/a11y-stock-item-page`), see `docs/ACCESSIBILITY.md` | passes the pipeline |
