"""API/integration tests for BR-1..BR-4, state transitions, cross-workflow sequences and read-back of shared records
(StockItem.quantity and the audit history) after BOTH success and rejection (R-24)."""
from decimal import Decimal
import pytest
from conftest import ADD, REMOVE, adjust, history, qty

D = Decimal


# =============================================================== BR-4 / FR-09: access decisions (role x endpoint)
@pytest.mark.req('BR-4', 'FR-09')
@pytest.mark.risk('PR-02')
@pytest.mark.parametrize('role,status', [('manager', 201), ('viewer', 403), ('anon', 401)])
@pytest.mark.parametrize('op', ['add', 'remove'])
def test_role_decision_and_read_back(request, role, status, op, new_item, manager):
    client = request.getfixturevalue(role)
    pk = new_item(10)
    r = adjust(client, op, pk, 1)
    assert r.status_code == status
    expected = D(10) + (1 if op == 'add' else -1) if status == 201 else D(10)
    assert qty(manager, pk) == expected
    assert len(history(manager, pk)) == (1 if status == 201 else 0)


@pytest.mark.req('BR-4')
def test_viewer_can_read_but_not_write(viewer, new_item):
    pk = new_item(10)
    assert viewer.get(f'/api/stock/{pk}/').status_code == 200
    assert adjust(viewer, 'add', pk, 1).status_code == 403


@pytest.mark.req('BR-4')
def test_invalid_credentials_are_rejected(new_item):
    import requests
    from conftest import BASE
    pk = new_item(10)
    r = requests.post(BASE + '/api/stock/add/', json={'items': [{'pk': pk, 'quantity': '1'}]}, auth=('manager', 'wrong'), timeout=30)
    assert r.status_code == 401


# =============================================================== BR-2 / FR-04: non-adjustable item (installed in another item)
@pytest.mark.req('BR-2', 'FR-04')
@pytest.mark.risk('PR-03')
@pytest.mark.parametrize('op', ['add', 'remove'])
def test_installed_item_is_rejected_unchanged(op, new_item, admin, manager):
    parent, child = new_item(1), new_item(10)
    r = admin.request('PATCH', f'/api/stock/{child}/', json={'belongs_to': parent})
    assert r.status_code == 200, r.text
    resp = adjust(manager, op, child, 1)
    assert resp.status_code == 400 and 'not in stock' in resp.text
    assert qty(manager, child) == 10 and history(manager, child) == []


# =============================================================== BR-3 / FR-08: state transitions (read back the shared record)
@pytest.mark.req('BR-3', 'FR-08')
@pytest.mark.risk('PR-01')
def test_depletion_retains_item_at_zero_when_flag_false(new_item, manager):
    pk = new_item(5)
    assert adjust(manager, 'remove', pk, 5).status_code == 201
    assert qty(manager, pk) == 0


@pytest.mark.req('BR-3', 'FR-08')
@pytest.mark.seq('S3-deplete-delete')
def test_depletion_deletes_item_when_flag_true_and_history_survives(new_item, manager):
    pk = new_item(5, delete_on_deplete=True)
    assert adjust(manager, 'remove', pk, 5).status_code == 201
    assert qty(manager, pk) is None                                    # GET -> 404
    assert len(history(manager, pk, REMOVE)) == 1


@pytest.mark.req('BR-3')
@pytest.mark.seq('S4-delete-then-adjust')
def test_deleted_item_cannot_be_adjusted(new_item, manager):
    pk = new_item(5, delete_on_deplete=True)
    adjust(manager, 'remove', pk, 5)
    for op in ('add', 'remove'):
        r = adjust(manager, op, pk, 1)
        assert r.status_code == 400 and 'does not exist' in r.text


@pytest.mark.req('BR-3', 'FR-01')
@pytest.mark.seq('S2-deplete-restock')
def test_restock_of_depleted_item(new_item, manager):
    pk = new_item(0)
    assert adjust(manager, 'add', pk, 8).status_code == 201
    assert qty(manager, pk) == 8


@pytest.mark.req('BR-3')
def test_remove_from_depleted_item_is_ignored(new_item, manager):
    pk = new_item(0)
    assert adjust(manager, 'remove', pk, 1).status_code == 201         # documented upstream behaviour: silent no-op
    assert qty(manager, pk) == 0 and history(manager, pk) == []


# =============================================================== cross-workflow sequences (shared record)
@pytest.mark.req('FR-01', 'FR-05', 'FR-02', 'FR-06')
@pytest.mark.risk('PR-07')
@pytest.mark.seq('S1-add-remove-add')
def test_add_remove_add_sequence_updates_balance_and_history_in_order(new_item, manager):
    pk = new_item(10)
    for op, q in (('add', 5), ('remove', 3), ('add', 2)):
        assert adjust(manager, op, pk, q).status_code == 201
    assert qty(manager, pk) == 14
    types = [e['event_type'] for e in sorted(history(manager, pk), key=lambda e: e['pk'])]
    assert types == [ADD, REMOVE, ADD]


@pytest.mark.req('FR-02')
def test_history_entry_matches_the_request(new_item, manager):
    pk = new_item(10)
    manager.post('/api/stock/add/', json={'items': [{'pk': pk, 'quantity': '2.5'}], 'notes': 'restock'})
    e = history(manager, pk, ADD)[0]
    assert e['notes'] == 'restock' and e['deltas']['added'] == 2.5 and e['actor_username'] == 'manager'


# =============================================================== repeated requests / duplicates / atomicity (PR-05, PR-06)
@pytest.mark.req('FR-05', 'FR-06')
@pytest.mark.risk('PR-06')
@pytest.mark.seq('S6-repeat-valid')
def test_repeating_a_valid_request_applies_it_once_per_request_no_duplicate_history(new_item, manager):
    pk = new_item(10)
    for _ in range(3):
        assert adjust(manager, 'remove', pk, 2).status_code == 201
    assert qty(manager, pk) == 4 and len(history(manager, pk, REMOVE)) == 3      # one entry per request, none duplicated


@pytest.mark.req('FR-03a')
@pytest.mark.risk('PR-06')
@pytest.mark.seq('S5-reject-retry')
def test_repeating_a_rejected_request_leaves_no_trace(new_item, manager):
    pk = new_item(10)
    for _ in range(3):
        assert adjust(manager, 'add', pk, -1).status_code == 400
    assert qty(manager, pk) == 10 and history(manager, pk) == []


@pytest.mark.req('FR-10')
@pytest.mark.risk('PR-05')
@pytest.mark.seq('S7-atomic-multi')
def test_multi_item_request_is_atomic_when_one_item_is_invalid(new_item, manager):
    a = new_item(10)
    r = manager.post('/api/stock/add/', json={'items': [{'pk': a, 'quantity': '1'}, {'pk': 999999999, 'quantity': '1'}]})
    assert r.status_code == 400 and qty(manager, a) == 10 and history(manager, a) == []


@pytest.mark.req('FR-10')
def test_multi_item_request_applies_every_item(new_item, manager):
    a, b = new_item(10), new_item(20)
    r = manager.post('/api/stock/remove/', json={'items': [{'pk': a, 'quantity': '1'}, {'pk': b, 'quantity': '2'}]})
    assert r.status_code == 201 and (qty(manager, a), qty(manager, b)) == (9, 18)


@pytest.mark.req('FR-07', 'BR-1')
@pytest.mark.risk('PR-01')
@pytest.mark.xfail(strict=True, raises=AssertionError, reason='DEF-01 (variant): duplicate pk entries whose SUM exceeds the available quantity are clamped, not rejected')
def test_duplicate_pk_entries_exceeding_available_are_rejected(new_item, manager):
    pk = new_item(10)
    r = manager.post('/api/stock/remove/', json={'items': [{'pk': pk, 'quantity': '6'}, {'pk': pk, 'quantity': '6'}]})
    assert r.status_code == 400 and qty(manager, pk) == 10


@pytest.mark.req('FR-11')
def test_serialized_item_is_unchanged_by_add_and_remove(admin, manager):
    r = admin.post('/api/part/', json={'name': 'Serial Keyboard', 'description': 'trackable', 'category': 1, 'trackable': True})
    assert r.status_code == 201, r.text
    part = r.json()['pk']
    r = admin.post('/api/stock/', json={'part': part, 'location': 1, 'quantity': '1', 'serial_numbers': 'A-1'})
    assert r.status_code == 201, r.text
    data = r.json()
    item = (data[0] if isinstance(data, list) else data)
    assert item['serial'] == 'A-1'                                   # really serialized
    pk = item['pk']
    for op in ('add', 'remove'):
        assert adjust(manager, op, pk, 1).status_code == 201         # upstream: accepted silently
    assert qty(manager, pk) == 1 and history(manager, pk) == []      # but nothing changes (FR-11)
