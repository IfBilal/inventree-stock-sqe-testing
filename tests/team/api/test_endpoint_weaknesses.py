"""Endpoint robustness probes (R-24 'Report endpoint weaknesses'): each test asserts the OBSERVED behaviour of the baseline
and the weakness it demonstrates is listed in docs/API_TESTING.md (W-xx)."""
import pytest
import requests
from conftest import BASE, adjust, history, qty


@pytest.mark.parametrize('method', ['GET', 'PUT', 'PATCH', 'DELETE'])
@pytest.mark.parametrize('op', ['add', 'remove'])
def test_unsupported_methods_return_405(method, op, manager):
    assert manager.request(method, f'/api/stock/{op}/', json={}).status_code == 405


@pytest.mark.parametrize('op', ['add', 'remove'])
def test_unsupported_content_type_is_rejected_with_415(op, manager, new_item):
    pk = new_item(10)
    r = manager.post(f'/api/stock/{op}/', data='{"items":[{"pk":%d,"quantity":"1"}]}' % pk, headers={'Content-Type': 'text/plain'})
    assert r.status_code == 415 and qty(manager, pk) == 10


def test_w01_success_response_does_not_report_the_new_balance(manager, new_item):
    """W-01: the 201 body only echoes the request; clients must issue a second GET to learn the resulting quantity."""
    pk = new_item(10)
    r = adjust(manager, 'add', pk, 1)
    assert r.status_code == 201 and r.json()['items'][0]['quantity'] == '1.00000' and 'balance' not in r.text


def test_w02_unknown_top_level_fields_are_silently_ignored(manager, new_item):
    """W-02: unknown fields are accepted (no strict schema) — typos such as 'note' instead of 'notes' go unnoticed."""
    pk = new_item(10)
    r = manager.post('/api/stock/add/', json={'items': [{'pk': pk, 'quantity': '1'}], 'note': 'typo', 'foo': 1})
    assert r.status_code == 201 and history(manager, pk)[0]['notes'] in (None, '')


def test_w03_no_idempotency_key_a_retried_request_is_applied_again(manager, new_item):
    """W-03: PR-06 — the API has no idempotency mechanism: a client retry after a lost response double-applies."""
    pk = new_item(10)
    body = {'items': [{'pk': pk, 'quantity': '1'}]}
    for _ in range(2):
        assert manager.post('/api/stock/add/', json=body, headers={'Idempotency-Key': 'abc'}).status_code == 201
    assert qty(manager, pk) == 12


def test_w04_pk_given_as_numeric_string_is_accepted(manager, new_item):
    """W-04: loose typing — pk '1' (string) is coerced to an integer."""
    pk = new_item(10)
    r = manager.post('/api/stock/add/', json={'items': [{'pk': str(pk), 'quantity': '1'}]})
    assert r.status_code == 201 and qty(manager, pk) == 11


def test_error_body_identifies_the_failing_field(manager, new_item):
    pk = new_item(10)
    r = adjust(manager, 'add', pk, -1)
    assert r.status_code == 400 and 'quantity' in r.json()['items']['0']


def test_w05_malformed_request_no_longer_leaks_the_exception_class(manager):
    """W-05 (DEF-04, fixed): malformed `items` is now a regular 400 validation error without an exception class name."""
    r = manager.post('/api/stock/add/', json={'items': None})
    assert r.status_code == 400 and 'error' not in r.json()


def test_session_is_not_required_stateless_basic_auth(manager, new_item):
    pk = new_item(10)
    assert requests.get(BASE + f'/api/stock/{pk}/', auth=('manager', 'manager12345'), timeout=30).status_code == 200


def test_w06_audit_endpoint_silently_ignores_the_object_pk_filter(manager, new_item):
    """W-06: `object_pk` is not a supported filter and is silently ignored (returns every item's entries) — clients that trust it read other items' history."""
    a, b = new_item(10), new_item(10)
    adjust(manager, 'add', a, 1)
    adjust(manager, 'add', b, 1)
    r = manager.get(f'/api/audit/?model_type=stock.stockitem&event_type=11&object_pk={a}&limit=1000')
    assert r.status_code == 200 and {str(e['object_pk']) for e in r.json()['results']} >= {str(a), str(b)}


def test_w08_boolean_field_accepts_integers(manager, new_item):
    """W-08: `merge` is a boolean but integers 0/1 are accepted (loose typing; the contract says boolean)."""
    pk = new_item(10)
    assert manager.post('/api/stock/add/', json={'items': [{'pk': pk, 'quantity': '1', 'merge': 1}]}).status_code == 201


def test_w09_audit_query_parameters_are_not_validated(manager):
    """W-09: invalid values for documented query parameters (event_type=999, limit=-1) are accepted, not rejected with 400."""
    r0 = manager.get('/api/audit/?model_type=stock.stockitem&event_type=999', validate_schema=False)
    assert r0.status_code == 200 and isinstance(r0.json(), list)       # an out-of-enum event_type is accepted and also yields a bare list
    r = manager.get('/api/audit/?model_type=stock.stockitem&limit=-1', validate_schema=False)
    assert r.status_code == 200 and isinstance(r.json(), list)          # ...and an invalid limit silently DISABLES pagination: a bare list instead of {count, results}


def test_w10_get_returns_quantity_as_json_float_while_writes_use_decimal_strings(manager, new_item):
    """W-10: precision hazard — `GET /api/stock/{id}/` serialises quantity as a JSON float (10.0) although inputs are decimal strings."""
    pk = new_item('10.12345')
    raw = manager.get(f'/api/stock/{pk}/').json()['quantity']
    assert isinstance(raw, float)


def test_w11_unknown_pk_in_a_write_returns_400_not_404(manager):
    """W-11: a missing referenced item yields 400 ("Invalid pk … does not exist") — acceptable for a body reference but inconsistent with GET (404)."""
    assert manager.post('/api/stock/add/', json={'items': [{'pk': 999999999, 'quantity': '1'}]}).status_code == 400
    assert manager.get('/api/stock/999999999/').status_code == 404


def test_w12_boolean_true_is_accepted_as_pk_1(manager):
    """W-12: JSON `true` is coerced to the integer 1 and addresses the seeded item with pk 1 (Python bool is an int)."""
    r = manager.post('/api/stock/add/', json={'items': [{'pk': True, 'quantity': '1'}]})
    assert r.status_code == 201


def test_w13_echo_reports_pk_null_when_the_adjustment_deleted_the_item(manager, new_item):
    """W-13: when a removal depletes and deletes the item the 201 echo contains `pk: null` — the client cannot tell which item was adjusted."""
    pk = new_item(5, delete_on_deplete=True)
    r = adjust(manager, 'remove', pk, 5)
    assert r.status_code == 201 and r.json()['items'][0]['pk'] is None
