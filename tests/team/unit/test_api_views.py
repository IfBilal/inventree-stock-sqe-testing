"""Thin view layer (StockAdjustView / StockAdd / StockRemove) exercised through DRF's test client (FR-09, BR-4)."""
import pytest
from rest_framework.test import APIClient
from conftest import reload

pytestmark = pytest.mark.django_db
ADD_URL, REMOVE_URL = '/api/stock/add/', '/api/stock/remove/'


def _client(user=None):
    c = APIClient()
    if user:
        c.force_authenticate(user=user)
    return c


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_superuser('root', 'r@example.test', 'pw')


@pytest.mark.req('FR-01', 'FR-09')
def test_superuser_add_returns_201_and_changes_quantity(admin, item):
    r = _client(admin).post(ADD_URL, {'items': [{'pk': item.pk, 'quantity': 3}]}, format='json')
    assert r.status_code == 201 and reload(item).quantity == 13


@pytest.mark.req('FR-05', 'FR-09')
def test_superuser_remove_returns_201_and_changes_quantity(admin, item):
    r = _client(admin).post(REMOVE_URL, {'items': [{'pk': item.pk, 'quantity': 3}]}, format='json')
    assert r.status_code == 201 and reload(item).quantity == 7


@pytest.mark.req('FR-09', 'BR-4')
@pytest.mark.parametrize('url', [ADD_URL, REMOVE_URL])
def test_user_without_stock_add_right_gets_403_and_no_change(url, user, item):
    r = _client(user).post(url, {'items': [{'pk': item.pk, 'quantity': 3}]}, format='json')
    assert r.status_code == 403 and reload(item).quantity == 10


@pytest.mark.req('FR-09')
@pytest.mark.parametrize('url', [ADD_URL, REMOVE_URL])
def test_unauthenticated_request_is_rejected(url, item):
    r = _client().post(url, {'items': [{'pk': item.pk, 'quantity': 3}]}, format='json')
    assert r.status_code in (401, 403) and reload(item).quantity == 10
