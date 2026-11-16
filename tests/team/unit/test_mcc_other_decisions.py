"""Complete MCC (every feasible row executed) for the other multi-condition decisions on the add/remove path:
is_in_stock (status, location, quantity, production), updateQuantity deletion (BR-3) and take_stock guards (BR-1).
Expected outcomes come from tools/mcdc.py (derived from the requirements)."""
import os, sys
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'tools')))
import mcdc  # noqa: E402
from conftest import reload

pytestmark = pytest.mark.django_db


def rows(key):
    d = mcdc.DECISIONS[key]
    return [pytest.param(n, row, out, id=f"{key}-MCC{n:02d}-" + ''.join('T' if v else 'F' for v in row))
            for n, row, out, feas in mcdc.truth_table(d) if feas]


# ---------------------------------------------------------------- is_in_stock sub-decisions
@pytest.mark.parametrize('n,row,not_in_stock', rows('IS-STATUS'))
@pytest.mark.req('BR-2')
def test_is_in_stock_status_decision(n, row, not_in_stock, item):
    check_status, unavailable = row
    item.status = 60 if unavailable else 10            # 60 = Destroyed (unavailable), 10 = OK
    assert item.is_in_stock(check_status=check_status, check_quantity=False, check_in_production=False) is (not not_in_stock)


@pytest.mark.parametrize('n,row,not_in_stock', rows('IS-LOCATION'))
@pytest.mark.parametrize('has_location', [True, False], ids=['with-location', 'no-location'])
@pytest.mark.req('BR-2')
def test_is_in_stock_location_decision(n, row, not_in_stock, has_location, item):
    from stock.models import StockLocation
    check_status, excluded = row
    if has_location:
        item.location = StockLocation.objects.create(name=f'L{n}{excluded}', exclude_from_stock=excluded)
    elif excluded:
        pytest.skip('coupled condition: an excluded location needs a location (masking, see tools/mcdc.py note)')
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


# ---------------------------------------------------------------- BR-3: deletion on depletion = delete_on_deplete AND can_delete()
@pytest.mark.parametrize('n,row,deleted', rows('BR3'))
@pytest.mark.req('BR-3', 'FR-08')
@pytest.mark.risk('PR-01')
def test_br3_delete_decision_with_real_can_delete(n, row, deleted, make_item):
    delete_on_deplete, can_delete = row
    d = make_item(3, delete_on_deplete=delete_on_deplete)
    if not can_delete:
        make_item(1, belongs_to=d)               # an installed child makes the REAL can_delete() return False
    assert d.can_delete() is can_delete
    result = d.updateQuantity(0)
    if deleted:
        assert result is False and reload(d) is None
    else:
        assert result is True and reload(d).quantity == 0


# ---------------------------------------------------------------- BR-1: take_stock guards
@pytest.mark.parametrize('n,row,applied', rows('BR1'))
@pytest.mark.req('BR-1', 'FR-05', 'FR-11')
@pytest.mark.risk('PR-01')
def test_br1_take_stock_guard_decision(n, row, applied, make_item, user):
    not_serialized, requested_positive, available_positive = row
    kw = {} if not_serialized else {'serial': '77'}
    start = 1 if not not_serialized else (10 if available_positive else 0)
    it = make_item(start, **kw)
    if not not_serialized and not available_positive:
        pass        # a serialized item always holds quantity 1; the serialized guard fires first (masking by order), expected: ignored
    requested = 4 if requested_positive else 0
    before = reload(it).quantity
    assert it.take_stock(requested, user) is applied
    assert reload(it).quantity == (before - min(requested, before) if applied else before)
