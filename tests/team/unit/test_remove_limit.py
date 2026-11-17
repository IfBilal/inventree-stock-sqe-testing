"""DEF-01 fix (Issue #1): StockRemoveSerializer.validate rejects a removal larger than the available quantity (FR-07, BR-1)."""
from decimal import Decimal
import pytest
from rest_framework.exceptions import ValidationError
from conftest import REMOVE, history, reload
from test_adjustment_serializers import _remove

pytestmark = pytest.mark.django_db


def _errors(exc):
    return exc.value.detail


@pytest.mark.req('FR-07', 'BR-1')
@pytest.mark.risk('PR-01')
def test_over_removal_error_names_the_available_quantity_and_points_at_the_quantity_field(item, request_ctx):
    with pytest.raises(ValidationError) as exc:
        _remove({'items': [{'pk': item.pk, 'quantity': 11}]}, request_ctx)
    msg = str(_errors(exc)['items']['0']['quantity'][0])
    assert 'available quantity (10)' in msg
    assert reload(item).quantity == 10 and history(item, REMOVE) == []


@pytest.mark.req('FR-07', 'BR-1')
@pytest.mark.risk('PR-01')
def test_splitting_an_over_removal_over_several_entries_cannot_bypass_the_limit(item, request_ctx):
    body = {'items': [{'pk': item.pk, 'quantity': 6}, {'pk': item.pk, 'quantity': 6}]}      # 12 > 10 in total
    with pytest.raises(ValidationError):
        _remove(body, request_ctx)
    assert reload(item).quantity == 10


@pytest.mark.req('FR-07', 'FR-10')
def test_split_entries_within_the_limit_are_accepted(item, request_ctx):
    _remove({'items': [{'pk': item.pk, 'quantity': 6}, {'pk': item.pk, 'quantity': 4}]}, request_ctx)
    assert reload(item).quantity == 0


@pytest.mark.req('FR-07', 'FR-10')
def test_the_offending_entry_index_is_reported_and_nothing_is_applied(make_item, request_ctx):
    a, b = make_item(10), make_item(5)
    with pytest.raises(ValidationError) as exc:
        _remove({'items': [{'pk': a.pk, 'quantity': 3}, {'pk': b.pk, 'quantity': 9}]}, request_ctx)
    assert list(_errors(exc)['items'].keys()) == ['1']                                       # entries are validated in pk order: a, b
    assert (reload(a).quantity, reload(b).quantity) == (10, 5)                              # atomic: the valid entry was not applied


@pytest.mark.parametrize('available,shown', [(100, '100'), (10, '10'), ('10.5', '10.5'), ('0.00001', '0.00001'), (1000, '1000')])
@pytest.mark.req('FR-07', 'BR-1')
def test_over_removal_message_is_exact_and_never_uses_scientific_notation(make_item, request_ctx, available, shown):
    """Pins the exact text, so mutations of the message construction (normalize/format/placeholder) are detected."""
    s = make_item(Decimal(str(available)))
    with pytest.raises(ValidationError) as exc:
        _remove({'items': [{'pk': s.pk, 'quantity': Decimal(str(available)) + 1}]}, request_ctx)
    assert str(_errors(exc)['items']['0']['quantity'][0]) == f'Cannot remove more than the available quantity ({shown})'
