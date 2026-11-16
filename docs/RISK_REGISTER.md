# RISK REGISTER — InvenTree Stock (Add/Remove)  · v0.3

Scale: Likelihood L (1 rare … 5 almost certain), Impact I (1 negligible … 5 severe). Score = L × I.
Level: **Critical ≥ 20**, **High 12–19**, **Medium 6–11**, **Low ≤ 5**. **Floor rule:** any risk with Impact = 5 is at least **High** (a single occurrence is unacceptable regardless of likelihood).
"Highest risks" in this project = Critical + High. Level decides technique and depth (table at the end; `docs/TEST_PLAN.md` §2).

| ID | Type | Risk | Cause / evidence | L | I | Score | Level | Mitigating technique and depth | Linked findings |
|---|---|---|---|---|---|---|---|---|---|
| PR-01 | Product | **Silent data loss**: removing more than available is clamped (not rejected); item may be deleted | Observed: remove 100 from 10 → 201, quantity 0 (`evidence/phase1/over_removal.txt`) | 5 | 5 | **25** | Critical | EP + 3-point BVA at unit/API/E2E; state transition; MCC on limit logic; mutation on limit operator; documented fix PR | DEF-01 (fixed, PR #13), DEF-03 |
| PR-02 | Product | Unauthorized role changes stock | Role check relies on default model permission for POST; viewer 403 observed | 2 | 5 | 10 → **High** (floor rule) | High | Access matrix, Playwright + API checks (≥ 4 decisions), source review of permission derivation | SEC-01, SEC-02 |
| PR-03 | Product | Non-adjustable items (customer, installed, consumed, sales order) are adjusted | `validate_pk` 5-condition decision (BR-2), V(G)=6 (`docs/STATIC_ANALYSIS.md`) | 3 | 4 | 12 | High | Decision table, **complete MCC (32 rows) + MC/DC pairs**, 6 basis-path tests, unit + API | — |
| PR-04 | Product | Invalid quantities accepted: zero, overflow of resulting quantity | Observed: 0 → 201 no-op; add 9 999 999 999.99999 to 10 → 500 on read (`evidence/phase1/over_removal.txt`) | 4 | 3 | 12 | High | EP + 3-point BVA from generated data on every input; resulting-quantity boundary | DEF-02, DEF-03, DEF-04 |
| PR-05 | Product | Partial multi-item update (non-atomic) | `transaction.atomic`; verified atomic for invalid item | 2 | 4 | 8 | Medium | API integration with mixed valid/invalid items + read-back | — |
| PR-06 | Product | Duplicate processing of repeated/retried requests | No idempotency key; retry after failure | 3 | 4 | 12 | High | Recovery test with test double + retry, assert 0 duplicates; repeated-request API test | W-03 |
| PR-07 | Product | History (audit) entry missing or inconsistent with quantity | `AuditLogEntry` written by `tracking_event` in a separate step | 3 | 4 | 12 | High | Read-back of history after success AND rejection (API + E2E) | W-01, W-06 |
| PR-08 | Product | Performance degradation/failures under concurrent adjustment | SQLite write locks; `select_for_update` not a row lock on SQLite | 3 | 3 | 9 | Medium | k6 1 vs 5 users, p95 + failure %, recovery test | DEF-06 |
| PR-09 | Product | Accessibility defects in stock dialogs | React UI, third-party components | 4 | 2 | 8 | Medium | Lighthouse + axe-core, keyboard test, before/after fix | DEF-05, A11Y-01 (fixed, PR #15), A11Y-02, UX-01 |
| PR-10 | Product | Vulnerable dependencies | Large Python/JS dependency tree (`requirements.txt` pinned) | 3 | 4 | 12 | High | pip-audit + yarn audit, record packages/versions | SEC-03 |
| PJ-01 | Project | Tooling/disk constraints (SonarQube, ZAP, k6, mutation) | Measured: 5 GB free; SonarQube needed JDK 21 + tmpfs (Docker daemon unavailable) | 4 | 4 | 16 | High | Run tools sequentially; export evidence right after each run; tmpfs for Sonar data | — |
| PJ-02 | Project | Team cannot explain AI-assisted work in the viva | Viva rule: unexplained component → zero | 3 | 5 | 15 | High | Per-member viva sheets, owner reruns tests, ownership by area | — |
| PJ-03 | Project | Mutation testing too slow on Django project | mutmut reruns tests per mutant | 4 | 3 | 12 | High | Mutate only business-rule functions, fast DB tests, parallel workers | — |

Counts: 10 product, 3 project risks. **Critical 1** (PR-01), **High 9** (PR-02, PR-03, PR-04, PR-06, PR-07, PR-10, PJ-01, PJ-02, PJ-03), **Medium 3** (PR-05, PR-08, PR-09), Low 0.

## 5 × 5 matrix (IDs at L,I; level colouring by score)
| L \ I | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| **5** | | | | | **PR-01** |
| **4** | | PR-09 | PR-04, PJ-03 | PJ-01 | |
| **3** | | | PR-08 | PR-03, PR-06, PR-07, PR-10 | PJ-02 |
| **2** | | | | PR-05 | PR-02 |
| **1** | | | | | |

## Basis for L and I values
| ID | Likelihood basis | Impact basis |
|---|---|---|
| PR-01 | 5: defect is **present** in the baseline (observed, 100 % reproducible) | 5: silently destroys stock data; audit entry records the clamped amount |
| PR-02 | 2: permission check exists and viewer got 403 (`evidence/phase1/roles.txt`); residual doubt: permission derived implicitly | 5: unauthorized stock change |
| PR-03 | 3: complex 5-condition decision, only `belongs_to` branch exercised so far | 4: stock assigned to a customer altered → inventory/finance error |
| PR-04 | 4: two input defects already observed | 3: wrong quantities or 500 errors; recoverable |
| PR-05 | 2: atomicity verified for two invalid-item cases | 4: inconsistent stock |
| PR-06 | 3: no idempotency mechanism by design | 4: double adjustment |
| PR-07 | 3: history written separately from quantity update | 4: audit trail unreliable |
| PR-08 | 3: SQLite single-writer | 3: slow/failed requests, no data loss |
| PR-09 | 4: custom React forms commonly lack labels/focus handling | 2: usability, not data integrity |
| PR-10 | 3: many pinned third-party packages | 4: depends on exploitability |
| PJ-01 | 4: disk already at 92 % | 4: tooling cannot run → missing evidence |
| PJ-02 | 3: AI-assisted work volume | 5: component marks reduced to zero |
| PJ-03 | 4: mutmut on Django is slow | 3: schedule slip |

## Tracking (re-assessed from evidence, v0.3 — see `docs/COMPLETION_REPORT.md` §5)
| ID | Owner | Status | Residual L×I (evidence) | Basis |
|---|---|---|---|---|
| PR-01 | M1 | **Mitigated** — DEF-01 fixed in PR #13 (unit, API, E2E verified); DEF-03 related and still open | 1×5 | limit BVA at 3 levels, CBR-1 mutants 2/2 killed |
| PR-02 | M3 | **Mitigated** — access matrix 20/20, denied calls leave no trace; CSP/SameSite open (SEC-01/02) | 1×5 | `docs/SECURITY.md` |
| PR-03 | M1 | **Mitigated** — complete MCC 32/32, MC/DC, 6 basis paths | 1×4 | CBR-2 mutants 5/5 killed |
| PR-04 | M2 | **Open (High)** — DEF-02, DEF-03, DEF-04 confirmed and open | 4×3 | strict-xfail tests |
| PR-05 | M2 | **Mitigated** — atomicity verified (unit, API, recovery) | 1×4 | `test_recovery.py` |
| PR-06 | M3 | **Reduced** — retry after failure is safe (recovery test); no idempotency key (W-03) | 2×4 | `docs/PERFORMANCE.md` §6 |
| PR-07 | M2 | **Reduced** — history read back after success and rejection; W-01, W-06 | 2×4 | API tests |
| PR-08 | M3 | **Materialised → High** — 19.5 % failures at 5 users (DEF-06) | 5×3 | k6 runs |
| PR-09 | M3 | **Reduced** — one screen fixed (78→85); others open | 3×2 | `docs/ACCESSIBILITY.md` |
| PR-10 | M3 | **Reduced** — backend 0/166; frontend moderate advisories (SEC-03) | 2×4 | audits |
| PJ-01 | M1 | **Closed** — all tools ran | 1×4 | — |
| PJ-02 | all | **Open** — viva guide written (`docs/VIVA_PREP.md`); depends on the team | 2×5 | — |
| PJ-03 | M1 | **Closed** — full mutation run 25 min on 5 workers | 1×3 | `docs/MUTATION.md` |

## Technique/depth by risk level (see TEST_PLAN §2)
| Level | Minimum techniques | Depth |
|---|---|---|
| Critical | EP, 3-point BVA, state transition, decision table, **MCC + MC/DC**, mutation, E2E, CI regression gate | every input and rule, all levels, blocks release |
| High | EP, BVA, decision table; **MCC + MC/DC where the risk is a multi-condition decision (PR-03)**; read-back; tool audits (PR-10) | all inputs of the area, ≥ 2 levels where data integrity is involved |
| Medium | EP/BVA at API or tool scan | representative, tool-based |
| Low | smoke only | — |
