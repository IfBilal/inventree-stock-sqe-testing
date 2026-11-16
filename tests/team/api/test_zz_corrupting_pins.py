"""Pins of DEF-03 (overflow). These tests CORRUPT data on purpose and therefore run last (marker corrupts_db); the DB is reset by the runner scripts."""
import pytest
from conftest import adjust, qty

MAXQ = '9999999999.99999'
pytestmark = pytest.mark.corrupts_db


@pytest.mark.risk('PR-04')
def test_pin_def03_overflow_makes_the_item_unreadable(manager, new_item):
    pk = new_item(10)
    assert adjust(manager, 'add', pk, MAXQ).status_code == 201                    # accepted although the total is not representable
    r = manager.get(f'/api/stock/{pk}/', validate_schema=False)
    assert r.status_code == 500 and r.json()['error'] == 'InvalidOperation'


@pytest.mark.risk('PR-04', 'PR-01')
def test_pin_def03_one_corrupted_item_breaks_the_whole_stock_list(manager, new_item):
    """Impact escalation of DEF-03: `GET /api/stock/` (the stock table of the UI) answers HTTP 500 for every user while the item exists."""
    pk = new_item(10)
    adjust(manager, 'add', pk, MAXQ)
    r = manager.get('/api/stock/?limit=1000&ordering=-pk', validate_schema=False)
    assert r.status_code == 500 and r.json()['error'] == 'InvalidOperation'
