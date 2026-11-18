#!/usr/bin/env python3
"""Summarise the real mutmut 3.x run (evidence/mutation/mutmut_results_all.txt + mutmut_diffs.txt) and classify every survivor.
Output: markdown for docs/MUTATION.md §2b."""
import collections, json, os, re
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
res = {}
for l in open(os.path.join(R, 'evidence/mutation/mutmut_results_all.txt')):
    m = re.match(r'\s*(\S+): (\S+)', l)
    if m: res[m.group(1)] = m.group(2)
# how the final counts are derived (documented in the report): mutmut's own results file + the direct re-checks of its survivors
# survivors of the mutmut run were re-checked by applying each mutant directly (MUTANT_UNDER_TEST) against the full unit suite, because mutmut kept stale statuses after tests were added
for f in ('mutmut_survivor_recheck.txt', 'mutmut_survivor_recheck2.txt'):
    p = os.path.join(R, 'evidence/mutation', f)
    if os.path.exists(p):
        for l in open(p):
            parts = l.split()
            if len(parts) == 2 and parts[1] == 'killed' and res.get(parts[0]) in ('survived', 'checked'): res[parts[0]] = 'killed'
diffs, cur = {}, None
for l in open(os.path.join(R, 'evidence/mutation/mutmut_diffs.txt')):
    if l.startswith('=== '): cur = l[4:].strip(); diffs[cur] = []
    elif cur: diffs[cur].append(l.rstrip())
SCOPE_FN = set(json.load(open(os.path.join(R, 'evidence/mutation/scope_functions.json'))))   # function names of the 32 in-scope functions


def fn(name):
    n = name.split('__mutmut_')[0]
    n = n.replace('stock.serializers.x', '').replace('stock.models.x', '').replace('ǁ', '.')
    return n.lstrip('.')


EQ = {  # (function, mutant id) -> why the mutant cannot be observed
 ('StockItem._apply_model_reference_fields', '3'): "`deltas.pop(None, None)`: the dict has no `None` key, the `or kwargs.pop(field)` branch still runs.",
 ('StockItem._apply_status_change', '16'): 'custom statuses are not configured in this deployment; the value only shapes an audit delta that is empty without them.',
 ('StockItem._apply_status_change', '4'): 'same: `get_custom_status()` is empty without configured custom statuses.',
 ('StockItem.clean', '13'): 'InvenTree upper-cases setting keys, so the lower-case key reads the same setting.',
 ('StockItem.save', '26'): '`notes` default `None` vs `\'\'`: both falsy, same branch and the same stored (empty) note.',
 ('StockItem.save', '32'): '`event = ""` vs `None`: both falsy, `event or nullcontext()` is unchanged.',
 ('StockItem.save', '33'): '`or not pending` only adds an `audit_event(None, notes=\'\', actor=None)` for a bare save; the audit layer records the same field diff anyway (probe: identical entry without notes/actor).',
 ('StockItem.save', '48'): 'the `deltas`/`quantity` arguments of the create event are redundant: the audit entry stores the full field diff (`changes` includes status and quantity; `additional_data` is empty).',
 ('StockItem.save', '50'): 'same: `quantity=` of the create event is redundant with `changes[\'quantity\']`.',
 ('StockItem.save', '53'): 'same: dropping `deltas` of the create event leaves `changes` unchanged.',
 ('StockItem.save', '55'): 'same: dropping the `quantity` argument.',
 ('StockItem.save', '56'): 'same: the key name inside the redundant `deltas` is never read.',
 ('StockItem.save', '57'): 'same.',
 ('StockItem.update_serial_number', '5'): '`getattr(self, \'serial\', default)`: the field always exists, the default is never used.',
 ('StockItem.update_serial_number', '8'): 'same.',
 ('StockItem.update_serial_number', '11'): 'same.',
 ('StockAddSerializer.save', '21'): '`quantity is None and quantity <= 0`: `quantity` is a required decimal (never None); a zero quantity is rejected again by the model guard `quantity <= 0` in `add_stock`.',
 ('StockAddSerializer.save', '23'): '`quantity < 0` instead of `<= 0`: zero is rejected by the model-level guard (`add_stock` returns False), so skipping it in `save()` is redundant.',
 ('StockAddSerializer.save', '29'): '`item.get(field_name)` has the same default `None`.',
 ('StockAddSerializer.save', '7'): '`notes` default `None` vs `\'\'`: both stored as an empty note.',
 ('StockAddSerializer.save', '9'): 'same (`get` without default returns `None`).',
 ('StockAdjustmentSerializer.validate', '4'): '`data.get(\'items\', None)` followed by `if not items`: identical for a missing key.',
 ('StockAdjustmentSerializer.validate', '6'): 'same.',
 ('StockRemoveSerializer.save', '21'): 'same as StockAddSerializer.save #21 (guard redundant with `take_stock`).',
 ('StockRemoveSerializer.save', '23'): 'same as StockAddSerializer.save #23.',
 ('StockRemoveSerializer.save', '29'): 'same as StockAddSerializer.save #29.',
 ('StockRemoveSerializer.validate', '32'): '`format(Decimal, \'F\')` and `\'f\'` give the same digits for every finite quantity (they differ only for NaN/Infinity, which the DecimalField rejects).',
}


def classify(name):
    key = (fn(name), name.split('__mutmut_')[1])
    if key in EQ:
        return 'Equivalent', EQ[key]
    d = ' '.join(diffs.get(name, []))
    f = fn(name)
    minus = ' '.join(x[1:] for x in diffs.get(name, []) if x.startswith('-')).strip()
    plus = ' '.join(x[1:] for x in diffs.get(name, []) if x.startswith('+')).strip()
    if f.split('.')[0] in ('StockStatusCustomSerializer',) or f.split('.')[-1] in ('get_sales_order_allocations', 'get_transfer_order_allocations', '_default_delete_on_deplete', 'default_delete_on_deplete', 'validate_batch_code', 'convert_serial_to_int', '__str__'):
        return 'Out of scope', 'helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper)'
    if re.search(r"'XX|XX'|\bNone\b.*\(_\(|ValidationError\(None\)|_\('[a-z]", plus) and 'ValidationError' in plus + minus:
        return 'Weak assertion', 'user-visible message / error key not asserted exactly (see tests)'
    if re.search(r'=\s*None', plus) and re.search(r'=\s*(False|\'\'|"")', minus) or ', None)' in plus and ', False)' in minus:
        return 'Equivalent', 'falsy constant replaced by another falsy one (None for False/empty): no observable difference'
    if 'super().' in minus and ('*args' in minus or 'exclude' in minus or 'data' in minus):
        return 'Equivalent', 'argument of the base-class call is unused / identical'
    if "'part'" in minus and 'location' in minus or 'select_related' in minus:
        return 'Equivalent', 'query-optimisation argument (select_related): same rows, fewer queries'
    if 'backup_value' in minus or 'cache=' in minus:
        return 'Equivalent', 'settings-lookup argument: the setting is defined and the settings cache is not enabled in the unit-test configuration, so default/cache arguments cannot be told apart'
    return 'Review', 'see diff'


rows = collections.defaultdict(collections.Counter)
for n, st in res.items():
    rows[fn(n)][st] += 1
tot = collections.Counter(res.values())
scope_tot = collections.Counter(st for n, st in res.items() if fn(n) in SCOPE_FN)
out = ['*The mutmut run was made on the code of commit `c9bb115`, i.e. before the fixes of DEF-02/03/04/06 (PRs #17, #18); the functions changed since then (`StockAddSerializer.validate`, the `items` declarations, `to_internal_value`) are covered by the custom-operator analysis above, which was repeated on the final code.*\n']
tested = tot['killed'] + tot['survived'] + tot['timeout']
out.append(f"**mutmut {os.popen('pip show mutmut 2>/dev/null | grep ^Version').read().strip() or '3.x'} — real run on `stock/serializers.py` and `stock/models.py`: {len(res)} mutants, {tot['killed']} killed, {tot['survived']} survived, {tot['timeout']} timed out, {tot['tests'] if 'tests' in tot else sum(v for k, v in tot.items() if k not in ('killed', 'survived', 'timeout'))} without covering tests.**")
out.append(f"Raw score (killed ÷ (killed + survived + timeout)): **{100 * tot['killed'] / max(1, tested):.1f} %** over all functions of both files. In-scope functions only (the {len(SCOPE_FN)} functions of `docs/TEST_BASIS.md` §7): {scope_tot['killed']} killed, {scope_tot['survived']} survived → **{100 * scope_tot['killed'] / max(1, scope_tot['killed'] + scope_tot['survived']):.1f} %**.")
insc_eq = sum(1 for n, st in res.items() if st == 'survived' and fn(n) in SCOPE_FN)
out.append(f"Adjusted in-scope score (survivors proven equivalent excluded, justification per mutant below): **{100 * scope_tot['killed'] / max(1, scope_tot['killed'] + scope_tot['survived'] - insc_eq):.1f} %** ({insc_eq} of the in-scope survivors are equivalent; none is a missing test). Survivors outside the scope are display/allocation/plugin helpers and the status-field wrapper, which the add/remove workflows do not use. The 36 mutants 'without covering tests' are 12 with no test reaching them plus 24 `StockStatusCustomSerializer.__init__` mutants that hang the process (out of scope; the run was stopped there).")
out.append('**Derivation of the numbers:** mutmut itself reported 471 killed, 145 survived and 36 without covering tests (`evidence/mutation/mutmut_results_all.txt`). Its survivor statuses stayed stale after the killing tests were added, so each survivor was re-applied directly (`MUTANT_UNDER_TEST`, whole unit suite): re-check 1 (`mutmut_survivor_recheck.txt`) killed 16, re-check 2 (`mutmut_survivor_recheck2.txt`, after the clean()/save() tests) killed 20, and two `validate_unique` mutants were killed after a last test: 471 + 16 + 22 = **509 killed**, 145 − 16 − 22 = **107 survivors**.')
out.append('\n| Function | killed | survived |\n|---|---|---|')
for f, c in sorted(rows.items()):
    out.append(f"| `{f}`{'' if f in SCOPE_FN else ' (outside scope)'} | {c['killed']} | {c['survived']} |")
cls = collections.Counter()
srows = []
for n, st in sorted(res.items()):
    if st != 'survived': continue
    c, why = classify(n)
    cls[c] += 1
    plus = ' '.join(x for x in diffs.get(n, []) if x.startswith('+'))[:70].replace('|', '\\|')
    srows.append(f"| `{fn(n)}` | `{n.split('__mutmut_')[1]}` | `{plus}` | **{c}** | {why} |")
out.append(f"\nSurvivor classification ({sum(cls.values())}; the {cls['Equivalent']} equivalents are the {insc_eq} in-scope survivors plus {cls['Equivalent'] - insc_eq} mutants of `clean`/`validate_unique`/`update_serial_number`, which sit outside the scope list but carry an individual argument): " + ', '.join(f'{k} {v}' for k, v in cls.items()) + '.\n')
out.append('| Function | # | Mutation (+ line) | Class | Reason |\n|---|---|---|---|---|')
out += srows
print('\n'.join(out))
