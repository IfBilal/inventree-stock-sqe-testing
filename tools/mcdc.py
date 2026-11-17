"""MCC / MC/DC generator for BR-2 (adjustability decision of StockAdjustmentItemSerializer.validate_pk).

Decision under test (from the requirement BR-2, written independently of the code):
    REJECT = (not ALLOW) and (SO or BT or CU or CB)
  ALLOW = global setting STOCK_ALLOW_OUT_OF_STOCK_TRANSFER is true
  SO / BT / CU / CB = sales_order / belongs_to / customer / consumed_by is set (not None)
Usage: python tools/mcdc.py > docs/MCC_MCDC.md
"""
from itertools import combinations, product

from dataclasses import dataclass
from typing import Callable


@dataclass
class Decision:
    key: str                       # id used in tests/docs
    title: str
    conditions: list
    fn: Callable                   # row (tuple of bools) -> outcome (bool); written from the REQUIREMENT, not the code
    outcome_label: tuple           # (label when True, label when False)
    feasible: Callable = lambda row: True   # rows that cannot occur (short-circuit dependency) are listed but not executed
    note: str = ''


def _d(row, i): return row[i]


DECISIONS = {
    # BR-2 adjustability (validate_pk): reject iff not ALLOW and any of the four structural references is set
    'BR2': Decision('BR2', 'validate_pk adjustability (BR-2)', ['ALLOW', 'SO', 'BT', 'CU', 'CB'],
                    lambda r: (not r[0]) and (r[1] or r[2] or r[3] or r[4]), ('reject', 'accept')),
    # is_in_stock sub-decisions (each returns False => item NOT in stock). Others neutralised in the test.
    'IS-STATUS': Decision('IS-STATUS', 'is_in_stock: status not available', ['check_status', 'status_unavailable'],
                          lambda r: r[0] and r[1], ('not in stock', 'in stock')),
    'IS-LOCATION': Decision('IS-LOCATION', 'is_in_stock: location excluded from stock', ['check_status', 'has_location', 'location_excluded'],
                            lambda r: r[0] and r[1] and r[2], ('not in stock', 'in stock'),
                            feasible=lambda r: r[1] or not r[2],
                            note='Real code: `check_status and self.location and self.location.exclude_from_stock`. `location_excluded` is only evaluated when the item has a location, so rows with has_location=F and location_excluded=T cannot occur (infeasible, listed but not executed; unique-cause pairs are formed among feasible rows).'),
    'IS-QUANTITY': Decision('IS-QUANTITY', 'is_in_stock: quantity not positive', ['check_quantity', 'quantity_le_0'],
                            lambda r: r[0] and r[1], ('not in stock', 'in stock')),
    'IS-PRODUCTION': Decision('IS-PRODUCTION', 'is_in_stock: item in production', ['check_in_production', 'is_building'],
                              lambda r: r[0] and r[1], ('not in stock', 'in stock')),
    # BR-3 deletion in updateQuantity: `quantity == 0 and self.delete_on_deplete and self.can_delete()`
    'BR3': Decision('BR3', 'updateQuantity: delete item when depleted (BR-3)', ['quantity_zero', 'delete_on_deplete', 'can_delete'],
                    lambda r: all(r), ('deleted', 'retained'),
                    note='Short-circuit order quantity_zero, delete_on_deplete, can_delete(): `can_delete()` is only evaluated when the first two hold (its value is irrelevant otherwise; the test still sets it to a defined state).'),
    # BR-4 role permission (RolePermission.has_permission for a view that requires the stock role): `user.is_superuser or check_user_role(user, 'stock', 'add')`
    'BR4': Decision('BR4', 'RolePermission: add right on the stock role (BR-4)', ['is_superuser', 'group_grants_add'],
                    lambda r: r[0] or r[1], ('allowed', 'denied'),
                    note='Short-circuit: the superuser branch returns before the role lookup, so `group_grants_add` is only evaluated for non-superusers; the superuser rows still set it to a defined state.'),
    # tracking: an audit event is skipped iff it is an update event with no deltas and no notes (history must not record empty noise)
    'TRACK-EMPTY': Decision('TRACK-EMPTY', '_is_empty_tracking_event: event carries no information', ['is_update_event', 'no_deltas', 'no_notes'],
                            lambda r: all(r), ('empty (not recorded)', 'recorded')),
    # validate_quantity: `require_non_zero and quantity <= 0`
    'VQ': Decision('VQ', 'validate_quantity: zero rejected when require_non_zero', ['require_non_zero', 'quantity_le_0'],
                   lambda r: r[0] and r[1], ('reject', 'accept'),
                   note='Called with a non-negative quantity (the `quantity < 0` operand is a separate dead branch, see COVERAGE_JUSTIFICATION).'),
    # PrefetchedPrimaryKeyRelatedField.to_internal_value: fall back to a DB lookup when `not cache or pk not in cache`
    'PF': Decision('PF', 'prefetch field: fall back to database lookup', ['cache_empty', 'pk_not_cached'],
                   lambda r: r[0] or r[1], ('database lookup', 'cache hit'),
                   feasible=lambda r: not (r[0] and not r[1]),
                   note='`cache_empty` (no/empty cache) implies the pk is not cached, so (cache_empty=T, pk_not_cached=F) cannot occur.'),
    # _apply_status_change: return early when `not status or self.compare_status(status)`
    'STAT': Decision('STAT', '_apply_status_change: no change recorded', ['no_status', 'same_status'],
                     lambda r: r[0] or r[1], ('no change', 'status changed'),
                     feasible=lambda r: not (r[0] and r[1]),
                     note='`compare_status` is only evaluated when a status is given (short-circuit), so (no_status=T, same_status=T) cannot occur.'),
    # _resolve_status_kwarg: `status or status_custom_key`
    'RESOLVE': Decision('RESOLVE', '_resolve_status_kwarg: a status value is resolved', ['status_given', 'custom_key_given'],
                        lambda r: r[0] or r[1], ('resolved', 'None')),
    # BR-1 removal guards in take_stock: the removal is applied iff the item is not serialized, the requested quantity is a positive number
    # and the item (still) exists with a positive available quantity
    'BR1': Decision('BR1', 'take_stock: removal is applied (BR-1 guards)', ['not_serialized', 'requested_positive', 'available_positive'],
                    lambda r: all(r), ('applied', 'ignored (returns False)'),
                    feasible=lambda r: r[0] or (r[1] and r[2]),
                    note='When the item is serialized the first guard returns before the others are evaluated, so those rows are masked duplicates of one execution (only the representative row is feasible). Guards are evaluated in this order and each returns False when violated. `requested_positive` = the argument converts to a Decimal that is > 0; `available_positive` = the row still exists (lock succeeds) and its quantity is > 0. When applied, the removed amount is clamped to the available quantity (DEF-01).'),
}


def truth_table(decision=None):
    d = decision or DECISIONS['BR2']
    return [(i + 1, row, bool(d.fn(row)), d.feasible(row)) for i, row in enumerate(product([False, True], repeat=len(d.conditions)))]


def independence_pairs(table, decision=None):
    """Unique-cause MC/DC pairs among FEASIBLE rows: rows differing only in one condition with different outcomes."""
    d = decision or DECISIONS['BR2']
    by_row = {row: (i, out, feas) for i, row, out, feas in table}
    pairs = {c: [] for c in d.conditions}
    for k, c in enumerate(d.conditions):
        for row, (i, out, feas) in by_row.items():
            if row[k] or not feas:
                continue
            flipped = row[:k] + (True,) + row[k + 1:]
            j, out2, feas2 = by_row[flipped]
            if feas2 and out != out2:
                pairs[c].append((i, j))
    return pairs


def minimal_mcdc_set(table, decision=None):
    """Smallest set of FEASIBLE rows containing an independence pair for every condition that has one.
    Conditions with no unique-cause pair among feasible rows are MASKED (short-circuit coupling) and reported as such."""
    d = decision or DECISIONS['BR2']
    pairs = independence_pairs(table, d)
    live = [c for c in d.conditions if pairs[c]]
    ids = [i for i, _, _, feas in table if feas]
    for size in range(len(live) + 1, len(ids) + 1):
        for subset in combinations(ids, size):
            s = set(subset)
            if all(any(a in s and b in s for a, b in pairs[c]) for c in live):
                chosen = {c: next((a, b) for a, b in pairs[c] if a in s and b in s) for c in live}
                chosen.update({c: 'masked (no unique-cause pair among feasible rows)' for c in d.conditions if c not in live})
                return sorted(subset), chosen
    raise RuntimeError('no MC/DC set for ' + d.key)


# ---- backwards-compatible BR-2 API used by tests/team/unit/test_validate_pk_mcc.py
CONDITIONS = DECISIONS['BR2'].conditions


def decision(row):
    return DECISIONS['BR2'].fn(row)


def _legacy_table():
    return [(i, row, out) for i, row, out, _ in truth_table(DECISIONS['BR2'])]


def main():
    print('# MCC and MC/DC for the multi-condition decisions on the add/remove path — generated by `tools/mcdc.py`\n')
    print('Expected outcomes are derived from the requirements (docs/TEST_BASIS.md), not from the code under test. '
          '**Complete MCC** = every feasible combination is executed as its own test (ids `MCC<n>-<row>` per decision). '
          '**MC/DC** = unique-cause independence pairs derived from the MCC table; the minimal set has n+1 rows.\n')
    for key, d in DECISIONS.items():
        t = truth_table(d)
        pairs = independence_pairs(t, d)
        mset, chosen = minimal_mcdc_set(t, d)
        print(f'## {key} — {d.title}\n')
        print(f'Conditions ({len(d.conditions)}): ' + ', '.join(d.conditions) + f'. Outcome: **{d.outcome_label[0]}** when the decision is true. ' + d.note + '\n')
        print('| # | ' + ' | '.join(d.conditions) + ' | expected | feasible | MC/DC set |\n|' + '---|' * (len(d.conditions) + 4))
        for i, row, out, feas in t:
            print(f"| {i} | " + ' | '.join('T' if v else 'F' for v in row) + f" | {d.outcome_label[0] if out else d.outcome_label[1]} | {'yes' if feas else 'no (infeasible)'} | {'✔' if i in mset else ''} |")
        print('\n| Condition | All independence pairs | Pair chosen in the minimal set |\n|---|---|---|')
        for c in d.conditions:
            print(f"| {c} | {', '.join(f'({a},{b})' for a, b in pairs[c])} | {chosen[c]} |")
        live = [c for c in d.conditions if pairs[c]]
        print(f"\nMinimal MC/DC set: rows {mset} ({len(mset)} tests = n+1 for the {len(live)} independently demonstrable conditions" + ('' if len(live) == len(d.conditions) else f"; masked: {', '.join(c for c in d.conditions if c not in live)}") + ").\n")


if __name__ == '__main__':
    main()
