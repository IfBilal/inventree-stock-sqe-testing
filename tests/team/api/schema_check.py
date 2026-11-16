"""Validate HTTP responses against the response schemas of openapi/stock.yaml (OpenAPI 3.0 -> JSON Schema translation)."""
import os
import jsonschema, yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SPEC = yaml.safe_load(open(os.path.join(ROOT, 'openapi', 'stock.yaml')))


def _resolve(node):
    if isinstance(node, dict):
        if '$ref' in node:
            ref = SPEC
            for part in node['$ref'].lstrip('#/').split('/'):
                ref = ref[part]
            return _resolve(ref)
        out = {k: _resolve(v) for k, v in node.items() if k not in ('nullable', 'format', 'x-wire-format', 'x-reference')}
        if node.get('nullable'):
            t = out.get('type')
            out['type'] = [t, 'null'] if isinstance(t, str) else t
            if 'enum' in out and None not in out['enum']:
                out['enum'] = out['enum'] + [None]
        return out
    if isinstance(node, list):
        return [_resolve(v) for v in node]
    return node


def response_schema(method, path_template, status):
    op = SPEC['paths'].get(path_template, {}).get(method.lower())
    if not op:
        return None
    content = (op.get('responses', {}).get(str(status), {}) or {}).get('content', {}).get('application/json')
    return _resolve(content['schema']) if content else None


def validate(method, path_template, status, body):
    """Return None if valid or if the spec defines no schema for this response; else an error string."""
    schema = response_schema(method, path_template, status)
    if schema is None:
        return None
    try:
        jsonschema.Draft7Validator(schema).validate(body)
    except jsonschema.ValidationError as e:
        return f'{e.message} at {list(e.absolute_path)}'
    return None
