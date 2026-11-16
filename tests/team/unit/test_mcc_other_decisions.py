"""Complete MCC (every FEASIBLE row executed once) for the other multi-condition decisions on the add/remove path.
Expected outcomes come from tools/mcdc.py (derived from the requirements, not from the code under test)."""
import os, sys
from decimal import Decimal
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'tools')))
import mcdc  # noqa: E402
from conftest import reload

pytestmark = pytest.mark.django_db


def rows(key):
    d = mcdc.DECISIONS[key]
    return [pytest.param(n, row, out, id=f"{key}-MCC{n:02d}-" + ''.join('T' if v else 'F' for v in row))
            for n, row, out, feas in mcdc.truth_table(d) if feas]


# ============================================================ is_in_stock sub-decisions
@pytest.mark.parametrize('n,row,not_in_stock', rows('IS-STATUS'))
@pytest.mark.req('BR-2')
def test_is_in_stock_status_decision(n, row, not_in_stock, item):
    check_status, unavailable = row
    item.status = 60 if unavailable else 10            # 60 = Destroyed (unavailable), 10 = OK
    assert item.is_in_stock(check_status=check_status, check_quantity=False, check_in_production=False) is (not not_in_stock)


@pytest.mark.parametrize('n,row,not_in_stock', rows('IS-LOCATION'))
@pytest.mark.req('BR-2')
def test_is_in_stock_location_decision(n, row, not_in_stock, item):
    from stock.models import StockLocation
    check_status, has_location, excluded = row
    if has_location:
        item.location = StockLocation.objects.create(name=f'L{n}', exclude_from_stock=excluded)
    assert item.is_in_stock(check_status=check_status, check_quantity=False, check_in_production=False) is (not not_in_stock)


@pytest.mark.parametrize('n,row,not_in_stock', rows('IS-QUANTITY'))
@pytest.mark.req('BR-2')
def test_is_in_stock_quantity_decision(n, row, not_in_stock, item):
    check_quantity, le0 = row
    item.quantity = 0 if le0 else 5
    assert item.is_in_stock(check_status=False, check_quantity=check_quantity, check_in_production=False) is (not not_in_stock)


@pytest.mark.parametrize('n,row,not_in_stock', rows('IS-PRODUCTION'))
@pytest.mark.req('BR-2')
def test_is_in_stock_production_decision(n, row, not_in_stock, item):
    check_prod, building = row
    item.is_building = building
    assert item.is_in_stock(check_status=False, check_quantity=False, check_in_production=check_prod) is (not not_in_stock)


# ============================================================ BR-3: `quantity == 0 and delete_on_deplete and can_delete()`
@pytest.mark.parametrize('n,row,deleted', rows('BR3'))
@pytest.mark.req('BR-3', 'FR-08')
@pytest.mark.risk('PR-01')
def test_br3_delete_decision_with_real_can_delete(n, row, deleted, make_item):
    quantity_zero, delete_on_deplete, can_delete = row
    d = make_item(3, delete_on_deplete=delete_on_deplete)
    if not can_delete:
        make_item(1, belongs_to=d)               # an installed child makes the REAL can_delete() return False
    assert d.can_delete() is can_delete
    new_qty = 0 if quantity_zero else 1           # a partial change must NEVER delete the item (kills the `quantity == 0` mutant)
    result = d.updateQuantity(new_qty)
    if deleted:
        assert result is False and reload(d) is None
    else:
        assert result is True and reload(d).quantity == new_qty


# ============================================================ BR-1: take_stock guards (masked rows are not executed)
@pytest.mark.parametrize('n,row,applied', rows('BR1'))
@pytest.mark.req('BR-1', 'FR-05', 'FR-11')
@pytest.mark.risk('PR-01')
def test_br1_take_stock_guard_decision(n, row, applied, make_item, user):
    not_serialized, requested_positive, available_positive = row
    it = make_item(10 if available_positive else 0) if not_serialized else make_item(1, serial='77')
    before = reload(it).quantity
    requested = 4 if requested_positive else 0
    assert it.take_stock(requested, user) is applied
    assert reload(it).quantity == (before - min(requested, before) if applied else before)


# ============================================================ small decisions
@pytest.mark.parametrize('n,row,reject', rows('VQ'))
@pytest.mark.req('FR-03b')
def test_validate_quantity_zero_decision(n, row, reject):
    from rest_framework.exceptions import ValidationError
    from stock.serializers import StockAdjustmentItemSerializer as S
    require_non_zero, le0 = row
    q = Decimal(0) if le0 else Decimal(1)
    if reject:
        with pytest.raises(ValidationError):
            S(require_non_zero=require_non_zero).validate_quantity(q)
    else:
        assert S(require_non_zero=require_non_zero).validate_quantity(q) == q


@pytest.mark.parametrize('n,row,uses_db', rows('PF'))
def test_prefetch_field_fallback_decision(n, row, uses_db, item):
    from InvenTree.fields import PrefetchedPrimaryKeyRelatedField
    from stock.models import StockItem
    cache_empty, pk_not_cached = row
    sentinel = object()
    cache = {} if cache_empty else ({item.pk + 1000: sentinel} if pk_not_cached else {item.pk: sentinel})
    f = PrefetchedPrimaryKeyRelatedField(cache_key='_c', queryset=StockItem.objects.all())
    f._context = {'_c': cache}
    got = f.to_internal_value(item.pk)
    assert (got == item) if uses_db else (got is sentinel)


@pytest.mark.parametrize('n,row,no_change', rows('STAT'))
def test_apply_status_change_decision(n, row, no_change, item):
    no_status, same = row
    deltas = {}
    status = None if no_status else (10 if same else 55)       # item is OK (10)
    item._apply_status_change(status, deltas)
    assert (deltas == {} and item.status == 10) if no_change else (deltas['status'] == 55 and item.status == 55)


@pytest.mark.parametrize('n,row,resolved', rows('RESOLVE'))
def test_resolve_status_kwarg_decision(n, row, resolved, item):
    status_given, custom_given = row
    kwargs = {}
    if status_given: kwargs['status'] = 55
    if custom_given: kwargs['status_custom_key'] = 50
    out = item._resolve_status_kwarg(kwargs)
    assert out == (55 if status_given else (50 if custom_given else None)) and (out is not None) is resolved
