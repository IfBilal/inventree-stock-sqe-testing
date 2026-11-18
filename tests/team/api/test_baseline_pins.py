"""Exact status codes and bodies of the fixed defects DEF-02 and DEF-04 (they were pins of the baseline behaviour (201 / HTTP 500) until the fix PR)."""
from decimal import Decimal
import pytest
from conftest import REMOVE, adjust, history, qty

MAXQ = '9999999999.99999'


@pytest.mark.risk('PR-04')
@pytest.mark.parametrize('op', ['add', 'remove'])
def test_def02_fixed_zero_quantity_is_rejected_with_a_message(op, manager, new_item):
    pk = new_item(10)
    r = adjust(manager, op, pk, 0)
    assert r.status_code == 400 and r.json()['items']['0']['quantity'] == ['Quantity must be greater than zero']
    assert qty(manager, pk) == 10 and history(manager, pk) == []


@pytest.mark.risk('PR-04')
@pytest.mark.parametrize('bad', [None, 'abc', 5], ids=['null', 'string', 'int'])
def test_def04_fixed_malformed_items_return_400_not_500(bad, manager):
    r = manager.post('/api/stock/add/', json={'items': bad})
    assert r.status_code == 400 and 'items' in r.json()
