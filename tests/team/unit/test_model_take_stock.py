"""WF-B at model level: StockItem.take_stock / updateQuantity (FR-05..FR-08, BR-1, BR-3)."""
from decimal import Decimal
from types import SimpleNamespace
import pytest
from conftest import REMOVE, history, reload

pytestmark = pytest.mark.django_db


@pytest.mark.req('FR-05')
@pytest.mark.risk('PR-01')
def test_remove_decreases_quantity_by_exact_amount(item, user):
    assert item.take_stock(4, user) is True
    assert reload(item).quantity == Decimal('6')


@pytest.mark.req('FR-06')
def test_remove_records_history(item, user):
    item.take_stock(Decimal('2.5'), user, notes='damaged')
    e = history(item, REMOVE)
    assert len(e) == 1 and e[0].additional_data['deltas']['removed'] == 2.5
    assert e[0].changes['quantity'] == ['10.00000', '7.50000'] and e[0].notes == 'damaged'


@pytest.mark.req('FR-11')
def test_remove_on_serialized_item_is_noop(make_item, user):
    s = make_item(1, serial='9')
    assert s.take_stock(1, user) is False and reload(s).quantity == 1


def test_remove_non_decimal_quantity_returns_false(item, user):
    assert item.take_stock('abc', user) is False and reload(item).quantity == 10


@pytest.mark.parametrize('q', [0, -1])
def test_remove_non_positive_returns_false(item, user, q):
    assert item.take_stock(q, user) is False
    assert reload(item).quantity == 10 and history(item, REMOVE) == []


def test_remove_returns_false_for_unsaved_item(part, user):
    from stock.models import StockItem
    assert StockItem(part=part, quantity=3).take_stock(1, user) is False


def test_remove_from_depleted_item_is_noop(make_item, user):
    z = make_item(0)
    assert z.take_stock(1, user) is False and history(z, REMOVE) == []


@pytest.mark.req('FR-07')
@pytest.mark.risk('PR-01')
def test_remove_more_than_available_is_clamped_upstream_behaviour(item, user):
    """CHARACTERISATION of the baseline (defect DEF-01): excess is silently discarded.
    The expected behaviour (rejection) is asserted at serializer level in test_adjustment_serializers.py."""
    assert item.take_stock(100, user) is True
    assert reload(item).quantity == 0
    assert history(item, REMOVE)[0].additional_data['deltas']['removed'] == 10.0   # clamped, not 100


@pytest.mark.req('FR-08', 'BR-3')
def test_remove_all_retains_item_at_zero_when_not_delete_on_deplete(item, user):
    item.take_stock(10, user)
    got = reload(item)
    assert got is not None and got.quantity == 0 and got.in_stock is False


@pytest.mark.req('FR-08', 'BR-3')
def test_remove_all_deletes_item_when_delete_on_deplete(make_item, user):
    d = make_item(5, delete_on_deplete=True)
    pk = d.pk                      # Django clears instance.pk when the row is deleted
    d.take_stock(5, user)
    assert reload(SimpleNamespace(pk=pk)) is None
    assert history(pk, REMOVE)[0].additional_data['deltas']['removed'] == 5.0   # history survives deletion


def test_remove_without_tracking_when_requested(item, user):
    item.take_stock(1, user, record_tracking=False)
    assert reload(item).quantity == 9 and history(item, REMOVE) == []


def test_remove_applies_status_batch_and_reference_fields(item, user, markers):
    from stock.status_codes import StockStatus
    item.take_stock(1, user, status=StockStatus.DAMAGED.value, batch='B9', packaging='bag', salesorder=markers.sales_order)
    got = reload(item)
    assert (got.status, got.batch, got.packaging) == (StockStatus.DAMAGED.value, 'B9', 'bag')


def test_remove_accepts_status_custom_key_fallback(item, user):
    from stock.status_codes import StockStatus
    item.take_stock(1, user, status_custom_key=StockStatus.ATTENTION.value)
    assert reload(item).status == StockStatus.ATTENTION.value


# ---------------------------------------------------------------- updateQuantity
def test_update_quantity_serialized_returns_none(make_item):
    assert make_item(1, serial='5').updateQuantity(3) is None


def test_update_quantity_invalid_value_returns_none(item):
    assert item.updateQuantity('x') is None and reload(item).quantity == 10


def test_update_quantity_negative_is_floored_at_zero(item):
    assert item.updateQuantity(-5) is True and reload(item).quantity == 0


def test_update_quantity_same_value_returns_none(item):
    assert item.updateQuantity(10) is None


def test_update_quantity_zero_deletes_when_delete_on_deplete(make_item):
    d = make_item(3, delete_on_deplete=True)
    assert d.updateQuantity(0) is False and reload(d) is None


def test_update_quantity_zero_keeps_item_when_cannot_delete(make_item, markers, monkeypatch):
    d = make_item(3, delete_on_deplete=True)
    monkeypatch.setattr(type(d), 'can_delete', lambda self: False)
    assert d.updateQuantity(0) is True and reload(d).quantity == 0


def test_update_quantity_zero_keeps_item_without_flag(item):
    assert item.updateQuantity(0) is True and reload(item) is not None


# ---------------------------------------------------------------- lock_quantity
def test_lock_quantity_refreshes_stale_in_memory_value(item):
    from stock.models import StockItem
    StockItem.objects.filter(pk=item.pk).update(quantity=Decimal('42'))
    assert item.quantity == 10 and item.lock_quantity() is True and item.quantity == 42


def test_lock_quantity_false_without_pk(part):
    from stock.models import StockItem
    assert StockItem(part=part, quantity=1).lock_quantity() is False


def test_lock_quantity_false_when_row_gone(item):
    from stock.models import StockItem
    StockItem.objects.filter(pk=item.pk).delete()
    assert item.lock_quantity() is False
