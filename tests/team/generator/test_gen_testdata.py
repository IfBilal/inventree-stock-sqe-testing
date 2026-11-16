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
            q: {{type: number, format: decimal, minimum: 0, exclusiveMinimum: true, maximum: 100, multipleOf: 0.01{quantity_extra}}}
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
    for case in [c for c in data['cases'] if c['location'] == 'body']:
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
    assert c['stockAdd:items[].pk:BVA:min-below']['value'] == 0


def test_operations_without_request_body_are_skipped():
    assert not [c for c in g.generate(SPEC)['cases'] if c['operation'] in ('stockItemRead', 'auditList') and c['location'] == 'body']


def test_changing_a_constraint_changes_the_output(tmp_path):
    base = cases(make_spec(tmp_path, notes_max=512))
    new = cases(make_spec(tmp_path, notes_max=100))
    assert len(base['op:n:BVA:maxlen-at']['value']) == 512 and len(new['op:n:BVA:maxlen-at']['value']) == 100


def test_cli_writes_json(tmp_path):
    out = tmp_path / 'o.json'
    assert g.main([SPEC, '-o', str(out)]) == 0
    assert json.loads(out.read_text())['count'] > 50


# ------------------------------------------------------------------ spec validity and keyword coverage (review round 1)
def test_the_project_spec_is_valid_openapi():
    import yaml
    from openapi_spec_validator import validate_spec
    validate_spec(yaml.safe_load(open(SPEC)))


def _probe(tmp_path, props, required='[q]'):
    text = textwrap.dedent("""
    openapi: 3.0.3
    info: {title: t, version: '1'}
    paths:
      /x/:
        post:
          operationId: op
          requestBody:
            content:
              application/json:
                schema: {$ref: '#/components/schemas/B'}
    components:
      schemas:
        B:
          type: object
          required: REQ
          properties:
    """).replace('REQ', required) + textwrap.indent(textwrap.dedent(props), '        ')
    p = tmp_path / 's.yaml'; p.write_text(text)
    return cases(str(p))


def test_exclusive_maximum_boolean_changes_max_at(tmp_path):
    c = _probe(tmp_path, "q: {type: number, format: decimal, maximum: 10, exclusiveMaximum: true, multipleOf: 1}")
    assert c['op:q:BVA:max-at']['value'] == '9' and c['op:q:BVA:max-above']['value'] == '10' and c['op:q:BVA:max-above']['expected'] == 'invalid'


def test_numeric_exclusive_bounds_openapi_31_style(tmp_path):
    c = _probe(tmp_path, "q: {type: number, format: decimal, exclusiveMinimum: 5, multipleOf: 1}")
    assert (c['op:q:BVA:min-at']['value'], c['op:q:BVA:min-at']['expected']) == ('5', 'invalid')


def test_enum_members_and_non_member(tmp_path):
    c = _probe(tmp_path, "q: {type: integer, enum: [1, 2, 3]}")
    assert c['op:q:EP:enum-member-2']['expected'] == 'valid' and c['op:q:EP:enum-non-member']['value'] == 4 and c['op:q:EP:enum-non-member']['expected'] == 'invalid'


def test_nullable_makes_null_valid(tmp_path):
    c = _probe(tmp_path, "q: {type: integer, nullable: true}")
    assert c['op:q:EP:null']['expected'] == 'valid'


def test_min_length_bva(tmp_path):
    c = _probe(tmp_path, "q: {type: string, minLength: 3, maxLength: 5}")
    assert [len(c[f'op:q:BVA:minlen-{k}']['value']) for k in ('below', 'at', 'above')] == [2, 3, 4]
    assert c['op:q:EP:empty-string']['expected'] == 'invalid'


def test_pattern_violation_case(tmp_path):
    c = _probe(tmp_path, "q: {type: string, pattern: '^[0-9]+$'}")
    assert c['op:q:EP:pattern-violation']['expected'] == 'invalid'


def test_optional_array_with_minitems_does_not_crash(tmp_path):
    c = _probe(tmp_path, "l: {type: array, minItems: 2, items: {type: integer}}\nq: {type: integer}")
    assert c['op:l:BVA:minitems-below']['expected'] == 'invalid' and c['op:l:BVA:minitems-at']['expected'] == 'valid'


def test_nested_object_inputs_are_walked(tmp_path):
    c = _probe(tmp_path, "o: {type: object, required: [n], properties: {n: {type: integer, minimum: 1}}}\nq: {type: integer}")
    assert 'op:o.n:BVA:min-below' in c and 'op:o.n:EP:missing-required' in c


def test_boundary_values_are_snapped_to_the_multipleof_grid(tmp_path):
    c = _probe(tmp_path, "q: {type: number, format: decimal, maximum: 10.005, multipleOf: 0.01}")
    assert c['op:q:BVA:max-at']['value'] == '10.00' and c['op:q:BVA:max-above']['value'] == '10.01'     # on-grid, violates only `maximum`


def test_integer_bva_values_stay_integers(tmp_path):
    c = _probe(tmp_path, "q: {type: integer, minimum: 4, maximum: 6}")
    assert [c[f'op:q:BVA:{k}']['value'] for k in ('min-below', 'min-at', 'min-above', 'max-below', 'max-at', 'max-above')] == [3, 4, 5, 5, 6, 7]


def test_reference_field_has_three_point_bva(tmp_path):
    c = cases(SPEC)
    assert [c[f'stockAdd:items[].pk:BVA:{k}']['expected'] for k in ('min-below', 'min-at', 'min-above')] == ['invalid', 'valid', 'valid']


def test_path_and_query_parameters_get_cases():
    c = cases(SPEC)
    assert c['stockItemRead:id:BVA:min-below']['expected_status'] == 404 and c['stockItemRead:id:BVA:min-at']['expected_status'] == 200
    assert any(k.startswith('auditList:limit:BVA') for k in c)


def test_type_confusion_classes_present():
    c = cases(SPEC)
    for k in ('stockAdd:items[].quantity:EP:type-bool-true', 'stockAdd:items[].quantity:EP:type-empty-list', 'stockAdd:items[].merge:EP:type-integer-1',
              'stockAdd:notes:EP:type-empty-object', 'stockAdd:notes:EP:multibyte-at-maxlen'):
        assert k in c, k
