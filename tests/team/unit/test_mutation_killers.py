"""Tests added after the FIRST mutation round (docs/MUTATION.md): each kills a surviving mutant that review showed to be killable
(ids M0xx refer to evidence/mutation/results_round1.json). Equivalent survivors are documented, not killed."""
from decimal import Decimal
from types import SimpleNamespace
import pytest
from conftest import ADD, reload

pytestmark = pytest.mark.django_db
FALSE_QS = SimpleNamespace(exists=lambda: False)


# ---- M031, M032: the pk prefetch performs ONE bulk query instead of one query per item (to_internal_value)
def test_prefetch_loads_all_referenced_items_with_a_single_stock_query(make_item, request_ctx):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext
    from stock.serializers import StockAddSerializer
    items = [make_item(1) for _ in range(6)]
    s = StockAddSerializer(data={'items': [{'pk': i.pk, 'quantity': 1} for i in items]}, context=request_ctx)
    with CaptureQueriesContext(connection) as ctx:
        s.is_valid(raise_exception=True)
    stock_selects = [q for q in ctx.captured_queries if 'FROM "stock_stockitem"' in q['sql'] and q['sql'].lstrip().upper().startswith('SELECT')]
    assert len(stock_selects) <= 2, f'{len(stock_selects)} stock queries for 6 items (prefetch broken)'
    assert '_stockitems' in s.context and set(s.context['_stockitems']) == {i.pk for i in items}


# ---- M106: a quantity change publishes the ITEM_QUANTITY_UPDATED event
def test_update_quantity_triggers_the_quantity_updated_event(item, monkeypatch):
    from stock.events import StockEvents
    calls = []
    monkeypatch.setattr('stock.models.trigger_event', lambda *a, **k: calls.append((a, k)))
    assert item.updateQuantity(7) is True
    assert calls == [((StockEvents.ITEM_QUANTITY_UPDATED,), {'id': item.pk, 'quantity': 7.0})]


# ---- M149, M150, M151: _apply_status_change records every delta of its contract
def test_apply_status_change_fills_all_status_deltas(item):
    deltas = {}
    item._apply_status_change(55, deltas)
    assert deltas == {'status': 55, 'status_logical': 55, 'old_status': 10, 'old_status_logical': 10}


# ---- M155: _apply_optional_transfer_fields records each applied field in the deltas
def test_apply_optional_transfer_fields_records_deltas_and_applies_values(item):
    deltas = {}
    item._apply_optional_transfer_fields({'batch': 'B1', 'packaging': 'P1', 'status': 55, 'ignored': 'x'}, deltas)
    assert deltas == {'batch': 'B1', 'packaging': 'P1', 'status': 55}
    assert (item.batch, item.packaging, item.status) == ('B1', 'P1', 55)


# ---- M166, M167: can_delete asks for ACTIVE allocations only (the stubs record the arguments)
def test_can_delete_queries_only_active_allocations(item, monkeypatch):
    from stock.models import StockItem
    seen = {}
    monkeypatch.setattr(StockItem, 'allocations', property(lambda self: FALSE_QS))
    monkeypatch.setattr(StockItem, 'return_order_lines', property(lambda self: FALSE_QS))
    monkeypatch.setattr(StockItem, 'get_sales_order_allocations', lambda self, **k: seen.setdefault('sales', k) and FALSE_QS)
    monkeypatch.setattr(StockItem, 'get_transfer_order_allocations', lambda self, **k: seen.setdefault('transfer', k) and FALSE_QS)
    assert item.can_delete() is True
    assert seen == {'sales': {'active': True}, 'transfer': {'active': True}}


# ---- M170, M171, M172: save() validates uniqueness, cleans the item and maintains serial_int
def test_save_rejects_a_duplicate_serial_number_for_the_same_part(part):
    from django.core.exceptions import ValidationError
    from stock.models import StockItem
    StockItem.objects.create(part=part, quantity=1, serial='DUP-1')
    with pytest.raises(ValidationError):
        StockItem.objects.create(part=part, quantity=1, serial='DUP-1')


def test_save_runs_clean_an_item_cannot_belong_to_itself(item):
    from django.core.exceptions import ValidationError
    item.belongs_to = item
    with pytest.raises(ValidationError, match='cannot belong to itself'):
        item.save()


def test_save_updates_the_integer_serial(part):
    from stock.models import StockItem
    s = StockItem.objects.create(part=part, quantity=1, serial='15')
    assert reload(s).serial_int == 15


# ---- M179: an update saved inside a pending event adds NO second audit entry of its own
def test_update_save_inside_a_pending_event_adds_exactly_one_audit_entry(item, user):
    from audit.models import AuditLogEntry
    before = AuditLogEntry.objects.filter(object_pk=str(item.pk)).count()
    with item.tracking_event(ADD, user, deltas={'added': 1.0}):
        item.quantity = 14
        item.save(user=user, notes='inner')
    assert AuditLogEntry.objects.filter(object_pk=str(item.pk)).count() == before + 1


# ---- M009/M010 (validate_pk) and M189 (delete): `get_global_setting(..., cache=False)` — the setting is read FRESH on every call
def test_validate_pk_reads_the_allow_out_of_stock_setting_fresh_each_time(item, markers):
    from common.models import InvenTreeSetting
    from rest_framework.exceptions import ValidationError
    from stock.serializers import StockAdjustmentItemSerializer as S
    item.customer = markers.customer                      # a non-adjustable item (BR-2)
    key = 'STOCK_ALLOW_OUT_OF_STOCK_TRANSFER'
    for value, rejected in ((False, True), (True, False), (False, True)):
        InvenTreeSetting.set_setting(key, value, None)
        if rejected:
            with pytest.raises(ValidationError):
                S(require_in_stock=True).validate_pk(item)
        else:
            assert S(require_in_stock=True).validate_pk(item) is item


def test_delete_reads_the_allow_delete_serialized_setting_fresh_each_time(make_item):
    from common.models import InvenTreeSetting
    from django.core.exceptions import ValidationError
    key = 'STOCK_ALLOW_DELETE_SERIALIZED'
    InvenTreeSetting.set_setting(key, False, None)
    s = make_item(1, serial='SET-1')
    with pytest.raises(ValidationError):
        s.delete()
    InvenTreeSetting.set_setting(key, True, None)
    s.delete()                                            # now allowed: a stale cached False would still refuse
    InvenTreeSetting.set_setting(key, False, None)
    t = make_item(1, serial='SET-2')
    with pytest.raises(ValidationError):
        t.delete()
