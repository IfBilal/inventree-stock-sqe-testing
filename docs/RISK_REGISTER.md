# RISK REGISTER — InvenTree Stock (Add/Remove)

Scale: Likelihood L (1 rare … 5 almost certain), Impact I (1 negligible … 5 severe). Score = L × I. Level: **Critical ≥ 20**, **High 12–19**, **Medium 6–11**, **Low ≤ 5**.
Level decides technique and depth (see `docs/TEST_PLAN.md` §4).

| ID | Type | Risk | Cause / evidence | L | I | Score | Level | Mitigating technique and depth | Linked findings |
|---|---|---|---|---|---|---|---|---|---|
| PR-01 | Product | **Silent data loss**: removing more than available is clamped (not rejected) and the item may be deleted | Observed on baseline: remove 100 from 10 → 201, item deleted (`take_stock`: `min(quantity, self.quantity)`) | 5 | 5 | **25** | Critical | BVA (below/at/above limit) at unit + API + E2E; state transition; MCC on limit logic; mutation on limit operator; documented fix PR | DEF-01 |
| PR-02 | Product | Unauthorized role changes stock | Role-based `stock.add` check only | 2 | 5 | 10 | Medium | Access matrix, Playwright + API checks (≥4 decisions), source review | — |
| PR-03 | Product | Non-adjustable items (customer, installed, consumed, sales order) are adjusted | `validate_pk` multi-condition decision (BR-2) | 3 | 4 | 12 | High | Decision table, complete MCC then MC/DC pairs, unit + API | — |
| PR-04 | Product | Invalid quantities accepted (0, negative, over-precision, > max) | `min_value=0` allows 0; silent no-op with 201 | 4 | 3 | 12 | High | EP + 3-point BVA from generated data on every input | DEF-02 (if confirmed) |
| PR-05 | Product | Partial multi-item update (non-atomic) | `transaction.atomic` but validation per item | 2 | 4 | 8 | Medium | API integration with mixed valid/invalid items, read-back | — |
| PR-06 | Product | Duplicate processing of repeated/retried requests (double adjustment) | No idempotency key; retry after failure | 3 | 4 | 12 | High | Recovery test with test double + retry, assert no duplicates; repeated request test | — |
| PR-07 | Product | History (tracking) entry missing or inconsistent with quantity | `tracking_event` in separate step | 3 | 4 | 12 | High | Read-back of history after success AND rejection (API + E2E) | — |
| PR-08 | Product | Performance degradation/failures under concurrent adjustment (SQLite write locks) | `select_for_update` no-op on SQLite | 3 | 3 | 9 | Medium | k6 1 vs 5 users, p95 + failure %, recovery test | — |
| PR-09 | Product | Accessibility defects in stock dialogs (labels, focus order, contrast) | React UI | 4 | 2 | 8 | Medium | Lighthouse + axe-core, keyboard test, before/after fix | — |
| PR-10 | Product | Vulnerable dependencies | Large Python/JS dependency tree | 3 | 4 | 12 | High | pip-audit + OWASP Dependency-Check, record packages/versions | — |
| PJ-01 | Project | Tooling and disk/CPU constraints (SonarQube, ZAP, k6, mutation on 5 GB free disk) | Measured: 5.1 GB free after UI build | 4 | 4 | 16 | High | Docker image cleanup, scope mutation to business module, sequential runs | — |
| PJ-02 | Project | Team cannot explain AI-assisted work in the viva | Viva rule: unexplained component → zero | 3 | 5 | 15 | High | Per-member viva sheets, owner reruns tests, ownership by area | — |
| PJ-03 | Project | Mutation testing too slow on Django project | mutmut regenerates and reruns tests per mutant | 4 | 3 | 12 | High | Mutate only business-rule functions, fast DB tests, parallel workers | — |

## 5 × 5 matrix (IDs placed at L,I)
| L \ I | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| **5** | | | | | **PR-01** |
| **4** | | PR-09 | PR-04, PJ-03 | PJ-01 | |
| **3** | | | PR-08 | PR-03, PR-06, PR-07, PR-10 | PJ-02 |
| **2** | | | | PR-05 | PR-02 |
| **1** | | | | | |

Counts: 10 product risks, 3 project risks. Critical: 1 (PR-01), High: 8 (PR-03, PR-04, PR-06, PR-07, PR-10, PJ-01, PJ-02, PJ-03), Medium: 4 (PR-02, PR-05, PR-08, PR-09), Low: 0.

## Technique/depth by risk level
| Level | Minimum techniques | Depth |
|---|---|---|
| Critical | EP, 3-point BVA, state transition, decision table, MCC + MC/DC, mutation, E2E, regression gate in CI | every input and rule, all levels, blocks release |
| High | EP, BVA or decision table, API + unit, read-back | all inputs of the area, one level plus read-back |
| Medium | EP/BVA at API or tool scan | representative, tool-based |
| Low | smoke only | — |
