"""DEF-06 fix (SQLite IMMEDIATE transactions): five clients adjusting the SAME item at the same time all succeed and no unit is lost or duplicated.
Baseline (before the fix): ~19.5 % of such requests answered HTTP 500 'database is locked' (reports/performance/concurrency_probe.txt)."""
from concurrent.futures import ThreadPoolExecutor
import pytest
import requests
from conftest import BASE, qty

pytestmark = pytest.mark.risk('PR-08')


def _remove_one(pk):
    return requests.post(BASE + '/api/stock/remove/', json={'items': [{'pk': pk, 'quantity': '1'}]}, auth=('manager', 'manager12345'), timeout=60).status_code


def test_concurrent_removals_from_one_item_all_succeed_and_the_final_quantity_is_exact(manager, new_item):
    pk = new_item(1000)
    with ThreadPoolExecutor(max_workers=5) as pool:
        codes = list(pool.map(_remove_one, [pk] * 100))
    assert codes.count(201) == 100, {c: codes.count(c) for c in set(codes)}
    assert qty(manager, pk) == 900
    hist = manager.get(f'/api/audit/?model_type=stock.stockitem&event_type=12&limit=1000').json()['results']
    assert sum(1 for e in hist if str(e['object_pk']) == str(pk)) == 100            # exactly one history entry per request


def test_concurrent_over_removal_never_makes_the_quantity_negative(manager, new_item):
    pk = new_item(10)
    with ThreadPoolExecutor(max_workers=5) as pool:
        codes = list(pool.map(_remove_one, [pk] * 25))
    ok = codes.count(201)
    assert ok == 10 and codes.count(400) == 15 and qty(manager, pk) == 0, {c: codes.count(c) for c in set(codes)}
