"""StockItem.is_in_stock — EQUIVALENCE PARTITIONS of the status value (BR-2). The boolean decisions of is_in_stock (status, location, quantity,
production flags) are covered once, as complete MCC rows, in test_mcc_other_decisions.py — not repeated here."""
import pytest

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('status', [10, 50, 55, 85], ids=['OK', 'attention', 'damaged', 'returned'])
def test_available_status_partition_counts_as_in_stock(item, status):
    item.status = status
    assert item.is_in_stock() is True


@pytest.mark.parametrize('status', [60, 65, 70, 75], ids=['destroyed', 'rejected', 'lost', 'quarantined'])
def test_unavailable_status_partition_is_not_in_stock(item, status):
    item.status = status
    assert item.is_in_stock() is False
