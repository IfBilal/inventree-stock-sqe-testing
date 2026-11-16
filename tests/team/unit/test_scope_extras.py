"""Remaining business-logic functions on the add/remove path: can_delete (BR-3), tracking/audit helpers (FR-02/FR-06),
the pk-prefetch field (validate_pk lookup) and the permission classes (BR-4)."""
import os, sys
from types import SimpleNamespace
import pytest
from conftest import ADD, history, reload

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'tools')))
import mcdc  # noqa: E402

pytestmark = pytest.mark.django_db
FALSE_QS = SimpleNamespace(exists=lambda: False)
TRUE_QS = SimpleNamespace(exists=lambda: True)


# =============================================================== can_delete (BR-3): every False reason + the True path
@pytest.fixture
def clear_relations(monkeypatch):
    """Neutral defaults for relations that need heavy fixtures (build allocations, orders); individual tests flip ONE of them."""
    from stock.models import StockItem
    monkeypatch.setattr(StockItem, 'allocations', property(lambda self: FALSE_QS))
    monkeypatch.setattr(StockItem, 'get_sales_order_allocations', lambda self, **k: FALSE_QS)
    monkeypatch.setattr(StockItem, 'get_transfer_order_allocations', lambda self, **k: FALSE_QS)
    monkeypatch.setattr(StockItem, 'return_order_lines', property(lambda self: FALSE_QS))
    return monkeypatch


@pytest.mark.req('BR-3')
def test_can_delete_true_when_no_blocking_relation(item):
    assert item.can_delete() is True


@pytest.mark.req('BR-3')
def test_can_delete_false_when_items_are_installed_inside(item, make_item):
    make_item(1, belongs_to=item)
    assert item.installed_item_count() == 1 and item.can_delete() is False


@pytest.mark.req('BR-3')
def test_installed_item_count_zero_without_children(item):
    assert item.installed_item_count() == 0


def test_can_delete_false_when_assigned_to_sales_order(item, markers):
    item.sales_order = markers.sales_order
    assert item.can_delete() is False


@pytest.mark.parametrize('blocker', ['allocations', 'sales_order_allocations', 'transfer_order_allocations', 'return_order_lines'])
def test_can_delete_false_for_each_remaining_blocker(blocker, item, clear_relations):
    from stock.models import StockItem
    if blocker == 'allocations':
        clear_relations.setattr(StockItem, 'allocations', property(lambda self: TRUE_QS))
    elif blocker == 'sales_order_allocations':
        clear_relations.setattr(StockItem, 'get_sales_order_allocations', lambda self, **k: TRUE_QS)
    elif blocker == 'transfer_order_allocations':
        clear_relations.setattr(StockItem, 'get_transfer_order_allocations', lambda self, **k: TRUE_QS)
    else:
        clear_relations.setattr(StockItem, 'return_order_lines', property(lambda self: TRUE_QS))
    assert item.can_delete() is False


# =============================================================== tracking helpers
@pytest.mark.parametrize('n,row,empty', [(n, r, o) for n, r, o, _ in mcdc.truth_table(mcdc.DECISIONS['TRACK-EMPTY'])],
                         ids=lambda v: None)
def test_is_empty_tracking_event_mcc(n, row, empty):
    from stock.models import StockItem
    from stock.status_codes import StockHistoryCode
    is_update, no_deltas, no_notes = row
    entry = StockHistoryCode.STOCK_UPDATE if is_update else StockHistoryCode.STOCK_ADD
    assert StockItem._is_empty_tracking_event(entry, {} if no_deltas else {'k': 1}, '' if no_notes else 'note') is empty


def test_tracking_deltas_adds_references_and_quantity(item, markers):
    d = item._tracking_deltas({'x': 1}, {'salesorder': markers.sales_order, 'quantity': 5})
    assert d['x'] == 1 and d['salesorder'] is markers.sales_order and d['quantity'] == 5.0


def test_tracking_deltas_existing_reference_wins_and_zero_quantity_is_ignored(item, markers):
    d = item._tracking_deltas({'salesorder': 'keep'}, {'salesorder': markers.sales_order, 'quantity': 0})
    assert d['salesorder'] == 'keep' and 'quantity' not in d


def test_tracking_deltas_without_kwargs_is_a_copy(item):
    src = {'a': 1}
    out = item._tracking_deltas(src, {})
    assert out == src and out is not src and item._tracking_deltas(None, {}) == {}


def test_audit_deltas_drops_ignored_keys(item):
    ignored = next(iter(item.AUDIT_IGNORE_DELTAS))
    assert item._audit_deltas({ignored: 1, 'added': 2}) == {'added': 2}


def test_tracking_event_records_a_normal_event(item, user):
    with item.tracking_event(ADD, user, deltas={'added': 3.0}, notes='n'):
        pass
    e = history(item, ADD)
    assert len(e) == 1 and e[0].additional_data['deltas']['added'] == 3.0 and e[0].notes == 'n'


def test_tracking_event_skips_empty_update_event(item, user):
    from audit.models import AuditLogEntry
    from stock.status_codes import StockHistoryCode
    before = AuditLogEntry.objects.count()
    with item.tracking_event(StockHistoryCode.STOCK_UPDATE, user):
        pass
    assert AuditLogEntry.objects.count() == before


def test_nested_tracking_event_records_only_the_outer_event(item, user):
    with item.tracking_event(ADD, user, deltas={'added': 1.0}):
        with item.tracking_event(ADD, user, deltas={'added': 99.0}):
            pass
    e = history(item, ADD)
    assert len(e) == 1 and e[0].additional_data['deltas']['added'] == 1.0


# =============================================================== PrefetchedPrimaryKeyRelatedField (the pk lookup behind validate_pk)
def _field(context):
    from InvenTree.fields import PrefetchedPrimaryKeyRelatedField
    from stock.models import StockItem
    f = PrefetchedPrimaryKeyRelatedField(cache_key='_c', queryset=StockItem.objects.all())
    f._context = context
    return f


def test_prefetch_field_uses_cache_hit(item):
    sentinel = object()
    assert _field({'_c': {item.pk: sentinel}}).to_internal_value(str(item.pk)) is sentinel


def test_prefetch_field_falls_back_to_database_when_not_cached(item):
    assert _field({'_c': {}}).to_internal_value(item.pk) == item and _field({}).to_internal_value(item.pk) == item


def test_prefetch_field_non_integer_pk_is_a_validation_error_not_a_crash():
    from rest_framework.exceptions import ValidationError
    with pytest.raises(ValidationError):
        _field({'_c': {1: object()}}).to_internal_value('abc')
    with pytest.raises(ValidationError):
        _field({'_c': {1: object()}}).to_internal_value(None)


# =============================================================== permission classes (BR-4)
def _view(**attrs):
    return SimpleNamespace(**attrs)


def _req(user, method='POST'):
    return SimpleNamespace(user=user, method=method, successful_authenticator=None)


def _grant(user, role, **rights):
    from django.contrib.auth.models import Group
    from users.models import RuleSet
    g = Group.objects.create(name=f'g-{role}-{user.pk}-{sorted(rights)}')
    rs, _ = RuleSet.objects.get_or_create(group=g, name=role)
    rs.can_view = True
    for k, v in rights.items(): setattr(rs, k, v)
    rs.save()
    user.groups.add(g)
    return user


@pytest.fixture
def perm():
    from InvenTree.permissions import RolePermission
    return RolePermission()


def test_role_permission_superuser_always_allowed(perm, django_user_model):
    su = django_user_model.objects.create_superuser('su', 's@e.test', 'p')
    assert perm.has_permission(_req(su, 'DELETE'), _view()) is True


@pytest.mark.req('BR-4')
def test_role_permission_stock_adjust_views_have_no_model_and_do_not_restrict(perm, user):
    """The stock add/remove views declare no Meta.model: RolePermission returns True (enforcement is DRF ModelPermission, see test_api_views)."""
    from stock.api import StockAdd
    assert perm.has_permission(_req(user), StockAdd()) is True


def test_role_permission_view_without_serializer_is_not_restricted(perm, user):
    assert perm.has_permission(_req(user), _view()) is True


def test_role_permission_model_none_is_not_restricted(perm, user):
    assert perm.has_permission(_req(user), _view(get_permission_model=lambda: None)) is True


@pytest.mark.req('BR-4')
def test_role_permission_role_required_without_add_right_is_denied(perm, user):
    assert perm.has_permission(_req(user), _view(role_required='stock')) is False


@pytest.mark.req('BR-4')
def test_role_permission_role_required_with_add_right_is_allowed(perm, user):
    _grant(user, 'stock', can_add=True)
    assert perm.has_permission(_req(user), _view(role_required='stock')) is True


def test_role_permission_dotted_role_overrides_method_permission(perm, user):
    _grant(user, 'stock', can_delete=True)
    assert perm.has_permission(_req(user, 'GET'), _view(role_required='stock.delete')) is True
    assert perm.has_permission(_req(user, 'GET'), _view(role_required='stock.add')) is False


def test_role_permission_custom_rolemap(perm, user):
    _grant(user, 'stock', can_change=True)
    assert perm.has_permission(_req(user, 'POST'), _view(role_required='stock', rolemap={'POST': 'change'})) is True


def test_role_permission_model_based_check_denies_user_without_permission(perm, user):
    from stock.models import StockItem
    assert perm.has_permission(_req(user, 'POST'), _view(get_permission_model=lambda: StockItem)) is False


def test_model_permission_queryset_is_cached_on_the_view():
    from InvenTree.permissions import ModelPermission
    from stock.api import StockAdd
    v = StockAdd()
    first = ModelPermission()._queryset(v)
    assert v._cached_queryset is first and ModelPermission()._queryset(v) is first
