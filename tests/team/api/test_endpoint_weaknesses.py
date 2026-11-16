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


def test_w05_500_error_body_hides_internal_details_but_reports_exception_class(manager):
    """W-05 (DEF-04): unhandled exceptions leak the Python exception class name to clients (information disclosure, minor)."""
    r = manager.post('/api/stock/add/', json={'items': None})
    assert r.status_code == 500 and r.json()['error'] == 'TypeError'


def test_session_is_not_required_stateless_basic_auth(manager):
    assert requests.get(BASE + '/api/stock/', auth=('manager', 'manager12345'), timeout=30).status_code == 200


def test_w06_audit_endpoint_silently_ignores_the_object_pk_filter(manager, new_item):
    """W-06: `object_pk` is not a supported filter and is silently ignored (returns every item's entries) — clients that trust it read other items' history."""
    a, b = new_item(10), new_item(10)
    adjust(manager, 'add', a, 1)
    adjust(manager, 'add', b, 1)
    r = manager.get(f'/api/audit/?model_type=stock.stockitem&event_type=11&object_pk={a}&limit=1000')
    assert r.status_code == 200 and {str(e['object_pk']) for e in r.json()['results']} >= {str(a), str(b)}
