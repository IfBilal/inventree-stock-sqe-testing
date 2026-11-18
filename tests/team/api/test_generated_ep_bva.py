"""API tests driven ENTIRELY by the generator output (tools/gen_testdata.py reading openapi/stock.yaml):
equivalence classes and 3-point BVA for every input of every operation: body fields, path and query parameters (R-24, R-29).
No boundary value is hard-coded here: the representable maximum used to prepare state is read from the spec."""
import json, os, sys
from decimal import Decimal
import pytest
from conftest import ROOT, qty, history

sys.path.insert(0, os.path.join(ROOT, 'tools'))
import gen_testdata  # noqa: E402

SPEC = os.environ.get('API_SPEC', os.path.join(ROOT, 'openapi', 'stock.yaml'))
GEN = gen_testdata.generate(SPEC)
CASES = GEN['cases']
_ROOT_SPEC, _ = gen_testdata.load_spec(SPEC)
_QSCHEMA = _ROOT_SPEC['components']['schemas']['StockAdjustmentItem']['properties']['quantity']
MAXQ = format(Decimal(str(_QSCHEMA['maximum'])), 'f')            # largest representable quantity, from the spec
BIG = Decimal(MAXQ) / 10                                          # "near the maximum" threshold, derived
EXEC_LOG = os.path.join(ROOT, 'evidence', 'api', 'cases_executed.jsonl')
_EXEC = []

# Remaining mismatches (DEF-01..04 are fixed): generated cases whose EXPECTED (contract) outcome the upstream still does not meet (loose typing, unvalidated audit parameters).
# strict xfail + raises=AssertionError: when a defect is fixed the xfail turns XPASS and fails, forcing the marker's removal.
DEFECT = {'W-12': 'boolean true accepted as pk 1 (loose typing)', 'W-08': 'boolean accepts integers 0/1 (loose typing)', 'W-09': 'audit query parameters are not validated'}
KNOWN = {}
for op in ('stockAdd', 'stockRemove'):
    KNOWN[f'{op}:items[].merge:EP:type-integer-1'] = 'W-08'
    KNOWN[f'{op}:items[].merge:EP:type-integer-0'] = 'W-08'
    KNOWN[f'{op}:items[].pk:EP:type-bool-true'] = 'W-12'
for _c in CASES:   # every INVALID query-parameter case of the audit endpoint: not validated (W-09)
    if _c['location'] == 'query' and _c['expected'] == 'invalid' and _c['id'] != 'auditList:event_type:EP:null':   # type errors of event_type ARE validated (400)
        KNOWN[_c['id']] = 'W-09'


def _is_number(v):
    try:
        return (not isinstance(v, bool)) and Decimal(str(v)).is_finite()
    except Exception:
        return False


def initial_quantity(case):
    cls, op, f = case['class'], case['operation'], case['field']
    if cls.startswith('limit-'):
        return '10'
    if f.endswith('quantity') and op == 'stockRemove':
        return MAXQ                       # enough stock for every schema-valid removal
    if f.endswith('quantity') and op == 'stockAdd' and _is_number(case['value']) and abs(Decimal(str(case['value']))) >= BIG:
        return '0'                        # keep the RESULT representable (DEF-03 is tested separately)
    return '10'


def resolve(node, pk, available):
    if node == '$ITEM':
        return pk
    if isinstance(node, dict):
        if '$available' in node:
            return str(Decimal(str(available)) + Decimal(node['$available']))
        if '$pk' in node:
            return node['$pk']
        return {k: resolve(v, pk, available) for k, v in node.items()}
    if isinstance(node, list):
        return [resolve(v, pk, available) for v in node]
    return node


def delta_of(body):
    return sum(Decimal(str(i['quantity'])) for i in body['items'])


def _reqs(c):
    ids = set()
    if c['location'] == 'body':
        ids = {'FR-01' if c['operation'] == 'stockAdd' else 'FR-05'} if c['expected'] == 'valid' else {'FR-03a'}
        if c['field'].endswith('quantity') and c['technique'] == 'BVA': ids.add('BR-1')
        if c['class'].startswith('limit-') and c['expected'] == 'invalid': ids.add('FR-07')       # only the REJECTION verifies FR-07
        if c['class'] == 'min-at' and c['field'].endswith('quantity'): ids.add('FR-03b')
        if c['field'].endswith('.pk'): ids.add('FR-04')
    return ids or {'FR-02'}


def _params():
    for c in CASES:
        marks = [pytest.mark.req(*sorted(_reqs(c)))]
        if c['id'] in KNOWN:
            marks.append(pytest.mark.xfail(strict=True, raises=AssertionError, reason=f"{KNOWN[c['id']]}: {DEFECT[KNOWN[c['id']]]}"))
        yield pytest.param(c, id=c['id'], marks=marks)


@pytest.fixture(scope='module', autouse=True)
def _dump_executed():
    yield
    os.makedirs(os.path.dirname(EXEC_LOG), exist_ok=True)
    with open(EXEC_LOG, 'a' if os.environ.get('API_LOG_APPEND') == '1' else 'w') as f:
        for r in _EXEC:
            f.write(json.dumps(r, sort_keys=True) + '\n')


def _record(case, outcome):
    _EXEC.append({'id': case['id'], 'operation': case['operation'], 'field': case['field'], 'location': case['location'],
                  'technique': case['technique'], 'class': case['class'], 'expected': case['expected'], 'outcome': outcome})


@pytest.mark.risk('PR-01', 'PR-04')
@pytest.mark.parametrize('case', list(_params()))
def test_generated_case(case, manager, new_item):
    if case['location'] != 'body':
        return _run_param_case(case, manager, new_item)
    pk = new_item(initial_quantity(case))
    before_q, before_h = qty(manager, pk), history(manager, pk)
    body = resolve(case['body'], pk, before_q)
    target = body['items'][0]['pk'] if isinstance(body.get('items'), list) and body['items'] and isinstance(body['items'][0], dict) and isinstance(body['items'][0].get('pk'), int) else pk
    seeded = target != pk                                              # {"$pk": n} cases act on a seeded item
    if seeded:
        before_q, before_h = qty(manager, target), history(manager, target)
    try:
        r = manager.post(case['path'], json=body)
        after_q, after_h = qty(manager, target), history(manager, target)
        if case['expected'] == 'valid':
            assert r.status_code == 201, (r.status_code, r.text[:200])
            d = delta_of(body)
            assert after_q == (before_q + d if case['operation'] == 'stockAdd' else before_q - d)      # read-back of the shared record
            assert len(after_h) == len(before_h) + len(body['items'])
            _read_back_optional_fields(manager, target, body, after_h)
        else:
            assert r.status_code == 400, (r.status_code, r.text[:200])
            assert after_q == before_q and len(after_h) == len(before_h)                              # nothing changed after rejection
    except AssertionError:
        _record(case, 'mismatch'); raise
    _record(case, 'match')


def _read_back_optional_fields(client, pk, body, history_after):
    item = client.get(f'/api/stock/{pk}/').json()
    first = body['items'][0]
    for f in ('batch', 'packaging'):
        if first.get(f):
            assert item[f] == first[f], f'{f} did not take effect'
    if first.get('status') is not None:
        assert item['status'] == first['status']
    if body.get('notes'):
        assert sorted(history_after, key=lambda e: e['pk'])[-1]['notes'] == body['notes']


def _run_param_case(case, manager, new_item):
    v = case['value']
    v = v['$pk'] if isinstance(v, dict) and '$pk' in v else (new_item(10) if v == '$ITEM' else v)
    try:
        if case['location'] == 'path':
            r = manager.get(case['path'].replace('{id}', str(v)))
        else:
            r = manager.get(f"{case['path']}?model_type=stock.stockitem&{case['field']}={v}&limit=5" if case['field'] != 'limit'
                            else f"{case['path']}?model_type=stock.stockitem&limit={v}")
        assert r.status_code == case['expected_status'], (r.status_code, r.text[:160])
    except AssertionError:
        _record(case, 'mismatch'); raise
    _record(case, 'match')
