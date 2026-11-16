#!/usr/bin/env python3
"""Automated test-data generator: reads an OpenAPI spec and emits Equivalence-Partitioning classes and 3-point
Boundary-Value-Analysis values for EVERY input of every operation that has a JSON request body.

Usage:  python tools/gen_testdata.py openapi/stock.yaml -o evidence/generator/testdata.json

Output: JSON {"spec_sha256", "cases": [ {id, operation, path, field, technique (EP|BVA), class, value, expected
        (valid|invalid), constraint, body} ]}. `body` is a complete request body (valid template with exactly one
        mutation), ready to send. Placeholders: "$ITEM" = pk of an existing item; {"$available": "<offset>"} = a
        quantity relative to the item's current quantity (operations with x-quantity-limit-from).
Decimals are parsed exactly (no float rounding) and emitted as strings.
Constraints handled: type, required, minimum / exclusiveMinimum, maximum, multipleOf (decimal places), minLength,
maxLength, minItems, maxItems, x-reference, x-quantity-limit-from. Deterministic: same spec -> byte-identical output.
"""
import argparse, copy, hashlib, json, sys
from decimal import Decimal

import yaml


class _Loader(yaml.SafeLoader):
    pass


# exact decimals: never let YAML turn 9999999999.99999 into a binary float
_Loader.add_constructor('tag:yaml.org,2002:float', lambda l, n: Decimal(l.construct_scalar(n)))


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


def s(v):
    """Decimal -> plain string (no exponent)."""
    return format(v, 'f') if isinstance(v, Decimal) else v


def places(step):
    return max(0, -step.as_tuple().exponent) if step is not None else 0


def valid_sample(schema, field_ref=None):
    t = schema.get('type')
    if schema.get('x-reference'):
        return '$ITEM'
    if t in ('number', 'integer'):
        lo, hi = schema.get('minimum'), schema.get('maximum')
        step = schema.get('multipleOf')
        if t == 'integer':
            return int(lo) if lo is not None else 1
        cand = Decimal(1)
        if lo is not None and (cand < lo or (schema.get('exclusiveMinimum') and cand == lo)):
            cand = lo + (step or Decimal(1))
        if hi is not None and cand > hi:
            cand = hi
        return s(cand)
    if t == 'string':
        n = schema.get('maxLength')
        return 'sample' if n is None or n >= 6 else 'x' * max(1, n)
    if t == 'boolean':
        return True
    if t == 'array':
        return None   # filled by caller from item schema
    return 'x'


def build_valid(schema, root):
    schema = resolve(schema, root)
    t = schema.get('type')
    if t == 'object':
        out = {}
        for name in schema.get('required', []):
            out[name] = build_valid(schema['properties'][name], root)
        return out
    if t == 'array':
        n = max(1, schema.get('minItems', 0))
        return [build_valid(schema['items'], root) for _ in range(n)]
    return valid_sample(schema)


def leaf_fields(schema, root, prefix=''):
    """Yield (json_path, leaf_schema, required, container_path_info) for every input incl. array item fields."""
    schema = resolve(schema, root)
    t = schema.get('type')
    if t == 'object':
        req = set(schema.get('required', []))
        for name in sorted(schema.get('properties', {})):
            sub = resolve(schema['properties'][name], root)
            yield from _walk(sub, name, name in req, root, prefix)
    # top level non-object bodies are not used by this API


def _walk(sub, name, required, root, prefix):
    path = f'{prefix}{name}'
    t = sub.get('type')
    yield path, sub, required, prefix
    if t == 'array':
        item = resolve(sub['items'], root)
        if item.get('type') == 'object':
            req = set(item.get('required', []))
            for n2 in sorted(item.get('properties', {})):
                s2 = resolve(item['properties'][n2], root)
                yield from _walk(s2, n2, n2 in req, root, f'{path}[].')


def set_path(body, path, value, missing=False):
    body = copy.deepcopy(body)
    parts = path.replace('[]', '').split('.')
    node = body
    for i, p in enumerate(parts):
        if p == '':
            continue
        last = i == len(parts) - 1
        if isinstance(node, list):
            node = node[0]
        if last:
            tgt = node[0] if isinstance(node, list) else node
            if missing:
                tgt.pop(p, None)
            else:
                tgt[p] = value
        else:
            node = node[p]
    return body


def classes_for(path, sch, required, op):
    """Return list of (technique, class, value, expected, constraint). value may be the sentinel MISSING."""
    MISSING = '__missing__'
    t = sch.get('type')
    out = []
    ref = sch.get('x-reference')
    if required:
        out.append(('EP', 'missing-required', MISSING, 'invalid', 'required'))
    if t in ('number', 'integer'):
        lo, hi, step = sch.get('minimum'), sch.get('maximum'), sch.get('multipleOf')
        if t == 'number':   # YAML ints (e.g. `minimum: 0`) are normalised to exact Decimals so every value is emitted as a decimal string
            lo, hi, step = [None if v is None else Decimal(str(v)) for v in (lo, hi, step)]
        excl = bool(sch.get('exclusiveMinimum'))
        unit = step if step is not None else (Decimal(1))
        out.append(('EP', 'valid-typical', valid_sample(sch), 'valid', 'type'))
        out.append(('EP', 'not-a-number', 'abc', 'invalid', 'type'))
        out.append(('EP', 'null', None, 'invalid', 'nullable=false'))
        out.append(('EP', 'empty-string', '', 'invalid', 'type'))
        if t == 'number' and step is not None:
            out.append(('EP', 'too-many-decimals', '1.' + '1' * (places(step) + 1), 'invalid', f'multipleOf {step}'))
        if t == 'integer':
            out.append(('EP', 'fractional', Decimal('1.5'), 'invalid', 'type=integer'))
        if ref:
            out.append(('EP', 'unknown-reference', 999999999, 'invalid', f'x-reference {ref}'))
            out.append(('EP', 'negative', -1, 'invalid', f'minimum {lo}'))
            if lo is not None:
                out.append(('BVA', 'below-minimum', int(lo) - 1, 'invalid', f'minimum {lo}'))
        else:
            if lo is not None:
                lo_exp = 'invalid' if excl else 'valid'
                out.append(('EP', 'below-range', s(lo - Decimal(1) if t == 'number' else lo - 1), 'invalid', f'minimum {lo}'))
                out.append(('BVA', 'min-below', s(lo - unit), 'invalid', f'minimum {lo}'))
                out.append(('BVA', 'min-at', s(lo), lo_exp, f"minimum {lo}{' (exclusive)' if excl else ''}"))
                out.append(('BVA', 'min-above', s(lo + unit), 'valid', f'minimum {lo}'))
            if hi is not None:
                out.append(('EP', 'above-range', s(hi + Decimal(1)), 'invalid', f'maximum {hi}'))
                out.append(('BVA', 'max-below', s(hi - unit), 'valid', f'maximum {hi}'))
                out.append(('BVA', 'max-at', s(hi), 'valid', f'maximum {hi}'))
                out.append(('BVA', 'max-above', s(hi + unit), 'invalid', f'maximum {hi}'))
        if op.get('x-quantity-limit-from') and path.endswith('quantity'):
            lim = op['x-quantity-limit-from']
            u = s(unit)
            out.append(('BVA', 'limit-below', {'$available': '-' + u}, 'valid', f'quantity <= {lim}'))
            out.append(('BVA', 'limit-at', {'$available': '0'}, 'valid', f'quantity <= {lim}'))
            out.append(('BVA', 'limit-above', {'$available': '+' + u}, 'invalid', f'quantity <= {lim}'))
    elif t == 'string':
        mx, mn = sch.get('maxLength'), sch.get('minLength', 0)
        out.append(('EP', 'valid-typical', valid_sample(sch), 'valid', 'type'))
        out.append(('EP', 'wrong-type', ['x'], 'invalid', 'type=string'))
        if mn == 0:
            out.append(('EP', 'empty-string', '', 'valid', 'minLength 0'))
        if mx is not None:
            out.append(('BVA', 'maxlen-below', 'a' * (mx - 1), 'valid', f'maxLength {mx}'))
            out.append(('BVA', 'maxlen-at', 'a' * mx, 'valid', f'maxLength {mx}'))
            out.append(('BVA', 'maxlen-above', 'a' * (mx + 1), 'invalid', f'maxLength {mx}'))
    elif t == 'boolean':
        out.append(('EP', 'true', True, 'valid', 'type'))
        out.append(('EP', 'false', False, 'valid', 'type'))
        out.append(('EP', 'not-a-boolean', 'maybe', 'invalid', 'type'))
    elif t == 'array':
        mn, mx = sch.get('minItems'), sch.get('maxItems')
        out.append(('EP', 'not-an-array', 'abc', 'invalid', 'type=array'))
        out.append(('EP', 'null', None, 'invalid', 'nullable=false'))
        if mn is not None:
            out.append(('BVA', 'minitems-below', ('ARRAY', mn - 1), 'invalid' if mn - 1 < mn else 'valid', f'minItems {mn}'))
            out.append(('BVA', 'minitems-at', ('ARRAY', mn), 'valid', f'minItems {mn}'))
            out.append(('BVA', 'minitems-above', ('ARRAY', mn + 1), 'valid', f'minItems {mn}'))
        if mx is not None:
            out.append(('BVA', 'maxitems-below', ('ARRAY', mx - 1), 'valid', f'maxItems {mx}'))
            out.append(('BVA', 'maxitems-at', ('ARRAY', mx), 'valid', f'maxItems {mx}'))
            out.append(('BVA', 'maxitems-above', ('ARRAY', mx + 1), 'invalid', f'maxItems {mx}'))
    return out


def generate(spec_path):
    root, digest = load_spec(spec_path)
    cases = []
    for url in sorted(root['paths']):
        for method in sorted(root['paths'][url]):
            op = root['paths'][url][method]
            body_schema = (op.get('requestBody', {}).get('content', {}).get('application/json', {}) or {}).get('schema')
            if not body_schema:
                continue
            body_schema = resolve(body_schema, root)
            template = build_valid(body_schema, root)
            opid = op.get('operationId', f'{method}{url}')
            for path, sch, required, _prefix in leaf_fields(body_schema, root):
                for technique, klass, value, expected, constraint in classes_for(path, sch, required, op):
                    if value == '__missing__':
                        body = set_path(template, path, None, missing=True)
                    elif isinstance(value, tuple) and value[0] == 'ARRAY':
                        body = set_path(template, path, [copy.deepcopy(template[path.split('.')[0]][0]) for _ in range(value[1])])
                        value = f'{value[1]} item(s)'
                    else:
                        body = set_path(template, path, s(value) if isinstance(value, Decimal) else value)
                    cases.append({'id': f'{opid}:{path}:{technique}:{klass}', 'operation': opid, 'method': method.upper(), 'path': url,
                                  'field': path, 'technique': technique, 'class': klass,
                                  'value': s(value) if isinstance(value, Decimal) else value, 'expected': expected,
                                  'constraint': constraint, 'required': required, 'body': body})
    return {'spec': spec_path, 'spec_sha256': digest, 'count': len(cases), 'cases': cases}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('spec'); ap.add_argument('-o', '--out')
    a = ap.parse_args(argv)
    data = generate(a.spec)
    text = json.dumps(data, indent=1, sort_keys=True, default=str) + '\n'
    if a.out:
        open(a.out, 'w').write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
