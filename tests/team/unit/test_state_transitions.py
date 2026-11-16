"""State transition testing for BR-3 (IN_STOCK, DEPLETED, DELETED, NON_ADJUSTABLE): every allowed transition and >= 1 disallowed transition from each state."""
import pytest
from decimal import Decimal
from rest_framework.exceptions import ValidationError
from conftest import ADD, REMOVE, history, reload
from test_adjustment_serializers import _add, _remove, payload

pytestmark = pytest.mark.django_db


# ---- allowed transitions
@pytest.mark.req('BR-3')
def test_in_stock_add_stays_in_stock(item, request_ctx):
    _add(payload(item, 1), request_ctx)
    assert reload(item).quantity == 11 and reload(item).in_stock


def test_in_stock_partial_remove_stays_in_stock(item, request_ctx):
    _remove(payload(item, 4), request_ctx)
    assert reload(item).quantity == 6 and reload(item).in_stock


def test_in_stock_remove_all_becomes_depleted_when_retained(item, request_ctx):
    _remove(payload(item, 10), request_ctx)
    got = reload(item)
    assert got is not None and got.quantity == 0 and not got.in_stock


def test_in_stock_remove_all_becomes_deleted_when_delete_on_deplete(make_item, request_ctx):
    d = make_item(10, delete_on_deplete=True); pk = d.pk
    _remove(payload(d, 10), request_ctx)
    assert reload(type('X', (), {'pk': pk})) is None


def test_depleted_add_returns_to_in_stock(make_item, request_ctx):
    z = make_item(0)
    _add(payload(z, 8), request_ctx)
    assert reload(z).quantity == 8 and reload(z).in_stock


# ---- disallowed transitions (one or more from every state)
@pytest.mark.req('BR-3')
def test_depleted_remove_is_ignored_no_change_no_history(make_item, request_ctx):
    z = make_item(0)
    _remove(payload(z, 1), request_ctx)
    assert reload(z).quantity == 0 and history(z, REMOVE) == []


def test_deleted_item_cannot_be_adjusted(make_item, request_ctx):
    d = make_item(5, delete_on_deplete=True); pk = d.pk
    _remove(payload(d, 5), request_ctx)
    for call in (_add, _remove):
        with pytest.raises(ValidationError, match='does not exist'):
            call({'items': [{'pk': pk, 'quantity': 1}]}, request_ctx)


@pytest.mark.req('FR-04')
@pytest.mark.parametrize('call', [_add, _remove], ids=['add', 'remove'])
def test_non_adjustable_item_disallowed_transition_unchanged(item, markers, request_ctx, call):
    """IN_STOCK -> NON_ADJUSTABLE (installed in another item): adjustment is disallowed and nothing changes.
    (Each single-reference condition is covered by the MCC rows; this is the state-level view.)"""
    from stock.models import StockItem
    StockItem.objects.filter(pk=item.pk).update(belongs_to_id=markers.parent.pk)
    with pytest.raises(ValidationError, match='not in stock'):
        call(payload(item, 1), request_ctx)
    assert reload(item).quantity == 10 and history(item, ADD) == [] and history(item, REMOVE) == []


@pytest.mark.req('BR-3', 'FR-03a')
@pytest.mark.parametrize('call', [_add, _remove], ids=['add', 'remove'])
def test_in_stock_invalid_event_is_disallowed_and_state_unchanged(item, request_ctx, call):
    """Disallowed transition from IN_STOCK: an invalid (negative) quantity is rejected and the item stays IN_STOCK at 10."""
    with pytest.raises(ValidationError):
        call(payload(item, '-1'), request_ctx)
    got = reload(item)
    assert got.quantity == 10 and got.in_stock
