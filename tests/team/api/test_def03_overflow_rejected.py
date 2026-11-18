"""DEF-03 (overflow) is fixed: an addition whose resulting quantity cannot be stored is rejected. (Until the fix these tests stored an unrepresentable
quantity that made the item and the whole stock list unreadable and therefore had to run last; they no longer corrupt anything.)"""
import pytest
from conftest import adjust, qty

MAXQ = '9999999999.99999'


@pytest.mark.risk('PR-04')
def test_def03_fixed_overflowing_addition_is_rejected_and_the_item_stays_readable(manager, new_item):
    pk = new_item(10)
    r = adjust(manager, 'add', pk, MAXQ)
    assert r.status_code == 400 and r.json()['items']['0']['quantity'] == ['The resulting quantity must not exceed 9999999999.99999']
    assert qty(manager, pk) == 10


@pytest.mark.risk('PR-04', 'PR-01')
def test_def03_fixed_the_stock_list_stays_available(manager, new_item):
    pk = new_item(10)
    adjust(manager, 'add', pk, MAXQ)
    r = manager.get('/api/stock/?limit=1000&ordering=-pk')
    assert r.status_code == 200
