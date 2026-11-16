"""Failure-and-recovery test (project statement §5): a state-changing operation (Remove stock through the API view) is interrupted by a
dependency becoming unavailable BEFORE the write completes (test double = the audit/history writer raises a database error). We verify the persisted
state after the failure (nothing half-written), restore the dependency, RETRY the same request and assert the expected final state with NO duplicate records."""
from contextlib import contextmanager
from decimal import Decimal
import pytest
from django.db import OperationalError
from rest_framework.test import APIClient
from conftest import REMOVE, history, reload

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def admin_client(django_user_model):
    u = django_user_model.objects.create_superuser('rootrec', 'r@example.test', 'pw')
    c = APIClient(raise_request_exception=False)       # a server error must be observable as HTTP 500, not re-raised
    c.force_authenticate(user=u)
    return c


def _unavailable(when):
    """Test double for the history writer (`StockItem.tracking_event`): unavailable before the write ('enter') or after the quantity was
    saved but before the transaction completes ('exit')."""
    @contextmanager
    def double(self, *a, **kw):
        if when == 'enter':
            raise OperationalError('history store unavailable (test double)')
        yield
        raise OperationalError('history store lost the connection before commit (test double)')
    return double


@pytest.mark.req('FR-05', 'FR-06', 'FR-10')
@pytest.mark.risk('PR-06', 'PR-05', 'PR-07')
@pytest.mark.parametrize('when', ['enter', 'exit'])
def test_remove_fails_then_recovers_without_duplicates(when, admin_client, item, monkeypatch):
    from stock.models import StockItem
    body = {'items': [{'pk': item.pk, 'quantity': 4}]}

    # 1. the dependency becomes unavailable before the write completes
    with monkeypatch.context() as m:
        m.setattr(StockItem, 'tracking_event', _unavailable(when))
        r = admin_client.post('/api/stock/remove/', body, format='json')
        assert r.status_code == 500

    # 2. persisted state after the failure: atomic rollback — nothing half-written
    assert reload(item).quantity == Decimal(10)
    assert history(item, REMOVE) == []

    # 3. dependency restored (the double is undone by the context manager) -> retry the SAME request
    r = admin_client.post('/api/stock/remove/', body, format='json')
    assert r.status_code == 201

    # 4. expected final state: removed exactly once, exactly one history entry (no duplicates)
    assert reload(item).quantity == Decimal(6)
    entries = history(item, REMOVE)
    assert len(entries) == 1 and entries[0].additional_data['deltas']['removed'] == 4.0


@pytest.mark.req('FR-10')
@pytest.mark.risk('PR-05')
def test_multi_item_request_failure_leaves_every_item_untouched_then_retry_applies_each_once(admin_client, make_item, monkeypatch):
    from stock.models import StockItem
    a, b = make_item(10), make_item(20)
    body = {'items': [{'pk': a.pk, 'quantity': 1}, {'pk': b.pk, 'quantity': 2}]}
    with monkeypatch.context() as m:
        m.setattr(StockItem, 'tracking_event', _unavailable('exit'))
        assert admin_client.post('/api/stock/remove/', body, format='json').status_code == 500
    assert (reload(a).quantity, reload(b).quantity) == (10, 20)                      # all-or-nothing
    assert admin_client.post('/api/stock/remove/', body, format='json').status_code == 201
    assert (reload(a).quantity, reload(b).quantity) == (9, 18)
    assert len(history(a, REMOVE)) == 1 and len(history(b, REMOVE)) == 1
