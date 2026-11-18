"""The superuser role (C4 role coverage): an administrator may add and remove stock (BR-4 allowed decision for a third role)."""
import pytest
from conftest import adjust, qty

pytestmark = pytest.mark.risk('PR-02')


@pytest.mark.req('BR-4', 'FR-09')
def test_admin_can_add_and_remove_stock(admin, new_item):
    pk = new_item(10)
    assert adjust(admin, 'add', pk, 3).status_code == 201 and qty(admin, pk) == 13
    assert adjust(admin, 'remove', pk, 5).status_code == 201 and qty(admin, pk) == 8
