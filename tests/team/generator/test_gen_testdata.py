"""Unit tests of the test-data generator itself (tools/gen_testdata.py)."""
import json, os, sys, textwrap
from decimal import Decimal
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import gen_testdata as g  # noqa: E402

SPEC = os.path.join(ROOT, 'openapi', 'stock.yaml')


def make_spec(tmp_path, quantity_extra='', notes_max=512, text=None):
    text = text or textwrap.dedent(f"""
    openapi: 3.0.3
    info: {{title: t, version: '1'}}
    paths:
      /x/:
        post:
          operationId: op
          requestBody:
            content:
              application/json:
                schema: {{$ref: '#/components/schemas/Body'}}
    components:
      schemas:
        Body:
          type: object
          required: [q]
          properties:
            q: {{type: number, minimum: 0, exclusiveMinimum: true, maximum: 100, multipleOf: 0.01{quantity_extra}}}
            n: {{type: string, maxLength: {notes_max}}}
    """)
    p = tmp_path / 'spec.yaml'; p.write_text(text); return str(p)


def cases(path):
    return {c['id']: c for c in g.generate(path)['cases']}


def test_decimals_are_parsed_exactly():
    root, _ = g.load_spec(SPEC)
    mx = root['components']['schemas']['StockAdjustmentItem']['properties']['quantity']['maximum']
    assert isinstance(mx, Decimal) and str(mx) == '9999999999.99999'


def test_three_point_bva_for_exclusive_minimum(tmp_path):
    c = cases(make_spec(tmp_path))
    assert (c['op:q:BVA:min-below']['value'], c['op:q:BVA:min-below']['expected']) == ('-0.01', 'invalid')
    assert (c['op:q:BVA:min-at']['value'], c['op:q:BVA:min-at']['expected']) == ('0', 'invalid')     # exclusive
    assert (c['op:q:BVA:min-above']['value'], c['op:q:BVA:min-above']['expected']) == ('0.01', 'valid')


def test_three_point_bva_for_maximum(tmp_path):
    c = cases(make_spec(tmp_path))
    assert [c[f'op:q:BVA:max-{k}']['value'] for k in ('below', 'at', 'above')] == ['99.99', '100', '100.01']
    assert [c[f'op:q:BVA:max-{k}']['expected'] for k in ('below', 'at', 'above')] == ['valid', 'valid', 'invalid']


def test_inclusive_minimum_is_valid_at_boundary(tmp_path):
    p = make_spec(tmp_path, text=None).replace('x', 'x')
    text = open(p).read().replace('exclusiveMinimum: true, ', '')
    open(p, 'w').write(text)
    assert cases(p)['op:q:BVA:min-at']['expected'] == 'valid'


def test_string_length_bva(tmp_path):
    c = cases(make_spec(tmp_path, notes_max=10))
    assert [len(c[f'op:n:BVA:maxlen-{k}']['value']) for k in ('below', 'at', 'above')] == [9, 10, 11]
    assert [c[f'op:n:BVA:maxlen-{k}']['expected'] for k in ('below', 'at', 'above')] == ['valid', 'valid', 'invalid']


def test_ep_classes_present_for_numeric_input(tmp_path):
    c = cases(make_spec(tmp_path))
    for k in ('valid-typical', 'not-a-number', 'null', 'empty-string', 'too-many-decimals', 'below-range', 'above-range', 'missing-required'):
        assert f'op:q:EP:{k}' in c, k
    assert c['op:q:EP:too-many-decimals']['value'] == '1.111'


def test_required_missing_class_removes_the_field(tmp_path):
    assert 'q' not in cases(make_spec(tmp_path))['op:q:EP:missing-required']['body']


def test_optional_field_has_no_missing_class(tmp_path):
    assert 'op:n:EP:missing-required' not in cases(make_spec(tmp_path))


def test_each_case_mutates_exactly_one_field_of_a_valid_template():
    data = g.generate(SPEC)
    for case in data['cases']:
        if case['field'].count('.') == 0 and '[]' not in case['field'] and case['class'] != 'missing-required':
            others = {k: v for k, v in case['body'].items() if k != case['field']}
            assert all(k in ('items', 'notes') for k in others)


def test_output_is_deterministic():
    a = json.dumps(g.generate(SPEC), sort_keys=True, default=str)
    b = json.dumps(g.generate(SPEC), sort_keys=True, default=str)
    assert a == b


def test_remove_operation_gets_available_quantity_bva():
    c = cases(SPEC)
    for k, exp in (('limit-below', 'valid'), ('limit-at', 'valid'), ('limit-above', 'invalid')):
        assert c[f'stockRemove:items[].quantity:BVA:{k}']['expected'] == exp
        assert f'stockAdd:items[].quantity:BVA:{k}' not in c       # add has no available-quantity limit


def test_reference_field_gets_unknown_and_negative_classes():
    c = cases(SPEC)
    assert c['stockAdd:items[].pk:EP:unknown-reference']['expected'] == 'invalid'
    assert c['stockAdd:items[].pk:BVA:below-minimum']['value'] == 0


def test_operations_without_request_body_are_skipped():
    assert not [c for c in g.generate(SPEC)['cases'] if c['operation'] in ('stockItemRead', 'auditList')]


def test_changing_a_constraint_changes_the_output(tmp_path):
    base = cases(make_spec(tmp_path, notes_max=512))
    new = cases(make_spec(tmp_path, notes_max=100))
    assert len(base['op:n:BVA:maxlen-at']['value']) == 512 and len(new['op:n:BVA:maxlen-at']['value']) == 100


def test_cli_writes_json(tmp_path):
    out = tmp_path / 'o.json'
    assert g.main([SPEC, '-o', str(out)]) == 0
    assert json.loads(out.read_text())['count'] > 50
