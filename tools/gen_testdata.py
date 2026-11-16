#!/usr/bin/env python3
"""Automated test-data generator: reads an OpenAPI 3.0 spec and emits Equivalence-Partitioning classes (EP) and 3-point
Boundary-Value-Analysis values (BVA: just below, exactly at, just above every limit) for EVERY input of every operation:
JSON request-body fields (incl. nested objects and array items) and path / query parameters.

Usage:  python tools/gen_testdata.py openapi/stock.yaml -o evidence/generator/testdata.json

Output: JSON {"spec_sha256", "count", "cases": [ {id, operation, method, path, location (body|path|query), field,
        technique (EP|BVA), class, value, expected (valid|invalid), expected_status, constraint, required, body} ]}
`body` is a complete request body (a valid template with exactly ONE mutation) for body inputs, `null` for parameters.
Placeholders: "$ITEM" = pk of an existing item; {"$pk": n} = the pk n (seeded item); {"$available": "<offset>"} = a quantity
relative to the item's current quantity (operations with x-quantity-limit-from).

Keywords handled: type (string/number/integer/boolean/array/object), required, nullable, enum, minimum, maximum,
exclusiveMinimum / exclusiveMaximum (OpenAPI 3.0 boolean and 3.1 numeric), multipleOf, minLength, maxLength, pattern,
minItems, maxItems, nested object properties, x-reference, x-quantity-limit-from, x-wire-format. Numbers whose wire format is a
string are emitted as decimal strings. Boundary values are snapped to the multipleOf grid so every case violates AT MOST ONE
constraint. Decimals are parsed exactly. Deterministic: same spec -> byte-identical output.
"""
import argparse, copy, hashlib, json, re, sys
from decimal import Decimal, ROUND_FLOOR

import yaml


class _Loader(yaml.SafeLoader):
    pass


_Loader.add_constructor('tag:yaml.org,2002:float', lambda l, n: Decimal(l.construct_scalar(n)))   # exact decimals


def load_spec(path):
    raw = open(path, 'rb').read()
    return yaml.load(raw, Loader=_Loader), hashlib.sha256(raw).hexdigest()


def resolve(schema, root):
    while isinstance(schema, dict) and '$ref' in schema:
        node = root
        for part in schema['$ref'].lstrip('#/').split('/'):
            node = node[part]
        schema = node
    return schema


def D(v):
    return v if isinstance(v, Decimal) else Decimal(str(v))


def fmt(v, sch):
    """Wire representation of a numeric value."""
    if sch.get('type') == 'integer':
        return int(v)
    if sch.get('x-wire-format') == 'string' or sch.get('format') == 'decimal':
        return format(D(v), 'f')
    return float(v)


def snap_down(v, step):
    return (D(v) / step).to_integral_value(rounding=ROUND_FLOOR) * step if step else D(v)


def bounds(sch):
    """Return (lo, lo_exclusive, hi, hi_exclusive) as Decimals/bools from either OpenAPI 3.0 (boolean) or 3.1 (numeric) styles."""
    lo, hi = sch.get('minimum'), sch.get('maximum')
    lo_ex = hi_ex = False
    for key, which in (('exclusiveMinimum', 'lo'), ('exclusiveMaximum', 'hi')):
        v = sch.get(key)
        if v is True:
            if which == 'lo': lo_ex = True
            else: hi_ex = True
        elif v not in (None, False):          # numeric exclusive bound (3.1)
            if which == 'lo': lo, lo_ex = v, True
            else: hi, hi_ex = v, True
    return (None if lo is None else D(lo), lo_ex, None if hi is None else D(hi), hi_ex)


def valid_sample(sch):
    t = sch.get('type')
    if sch.get('x-reference'):
        return '$ITEM'
    if sch.get('enum'):
        return next(e for e in sch['enum'] if e is not None)
    if t in ('number', 'integer'):
        lo, lo_ex, hi, hi_ex = bounds(sch)
        step = D(sch['multipleOf']) if sch.get('multipleOf') else (Decimal(1) if t == 'integer' else None)
        cand = Decimal(1)
        if lo is not None and (cand < lo or (lo_ex and cand == lo)):
            cand = lo + (step or Decimal(1))
        if hi is not None and (cand > hi or (hi_ex and cand == hi)):
            cand = hi - (step or Decimal(1)) if hi_ex else hi
        return fmt(cand, sch)
    if t == 'string':
        mx, mn = sch.get('maxLength'), sch.get('minLength', 0)
        n = max(mn, 1) if mx is None else max(mn, min(6, mx))
        if mx == 0:
            return ''
        return ('sample' * 20)[:n]
    if t == 'boolean':
        return True
    return 'x'


def build_valid(schema, root):
    schema = resolve(schema, root)
    t = schema.get('type')
    if t == 'object':
        return {n: build_valid(schema['properties'][n], root) for n in schema.get('required', [])}
    if t == 'array':
        return [build_valid(schema['items'], root) for _ in range(max(1, schema.get('minItems', 0)))]
    return valid_sample(schema)


def walk(schema, root, prefix=''):
    """Yield (json_path, leaf_or_container_schema, required) for every input incl. nested object / array-item fields."""
    schema = resolve(schema, root)
    if schema.get('type') != 'object':
        return
    req = set(schema.get('required', []))
    for name in sorted(schema.get('properties', {})):
        sub = resolve(schema['properties'][name], root)
        path = f'{prefix}{name}'
        yield path, sub, name in req
        if sub.get('type') == 'array' and resolve(sub['items'], root).get('type') == 'object':
            yield from walk(sub['items'], root, f'{path}[].')
        elif sub.get('type') == 'object':
            yield from walk(sub, root, f'{path}.')


def set_path(body, path, value, root_template_fn, missing=False):
    body = copy.deepcopy(body)
    parts = path.split('.')
    node = body
    for i, part in enumerate(parts):
        arr = part.endswith('[]')
        key = part[:-2] if arr else part
        last = i == len(parts) - 1
        if last:
            tgt = node[0] if isinstance(node, list) else node
            if arr:                        # replace the whole array
                tgt[key] = value
            elif missing:
                tgt.pop(key, None)
            else:
                tgt[key] = value
        else:
            tgt = node[0] if isinstance(node, list) else node
            node = tgt.setdefault(key, [] if arr else {}) if key not in tgt else tgt[key]
    return body


TYPE_CONFUSION = {   # one clearly invalid value of a WRONG JSON type per case (unambiguous for DRF-style validators)
    'number': [('bool-true', True), ('empty-list', []), ('empty-object', {}), ('nan', 'NaN'), ('infinity', 'Infinity')],
    'integer': [('bool-true', True), ('empty-list', []), ('empty-object', {}), ('text', 'abc')],
    'string': [('bool-true', True), ('empty-object', {}), ('list', ['x'])],
    'boolean': [('text', 'maybe'), ('integer-2', 2), ('empty-list', [])],
}


def classes_for(path, sch, required, op, root):
    """Return list of (technique, class, value, expected, constraint)."""
    MISSING = '__missing__'
    t = sch.get('type')
    out = []
    ref = sch.get('x-reference')
    nullable = bool(sch.get('nullable'))
    if required:
        out.append(('EP', 'missing-required', MISSING, 'invalid', 'required'))
    out.append(('EP', 'null', None, 'valid' if nullable else 'invalid', 'nullable=true' if nullable else 'nullable=false'))
    if sch.get('enum'):
        members = [e for e in sch['enum'] if e is not None]
        for m in members:
            out.append(('EP', f'enum-member-{m}', m, 'valid', 'enum'))
        bad = max(m for m in members) + 1 if all(isinstance(m, int) for m in members) else 'NOT-A-MEMBER'
        out.append(('EP', 'enum-non-member', bad, 'invalid', 'enum'))
        return out
    if t in ('number', 'integer'):
        lo, lo_ex, hi, hi_ex = bounds(sch)
        step = D(sch['multipleOf']) if sch.get('multipleOf') else (Decimal(1) if t == 'integer' else None)
        unit = step or Decimal(1)
        out.append(('EP', 'valid-typical', valid_sample(sch), 'valid', 'type'))
        out.append(('EP', 'not-a-number', 'abc', 'invalid', 'type'))
        out.append(('EP', 'empty-string', '', 'invalid', 'type'))
        for name, v in TYPE_CONFUSION[t]:
            out.append(('EP', f'type-{name}', v, 'invalid', f'type={t}'))
        if t == 'number' and sch.get('multipleOf'):
            places = max(0, -D(sch['multipleOf']).as_tuple().exponent)
            out.append(('EP', 'too-many-decimals', '1.' + '1' * (places + 1), 'invalid', f'multipleOf {sch["multipleOf"]}'))
        if t == 'integer':
            out.append(('EP', 'fractional', '1.5', 'invalid', 'type=integer'))
        if ref:
            out.append(('EP', 'unknown-reference', 999999999, 'invalid', f'x-reference {ref}'))
            out.append(('EP', 'negative', -1, 'invalid', f'minimum {lo}'))
            if lo is not None:   # 3-point BVA on the reference: below (invalid), at and above (existing seeded items)
                lo_i = int(lo)
                out.append(('BVA', 'min-below', lo_i - 1, 'invalid', f'minimum {lo}'))
                out.append(('BVA', 'min-at', {'$pk': lo_i}, 'valid', f'minimum {lo}'))
                out.append(('BVA', 'min-above', {'$pk': lo_i + 1}, 'valid', f'minimum {lo}'))
        else:
            if lo is not None:
                at = lo if not lo_ex else lo           # the boundary itself
                out.append(('EP', 'below-range', fmt(lo - 1 if t == 'integer' else lo - Decimal(1), sch), 'invalid', f'minimum {lo}'))
                out.append(('BVA', 'min-below', fmt(lo - unit, sch), 'invalid', f'minimum {lo}'))
                out.append(('BVA', 'min-at', fmt(at, sch), 'invalid' if lo_ex else 'valid', f"minimum {lo}{' (exclusive)' if lo_ex else ''}"))
                out.append(('BVA', 'min-above', fmt(lo + unit, sch), 'valid', f'minimum {lo}'))
            if hi is not None:
                top = snap_down(hi, step) if step else hi          # largest on-grid value <= hi
                if hi_ex and top == hi:
                    top = hi - unit
                out.append(('EP', 'above-range', fmt(hi + Decimal(1), sch), 'invalid', f'maximum {hi}'))
                out.append(('BVA', 'max-below', fmt(top - unit, sch), 'valid', f'maximum {hi}'))
                out.append(('BVA', 'max-at', fmt(top, sch), 'valid', f"maximum {hi}{' (exclusive)' if hi_ex else ''}"))
                out.append(('BVA', 'max-above', fmt(top + unit, sch), 'invalid', f'maximum {hi}'))
        if op.get('x-quantity-limit-from') and path.endswith('quantity'):
            lim, u = op['x-quantity-limit-from'], format(unit, 'f')
            out.append(('BVA', 'limit-below', {'$available': '-' + u}, 'valid', f'quantity <= {lim}'))
            out.append(('BVA', 'limit-at', {'$available': '0'}, 'valid', f'quantity <= {lim}'))
            out.append(('BVA', 'limit-above', {'$available': '+' + u}, 'invalid', f'quantity <= {lim}'))
    elif t == 'string':
        mx, mn = sch.get('maxLength'), sch.get('minLength', 0)
        out.append(('EP', 'valid-typical', valid_sample(sch), 'valid', 'type'))
        for name, v in TYPE_CONFUSION['string']:
            out.append(('EP', f'type-{name}', v, 'invalid', 'type=string'))
        if mn == 0:
            out.append(('EP', 'empty-string', '', 'valid', 'minLength 0'))
        if mn > 0:
            out.append(('EP', 'empty-string', '', 'invalid', f'minLength {mn}'))
            out.append(('BVA', 'minlen-below', 'a' * (mn - 1), 'invalid', f'minLength {mn}'))
            out.append(('BVA', 'minlen-at', 'a' * mn, 'valid', f'minLength {mn}'))
            out.append(('BVA', 'minlen-above', 'a' * (mn + 1), 'valid', f'minLength {mn}'))
        if mx is not None:
            out.append(('BVA', 'maxlen-below', 'a' * (mx - 1), 'valid', f'maxLength {mx}'))
            out.append(('BVA', 'maxlen-at', 'a' * mx, 'valid', f'maxLength {mx}'))
            out.append(('BVA', 'maxlen-above', 'a' * (mx + 1), 'invalid', f'maxLength {mx}'))
            out.append(('EP', 'multibyte-at-maxlen', 'é' * mx, 'valid', f'maxLength {mx} counts characters, not bytes'))
        if sch.get('pattern'):
            pat = re.compile(sch['pattern'])
            bad = next((c for c in ('\x00', '!!!', ' ', '???', 'ZZZ-0') if not pat.search(c)), None)
            if bad is not None:
                out.append(('EP', 'pattern-violation', bad, 'invalid', f"pattern {sch['pattern']}"))
    elif t == 'boolean':
        out.append(('EP', 'true', True, 'valid', 'type'))
        out.append(('EP', 'false', False, 'valid', 'type'))
        for name, v in TYPE_CONFUSION['boolean']:
            out.append(('EP', f'type-{name}', v, 'invalid', 'type=boolean'))
        out.append(('EP', 'type-integer-1', 1, 'invalid', 'type=boolean (strict JSON type)'))
        out.append(('EP', 'type-integer-0', 0, 'invalid', 'type=boolean (strict JSON type)'))
    elif t == 'array':
        mn, mx = sch.get('minItems'), sch.get('maxItems')
        out.append(('EP', 'not-an-array', 'abc', 'invalid', 'type=array'))
        out.append(('EP', 'object-instead-of-array', {'a': 1}, 'invalid', 'type=array'))
        if mn is not None:
            out.append(('BVA', 'minitems-below', ('ARRAY', mn - 1), 'invalid', f'minItems {mn}'))
            out.append(('BVA', 'minitems-at', ('ARRAY', mn), 'valid', f'minItems {mn}'))
            out.append(('BVA', 'minitems-above', ('ARRAY', mn + 1), 'valid', f'minItems {mn}'))
        if mx is not None:
            out.append(('BVA', 'maxitems-below', ('ARRAY', mx - 1), 'valid', f'maxItems {mx}'))
            out.append(('BVA', 'maxitems-at', ('ARRAY', mx), 'valid', f'maxItems {mx}'))
            out.append(('BVA', 'maxitems-above', ('ARRAY', mx + 1), 'invalid', f'maxItems {mx}'))
    return out


def _case(opid, method, url, location, field, technique, klass, value, expected, constraint, required, body, status=None):
    return {'id': f'{opid}:{field}:{technique}:{klass}', 'operation': opid, 'method': method.upper(), 'path': url,
            'location': location, 'field': field, 'technique': technique, 'class': klass,
            'value': value, 'expected': expected, 'expected_status': status, 'constraint': constraint,
            'required': required, 'body': body}


def generate(spec_path):
    root, digest = load_spec(spec_path)
    cases = []
    for url in sorted(root['paths']):
        for method in sorted(root['paths'][url]):
            op = root['paths'][url][method]
            opid = op.get('operationId', f'{method}{url}')
            body_schema = (op.get('requestBody', {}).get('content', {}).get('application/json', {}) or {}).get('schema')
            if body_schema:
                body_schema = resolve(body_schema, root)
                template = build_valid(body_schema, root)
                for path, sch, required in walk(body_schema, root):
                    for technique, klass, value, expected, constraint in classes_for(path, sch, required, op, root):
                        if value == '__missing__':
                            body = set_path(template, path, None, None, missing=True)
                        elif isinstance(value, tuple) and value[0] == 'ARRAY':
                            item_t = build_valid(resolve(sch['items'], root), root)
                            body = set_path(template, path, [copy.deepcopy(item_t) for _ in range(value[1])], None)
                            value = f'{value[1]} item(s)'
                        else:
                            body = set_path(template, path, value, None)
                        cases.append(_case(opid, method, url, 'body', path, technique, klass, value, expected, constraint, required, body))
            for prm in op.get('parameters', []):
                sch = resolve(prm['schema'], root)
                loc, name, req = prm['in'], prm['name'], bool(prm.get('required'))
                if loc not in ('path', 'query') or sch.get('type') == 'string':
                    continue
                for technique, klass, value, expected, constraint in classes_for(name, sch, req, op, root):
                    if value == '__missing__' or (loc == 'path' and klass in ('null', 'empty-string')):
                        continue
                    status = (200 if expected == 'valid' else (404 if loc == 'path' else 400))
                    cases.append(_case(opid, method, url, loc, name, technique, klass, value, expected, constraint, req, None, status))
    return {'spec': spec_path, 'spec_sha256': digest, 'count': len(cases), 'cases': cases}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('spec'); ap.add_argument('-o', '--out')
    a = ap.parse_args(argv)
    text = json.dumps(generate(a.spec), indent=1, sort_keys=True, default=str) + '\n'
    if a.out:
        open(a.out, 'w').write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
