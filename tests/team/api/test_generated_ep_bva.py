"""API tests driven ENTIRELY by the generator output (tools/gen_testdata.py reading openapi/stock.yaml):
equivalence classes and 3-point BVA for every input of both endpoints (R-24, R-29). No boundary value is hard-coded here."""
import os, sys
from decimal import Decimal
import pytest
from conftest import ROOT, qty, history

sys.path.insert(0, os.path.join(ROOT, 'tools'))
import gen_testdata  # noqa: E402

SPEC = os.path.join(ROOT, 'openapi', 'stock.yaml')
CASES = gen_testdata.generate(SPEC)['cases']
MAXQ = '9999999999.99999'

# Baseline defects: generated cases whose EXPECTED (contract) outcome the unmodified upstream fails. strict xfail -> must be
# removed together with the fix (DEF-01 over-removal, DEF-02 zero accepted).
KNOWN = {
    'stockAdd:items[].quantity:BVA:min-at': 'DEF-02', 'stockRemove:items[].quantity:BVA:min-at': 'DEF-02',
    'stockRemove:items[].quantity:BVA:limit-above': 'DEF-01',
    'stockAdd:items:EP:not-an-array': 'DEF-04', 'stockAdd:items:EP:null': 'DEF-04',
    'stockRemove:items:EP:not-an-array': 'DEF-04', 'stockRemove:items:EP:null': 'DEF-04',
}


def initial_quantity(case):
    cls, op = case['class'], case['operation']
    if cls.startswith('limit-'):
        return '10'
    if case['field'].endswith('quantity') and op == 'stockRemove':
        return MAXQ                       # enough stock for every schema-valid removal
    if case['field'].endswith('quantity') and op == 'stockAdd' and isinstance(case['value'], str) and case['value'].replace('.', '').lstrip('-').isdigit() and abs(Decimal(case['value'])) >= Decimal('1e9'):
        return '0'                        # keep the RESULT representable (DEF-03 is tested separately)
    return '10'


def resolve(node, pk, available):
    if node == '$ITEM':
        return pk
    if isinstance(node, dict):
        if '$available' in node:
            return str(Decimal(available) + Decimal(node['$available']))
        return {k: resolve(v, pk, available) for k, v in node.items()}
    if isinstance(node, list):
        return [resolve(v, pk, available) for v in node]
    return node


def delta_of(body):
    return sum(Decimal(str(i['quantity'])) for i in body['items'])


def _reqs(c):
    ids = {'FR-01' if c['operation'] == 'stockAdd' else 'FR-05'} if c['expected'] == 'valid' else {'FR-03a'}
    if c['field'].endswith('quantity') and c['technique'] == 'BVA': ids.add('BR-1')
    if c['class'].startswith('limit-'): ids.add('FR-07')
    if c['class'] == 'min-at': ids.add('FR-03b')
    if c['field'].endswith('.pk'): ids.add('FR-04')
    return ids


def _params():
    for c in CASES:
        marks = [pytest.mark.req(*sorted(_reqs(c)))]
        if c['id'] in KNOWN:
            marks.append(pytest.mark.xfail(strict=True, raises=AssertionError, reason=KNOWN[c['id']]))
        yield pytest.param(c, id=c['id'], marks=marks)


@pytest.mark.risk('PR-01', 'PR-04')
@pytest.mark.parametrize('case', list(_params()))
def test_generated_case(case, manager, new_item):
    pk = new_item(initial_quantity(case))
    before_q, before_h = qty(manager, pk), len(history(manager, pk))
    body = resolve(case['body'], pk, before_q)
    r = manager.post(case['path'], json=body)
    after_q, after_h = qty(manager, pk), len(history(manager, pk))
    if case['expected'] == 'valid':
        assert r.status_code == 201, (r.status_code, r.text[:200])
        d = delta_of(body)
        assert after_q == (before_q + d if case['operation'] == 'stockAdd' else before_q - d)      # read-back after success
        assert after_h == before_h + len(body['items'])
    else:
        assert r.status_code == 400, (r.status_code, r.text[:200])
        assert after_q == before_q and after_h == before_h                                        # read-back after rejection
