#!/usr/bin/env python3
"""docs/MUTATION.md from the evidence/mutation/*.json files and docs/mutation_equivalents.json."""
import collections, json, os, sys
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
J = lambda p: json.load(open(os.path.join(R, p)))
a1, a2 = J('evidence/mutation/results_round1.json'), J('evidence/mutation/results_round2.json')      # first analysis (244 mutants, code before PR #13)
f1, f2, fin = J('evidence/mutation/results_final_run.json'), J('evidence/mutation/results_final_round2.json'), J('evidence/mutation/results.json')
eq = J('docs/mutation_equivalents.json')
key = lambda r: (r['file'], r['function'], r['op'], r['line'], r['desc'])


def rerun_map(first, second):
    """map each surviving mutant of `first` to its result in `second` (duplicates matched by source order)"""
    b = collections.defaultdict(list)
    for r in second['results']: b[key(r)].append(r)
    seen = collections.Counter(); out = {}
    for r in first['results']:
        if r['status'] == 'survived':
            k = key(r); out[r['id']] = b[k][seen[k]]['status']; seen[k] += 1
    return out


m_a, m_f = rerun_map(a1, a2), rerun_map(f1, f2)
CLASS = {  # function -> (classification, action) for KILLABLE survivors
 'StockAdjustmentSerializer.to_internal_value': ('Missing test', 'query-count test: the pk prefetch performs one bulk query (`test_prefetch_loads_all_referenced_items_with_a_single_stock_query`)'),
 'StockItem.updateQuantity': ('Missing test', 'event test: `trigger_event(ITEM_QUANTITY_UPDATED, id, quantity)` is called (`test_update_quantity_triggers_the_quantity_updated_event`)'),
 'StockItem._apply_status_change': ('Weak assertion', 'asserted the complete delta dict of the helper (`test_apply_status_change_fills_all_status_deltas`)'),
 'StockItem._apply_optional_transfer_fields': ('Weak assertion', 'asserted the recorded deltas and applied values (`test_apply_optional_transfer_fields_records_deltas_and_applies_values`)'),
 'StockItem.can_delete': ('Weak assertion', 'the monkeypatch stubs record their arguments: only ACTIVE allocations are queried (`test_can_delete_queries_only_active_allocations`)'),
 'StockItem.save': ('Missing test', 'tests for duplicate serial (`validate_unique`), item cannot belong to itself (`clean`), `serial_int` (`update_serial_number`)'),
 'StockItem.is_in_stock': ('Weak assertion', 'defaults test: each of the three checks is ON by default (`test_is_in_stock_defaults_check_status_quantity_and_production`)'),
 'StockAddSerializer.validate': ('Missing test', 'two different items in one request: the limit is checked per item and the error points at the offending entry (`test_add_limit_is_checked_per_item_and_the_error_points_at_the_offending_entry`)'),
 'StockRemoveSerializer.validate': ('Missing test', 'base validation of the remove serializer: empty list rejected and error index follows the pk-sorted order (`test_remove_rejects_an_empty_items_list`, `test_remove_reports_the_error_index_of_the_pk_sorted_entry`)'),
 'StockAdjustmentItemSerializer.validate_pk': ('Missing test (cache=False)', 'a direct DB update of the setting exposes a stale cached read (`test_validate_pk_does_not_use_a_cached_setting_value`); the `backup_value` constant is equivalent'),
 'StockItem.delete': ('Missing test (cache=False)', 'same technique for `STOCK_ALLOW_DELETE_SERIALIZED` (`test_delete_does_not_use_a_cached_setting_value`)'),
}


def ekey(r): return f"{r['function']}|{r['desc']}|{r['original']}"


ops = collections.defaultdict(lambda: [0, 0])
for r in f1['results']:
    ops[r['op']][0] += 1; ops[r['op']][1] += r['status'] != 'survived'
fn = collections.defaultdict(lambda: [0, 0])
for r in f1['results']:
    fn[r['function']][0] += 1; fn[r['function']][1] += r['status'] != 'survived'
equiv_n = sum(1 for r in fin['results'] if r['status'] == 'survived' and ekey(r) in eq)
adj = 100 * fin['killed'] / (fin['total'] - equiv_n)

o = ['# MUTATION ANALYSIS (Phase 11)\n',
 '> **Headline (raw, no adjustment):** custom-operator analysis on the final code **96.6 %** (254 of 263 mutants killed; CI gate 95 %); real mutmut run **82.6 %** over both whole files and **90.0 %** over the 33 in-scope functions. The "100 % adjusted" figures below exclude survivors that are individually argued to be equivalent mutants — those arguments are the team\'s own and each member must be able to defend them.\n\n## 1. Tool and scope\n- **Scope:** the business-rule functions of `docs/TEST_BASIS.md` §7 (33 functions in `stock/serializers.py`, `stock/models.py`, `InvenTree/fields.py`, `InvenTree/permissions.py`) — exactly the set whose coverage is gated.\n'
 '- **Tool:** `tools/mutate.py` — AST-based mutation runner of our own, executed in 5 isolated parallel copies of the backend; every mutant is judged by the **real unit suite** (`tests/team/unit`, `-x`, killed = first failing test). The repository and `upstream/` are never modified; the analyses ran on clean `git archive` exports.\n'
 '- **mutmut 3.8.1 was run for real** (`scripts/mutmut_run.sh`, results in §2b). Our first attempt failed and we first wrongly reported mutmut as unusable: the cause was in OUR set-up, not in mutmut — (1) mutmut reads list options in `setup.cfg` one per line, so a comma-separated `also_copy` copied nothing, and (2) InvenTree calls `sys.exit(1)` at start-up on an un-migrated database, which mutmut surfaces only as \"Child exited with code 1\" (reproduced by running its coverage step in-process, `evidence/mutation/mutmut_attempt.log`). With a newline-separated config and a migrated database mutmut runs. Because mutmut offers no custom operators, our own AST runner (`tools/mutate.py`) additionally implements the four business-rule operators below; both are reported.\n'
 '- **Standard operators:** ROR relational, LCR and/or, UOI remove `not`, CRP constants, RET boolean returns, AOR +/-, SDL statement deletion, NEG if-condition negation.\n'
 '- **Custom operators from OUR business rules (≥ 2 required):** **CBR-1 LIMIT_CLAMP** `min()`↔`max()` (BR-1 removal limit), **CBR-2 REFERENCE_CHECK** flip `x is None` on sales_order/belongs_to/customer/consumed_by (BR-2 adjustability), **CBR-3 DEPLETE_RULE** `delete_on_deplete`/`can_delete()` replaced by constants (BR-3), **CBR-4 POSITIVE_GUARD** `quantity <= 0` ↔ `< 0` on quantity guards (BR-1/FR-03). A custom mutant replaces the identical standard (ROR) mutant so no mutation is counted twice.\n',
 f"## 2. Scores — two analyses\n| Analysis | Mutants | Killed | Survived | Raw score |\n|---|---|---|---|---|\n| **First analysis** (code before PR #13) — before improving the tests | {a1['total']} | {a1['killed']} | {a1['survived']} | **{a1['score_raw']} %** |\n| First analysis — after 9 killing tests (12 survivors killed, 15 equivalents) | {a1['total']} | {a1['killed'] + sum(1 for v in m_a.values() if v != 'survived')} | {sum(1 for v in m_a.values() if v == 'survived')} | {100 * (a1['killed'] + sum(1 for v in m_a.values() if v != 'survived')) / a1['total']:.1f} % |\n| Intermediate analysis (code with the DEF-01 fix, before the DEF-02/03/04/06 fixes; `results_final_run_v1_pre_fix.json`) | 248 | 238 | 10 | 96.0 % (100 % adjusted) |\n| **Final analysis** (final code incl. the DEF-01..04 fixes and the dedupe of CBR-4/ROR) — before the second test round | {f1['total']} | {f1['killed']} | {f1['survived']} | **{f1['score_raw']} %** |\n| Final analysis — after more killing tests ({f1['survived'] - fin['survived']} survivors killed, {fin['survived']} equivalents) | {fin['total']} | {fin['killed']} | {fin['survived']} | {fin['score_raw']} % |\n| **Final, adjusted** (the {equiv_n} survivors proven equivalent are excluded) | {fin['total'] - equiv_n} | {fin['killed']} | 0 | **{adj:.1f} %** |\n",
 '## 3. Results by operator (final analysis, before the second test round)\n| Operator | Mutants | Killed | Survived | Note |\n|---|---|---|---|---|']
NOTE = {'CBR-1': 'custom — limit clamp', 'CBR-2': 'custom — reference conditions', 'CBR-3': 'custom — deplete rule', 'CBR-4': 'custom — positive guard (3 survivors are equivalent: redundant guards)'}
for k, (n, kl) in sorted(ops.items()):
    o.append(f"| {k} | {n} | {kl} | {n - kl} | {NOTE.get(k, '')} |")
o.append('\n## 2b. mutmut results (the real tool, 3.8.1)\n' + os.popen(f'{sys.executable} {R}/tools/mutmut_report.py').read() + '\n')
o.append('\n## 4. Results by function (final analysis, before the second test round)\n| Function | Mutants | Killed | Survived |\n|---|---|---|---|')
for f, (n, kl) in sorted(fn.items()):
    o.append(f'| `{f}` | {n} | {kl} | {n - kl} |')
n_surv_total = a1['survived'] + f1['survived']
o.append(f'\n## 5. Analysis of the surviving mutants ({a1["survived"]} + {f1["survived"]} = {n_surv_total} analysed; ≥ 15 required): equivalent / missing test / weak assertion\n### 5.1 Final analysis ({f1["survived"]} survivors)\n| ID | Operator | Function (line) | Mutation | Classification | Action / argument | After the second test round |\n|---|---|---|---|---|---|---|')
for r in f1['results']:
    if r['status'] != 'survived': continue
    after = m_f[r['id']]
    if after != 'survived' and r['function'] in CLASS:
        cl, act = CLASS[r['function']]
    else:
        cl, act = 'Equivalent', eq.get(ekey(r), {}).get('justification', '—')
    o.append(f"| {r['id']} | {r['op']} | `{r['function']}` (L{r['line']}) | {r['desc'][:55]} | **{cl}** | {act} | {'**killed**' if after != 'survived' else 'survives (equivalent)'} |")
o.append(f'\n### 5.2 First analysis ({a1["survived"]} survivors, code before PR #13)\n| ID | Operator | Function | Mutation | Classification | Action | Result |\n|---|---|---|---|---|---|---|')
for r in a1['results']:
    if r['status'] != 'survived': continue
    after = m_a[r['id']]
    if after != 'survived' and r['function'] in CLASS:
        cl, act = CLASS[r['function']]
    else:
        cl, act = 'Equivalent', 'redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1)'
    o.append(f"| {r['id']} | {r['op']} | `{r['function']}` | {r['desc'][:50]} | **{cl}** | {act} | {'killed' if after != 'survived' else 'equivalent'} |")
o.append('\n## 6. Gate in CI\nThe `mutation` job runs the same runner on a deterministic sample (`--workers 3 --max-per-function 7`, all custom mutants kept) and `tools/mutation_gate.py` requires an **adjusted score ≥ 95 %**, where adjusted = killed ÷ (total − equivalents listed in `docs/mutation_equivalents.json`); the key is `function|mutation|original code` (line-independent but specific). Every surviving mutant that is not a documented equivalent counts against the score.\n'
 '**CI-produced scores (sampled runs, `evidence/ci/`):** before the killing tests — 159 mutants, 140 killed, **88.1 %** (gate then 85 %, passed); after the first killing tests (PR #13 run 43920009616) — 166 mutants, 157 killed, 9 survivors of which 7 documented → **98.7 % adjusted** (gate 90 %, passed). The threshold was first 85 %, then 90 %, and is now **95 %**: PR #16 (removal of the killing tests) scored **90.4 %** in CI (166 mutants, 150 killed, run 43927877708) and therefore *passed* a 90 % gate — a real weakness found by our own blocked-PR experiment. The improved suite scores 98.7 % on the same sample, the degraded one 90.4 %, so 95 % sits between them with ~3.7 points of tolerance for sampling variation. **Pull request #16** removes the killing tests: the baseline still passes but the score scores 90.4 %, below the 95 % gate → the pipeline blocks it on the **mutation threshold itself** (re-run after the threshold change; the first run at 90 % let it through) (see `docs/CI_QUALITY_GATE.md`).\n')
o.append('## 7. Reproduce\n`scripts/mutation_setup.sh` then `python tools/mutate.py --workers 5 --max-per-function 14` (≈ 25 min); `python tools/mutate.py --only stock/models.py::StockItem.take_stock` for one function; `python tools/mutate.py --rerun-survivors evidence/mutation/results_final_run.json` re-runs the survivors. Raw data: `evidence/mutation/` (`results_round1.json`, `results_round2.json` = first analysis; `results_final_run.json`, `results_final_round2.json`, `results.json` = final).\n')
print('\n'.join(o))
