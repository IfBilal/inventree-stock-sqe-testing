"""WF-A at model level: StockItem.add_stock (FR-01, FR-02, FR-11, BR-1)."""
from decimal import Decimal
import pytest
from conftest import ADD, history, reload

pytestmark = pytest.mark.django_db


@pytest.mark.req('FR-01')
@pytest.mark.risk('PR-01')
def test_add_increases_quantity_by_exact_amount(item, user):
    assert item.add_stock(5, user) is True
    assert reload(item).quantity == Decimal('15')


@pytest.mark.req('FR-02')
def test_add_records_history_with_deltas_and_notes(item, user):
    item.add_stock(Decimal('2.5'), user, notes='restock')
    entries = history(item, ADD)
    assert len(entries) == 1
    assert entries[0].additional_data['deltas']['added'] == 2.5
    assert entries[0].changes['quantity'] == ['10.00000', '12.50000']
    assert entries[0].notes == 'restock' and entries[0].actor_username == user.username


@pytest.mark.req('FR-11')
def test_add_on_serialized_item_is_noop(make_item, user):
    s = make_item(1, serial='7')
    assert s.add_stock(5, user) is False
    assert reload(s).quantity == 1 and history(s, ADD) == []


def test_add_non_decimal_quantity_returns_false(item, user):
    assert item.add_stock('abc', user) is False
    assert reload(item).quantity == 10


@pytest.mark.parametrize('q', [0, -1, Decimal('-0.00001')])
@pytest.mark.req('FR-03')
def test_add_non_positive_quantity_returns_false(item, user, q):
    assert item.add_stock(q, user) is False
    assert reload(item).quantity == 10 and history(item, ADD) == []


def test_add_returns_false_when_item_not_saved(part, user):
    from stock.models import StockItem
    unsaved = StockItem(part=part, quantity=1)
    assert unsaved.add_stock(1, user) is False


def test_add_returns_false_when_row_deleted_meanwhile(item, user):
    from stock.models import StockItem
    StockItem.objects.filter(pk=item.pk).delete()
    assert item.add_stock(1, user) is False


def test_add_applies_optional_fields_and_status(item, user):
    from stock.status_codes import StockStatus
    assert item.add_stock(1, user, batch='B1', packaging='box', status=StockStatus.DAMAGED.value) is True
    got = reload(item)
    assert got.batch == 'B1' and got.packaging == 'box' and got.status == StockStatus.DAMAGED.value
    assert history(item, ADD)[0].changes['status'] == [StockStatus.OK.value, StockStatus.DAMAGED.value]


def test_add_same_status_is_not_recorded_as_change(item, user):
    from stock.status_codes import StockStatus
    item.add_stock(1, user, status=StockStatus.OK.value)
    assert 'status' not in (history(item, ADD)[0].changes or {})
