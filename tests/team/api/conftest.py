"""Fixtures for API/integration tests: a live InvenTree server (scripts/start.sh), seeded by scripts/reset.sh.
Every request is logged to evidence/api/request_log.jsonl (used by tools/api_coverage.py)."""
import json, os, re
from decimal import Decimal
import pytest
import requests
from schema_check import validate as schema_validate, response_schema

BASE = os.environ.get('API_BASE', 'http://127.0.0.1:8000')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
LOG = os.path.join(ROOT, 'evidence', 'api', 'request_log.jsonl')
USERS = {'admin': ('admin', 'admin12345'), 'manager': ('manager', 'manager12345'), 'viewer': ('viewer', 'viewer12345'), 'anon': None}
ADD, REMOVE = 11, 12
_LOG = []


def template(path):
    return re.sub(r'/\d+/', '/{id}/', path.split('?')[0])


class Client:
    def __init__(self, role):
        self.role = role
        self.s = requests.Session()
        if USERS[role]:
            self.s.auth = USERS[role]

    def request(self, method, path, **kw):
        validate = kw.pop('validate_schema', True)     # weakness probes opt out: their point is that the response violates the contract
        r = self.s.request(method, BASE + path, timeout=30, **kw)
        tpl = template(path)
        checked = validate and response_schema(method, tpl, r.status_code) is not None
        if checked:
            try:
                err = schema_validate(method, tpl, r.status_code, r.json())
            except ValueError:
                err = 'response is not JSON'
            assert err is None, f'response of {method} {tpl} [{r.status_code}] violates the OpenAPI schema: {err}'
        _LOG.append({'role': self.role, 'method': method.upper(), 'path': tpl, 'status': r.status_code, 'schema_checked': checked,
                     'content_type': (kw.get('headers') or {}).get('Content-Type', 'application/json' if 'json' in kw else None)})
        return r

    def get(self, path, **kw): return self.request('GET', path, **kw)
    def post(self, path, **kw): return self.request('POST', path, **kw)


@pytest.fixture(scope='session', autouse=True)
def _server_and_log():
    try:
        status = requests.get(BASE + '/api/', timeout=10).status_code
    except requests.RequestException as e:  # pragma: no cover
        pytest.exit(f'server not reachable at {BASE}: run scripts/start.sh ({e})')
    if status != 200:  # pragma: no cover
        pytest.exit(f'server at {BASE} answered HTTP {status}: run scripts/start.sh')
    yield
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a' if os.environ.get('API_LOG_APPEND') == '1' else 'w') as f:
        for rec in _LOG:
            f.write(json.dumps(rec, sort_keys=True) + '\n')


@pytest.fixture(scope='session')
def admin(): return Client('admin')
@pytest.fixture(scope='session')
def manager(): return Client('manager')
@pytest.fixture(scope='session')
def viewer(): return Client('viewer')
@pytest.fixture(scope='session')
def anon(): return Client('anon')


@pytest.fixture
def new_item(admin):
    """Create a fresh StockItem of the seeded 'Keyboard' part (pk 1) at location 1; returns its pk. Order-independent tests."""
    def _make(quantity='10', **extra):
        body = {'part': 1, 'location': 1, 'quantity': str(quantity), 'delete_on_deplete': False, **extra}
        r = admin.post('/api/stock/', json=body)
        assert r.status_code == 201, r.text
        data = r.json()
        return (data[0] if isinstance(data, list) else data)['pk']
    return _make


def qty(client, pk):
    """Read back the shared record: StockItem.quantity (None when the item does not exist)."""
    r = client.get(f'/api/stock/{pk}/')
    if r.status_code == 404:
        return None
    assert r.status_code == 200, r.text
    return Decimal(str(r.json()['quantity']))


def history(client, pk, code=None):
    """Read back history entries (audit log) for ONE stock item, optionally for one event type (11 add / 12 remove).
    NOTE: the audit endpoint silently ignores the `object_pk` query filter (weakness W-06), so entries are filtered client-side."""
    out = []
    for c in ([code] if code else [ADD, REMOVE]):
        url = f'/api/audit/?model_type=stock.stockitem&event_type={c}&limit=1000'
        while url:
            r = client.get(url)
            assert r.status_code == 200, r.text
            data = r.json()
            out += [e for e in data['results'] if str(e['object_pk']) == str(pk)]
            nxt = data.get('next')
            url = nxt.replace(BASE, '') if nxt else None
    return out


def adjust(client, op, pk, quantity, **extra):
    return client.post(f'/api/stock/{op}/', json={'items': [{'pk': pk, 'quantity': str(quantity), **extra}]})


def pytest_collection_modifyitems(items):
    """Tests marked `corrupts_db` deliberately store an unrepresentable quantity (DEF-03) which breaks the stock LIST endpoint for every
    later test; they run LAST. Every runner script (scripts/test_api.sh, test_e2e.sh) resets the DB first, so the damage never leaks."""
    items.sort(key=lambda it: it.get_closest_marker('corrupts_db') is not None)
