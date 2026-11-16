"""StockItem.is_in_stock — every condition and flag combination (supports BR-2, PR-03)."""
import pytest
from conftest import reload

pytestmark = pytest.mark.django_db


def test_in_stock_for_normal_item(item):
    assert item.is_in_stock() is True and item.in_stock is True


@pytest.mark.parametrize('status', [50, 55, 85])
def test_available_statuses_count_as_in_stock(item, status):
    item.status = status
    assert item.is_in_stock() is True


@pytest.mark.parametrize('status', [60, 65, 70, 75])
def test_unavailable_statuses_are_not_in_stock(item, status):
    item.status = status
    assert item.is_in_stock() is False


def test_status_ignored_when_check_status_false(item):
    item.status = 60
    assert item.is_in_stock(check_status=False) is True


def test_location_excluded_from_stock(item):
    from stock.models import StockLocation
    loc = StockLocation.objects.create(name='Quarantine', exclude_from_stock=True)
    item.location = loc
    assert item.is_in_stock() is False
    assert item.is_in_stock(check_status=False) is True    # location check belongs to the status check


def test_location_not_excluded(item):
    from stock.models import StockLocation
    item.location = StockLocation.objects.create(name='Shelf')
    assert item.is_in_stock() is True


@pytest.mark.parametrize('q, expected', [(0, False), (-1, False), (1, True)])
def test_quantity_condition(make_item, q, expected):
    i = make_item(max(q, 0)); i.quantity = q
    assert i.is_in_stock() is expected


def test_quantity_ignored_when_check_quantity_false(make_item):
    assert make_item(0).is_in_stock(check_quantity=False) is True


def test_in_production_item_is_not_in_stock(item):
    item.is_building = True
    assert item.is_in_stock() is False
    assert item.is_in_stock(check_in_production=False) is True
