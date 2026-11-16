"""PINNED baseline behaviour of the defects (exact status codes and bodies). The strict-xfail generated cases only prove 'expected != actual';
these tests pin WHAT the baseline actually does, so a xfail cannot hide a different failure. They must be updated/removed in the fix PR."""
from decimal import Decimal
import pytest
from conftest import REMOVE, adjust, history, qty

MAXQ = '9999999999.99999'


@pytest.mark.risk('PR-04')
@pytest.mark.parametrize('op', ['add', 'remove'])
def test_pin_def02_zero_quantity_returns_201_without_effect(op, manager, new_item):
    pk = new_item(10)
    assert adjust(manager, op, pk, 0).status_code == 201 and qty(manager, pk) == 10 and history(manager, pk) == []


@pytest.mark.risk('PR-04')
@pytest.mark.parametrize('bad, error', [(None, 'TypeError'), ('abc', 'AttributeError'), (5, 'TypeError')], ids=['null', 'string', 'int'])
def test_pin_def04_malformed_items_returns_500_with_exception_class(bad, error, manager):
    r = manager.post('/api/stock/add/', json={'items': bad})
    assert r.status_code == 500 and r.json()['error'] == error
