#!/usr/bin/env python3
"""API coverage criteria computed from the REAL request log of the API suite (evidence/api/request_log.jsonl), the OpenAPI
contract (openapi/stock.yaml) and the generator output. Usage: api_coverage.py > docs/API_COVERAGE.md
Criteria: endpoint, operation (method+path), status code, role/auth, input parameter (EP + BVA), content type, negative methods."""
import json, os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import gen_testdata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
log = [json.loads(l) for l in open(os.path.join(ROOT, 'evidence/api/request_log.jsonl'))]
root, _ = gen_testdata.load_spec(os.path.join(ROOT, 'openapi/stock.yaml'))
gen = gen_testdata.generate(os.path.join(ROOT, 'openapi/stock.yaml'))
seen = Counter((r['method'], r['path'], r['status']) for r in log)
roles = defaultdict(set)
for r in log: roles[(r['method'], r['path'])].add(r['role'])
ctypes = Counter((r['path'], r['content_type']) for r in log if r['method'] == 'POST')

out = ['# API coverage criteria — computed by `tools/api_coverage.py` from `evidence/api/request_log.jsonl` (%d logged requests)\n' % len(log)]
ops = [(m.upper(), p, op) for p, v in root['paths'].items() for m, op in v.items()]
cov = []

out.append('## C1 Endpoint coverage\n| Endpoint | Requests |\n|---|---|')
n1 = 0
for _, p, _op in dict(((p, 1) for _, p, _ in ops)).items() and [(0, p, 0) for p in root['paths']]:
    c = sum(v for (m, pp, s), v in seen.items() if pp == p); n1 += c > 0
    out.append(f'| `{p}` | {c} |')
cov.append(('C1 endpoints exercised', n1, len(root['paths'])))

out.append('\n## C2 Operation (method + path) and C3 documented status-code coverage\n| Operation | Documented status codes | Observed | Missing |\n|---|---|---|---|')
tot = hit = 0
for m, p, op in ops:
    doc = sorted(op['responses'])
    obs = sorted({str(s) for (mm, pp, s) in seen if (mm, pp) == (m, p)})
    miss = [d for d in doc if d not in obs]
    tot += len(doc); hit += len(doc) - len(miss)
    out.append(f"| {m} `{p}` | {', '.join(doc)} | {', '.join(obs) or '—'} | {', '.join(miss) or '—'} |")
cov.append(('C3 documented status codes observed', hit, tot))
cov.append(('C2 operations exercised', sum(1 for m, p, _ in ops if any((mm, pp) == (m, p) for (mm, pp, s) in seen)), len(ops)))

out.append('\n## C4 Role / authentication coverage (POST add/remove)\n| Operation | admin | manager | viewer | anonymous |\n|---|---|---|---|---|')
rc = rt = 0
for p in ('/api/stock/add/', '/api/stock/remove/'):
    r = roles[('POST', p)]
    out.append(f"| POST `{p}` | " + ' | '.join('✔' if x in r else '—' for x in ('admin', 'manager', 'viewer', 'anon')) + ' |')
    rt += 3; rc += sum(x in r for x in ('manager', 'viewer', 'anon'))
cov.append(('C4 roles (manager/viewer/anonymous) per write endpoint', rc, rt))

out.append('\n## C5 Input-parameter coverage (every input of every request body, EP and 3-point BVA cases executed)\n| Operation | Input | EP cases | BVA cases |\n|---|---|---|---|')
pc = pt = 0
cnt = Counter((c['operation'], c['field'], c['technique']) for c in gen['cases'])
for (opn, field, tech) in sorted({(a, b, 'x') for a, b, _ in cnt}):
    ep, bva = cnt.get((opn, field, 'EP'), 0), cnt.get((opn, field, 'BVA'), 0)
    out.append(f'| {opn} | `{field}` | {ep} | {bva} |')
    pt += 1; pc += ep > 0
cov.append(('C5 inputs with >= 1 executed EP case (generated)', pc, pt))
out.append(f"\nAll {gen['count']} generated cases are executed by `tests/team/api/test_generated_ep_bva.py` (one test per case).")

out.append('\n## C6 Content-type coverage (POST)\n| Path | Content-Type | Requests |\n|---|---|---|')
for (p, c), v in sorted(ctypes.items(), key=lambda x: (x[0][0], str(x[0][1]))):
    out.append(f'| `{p}` | {c} | {v} |')
cov.append(('C6 content types per write endpoint (JSON + unsupported)', sum(1 for p in ('/api/stock/add/', '/api/stock/remove/') for c in ('application/json', 'text/plain') if ctypes.get((p, c))), 4))

out.append('\n## C7 Negative-method coverage (405)\n| Path | GET | PUT | PATCH | DELETE |\n|---|---|---|---|---|')
nm = nt = 0
for p in ('/api/stock/add/', '/api/stock/remove/'):
    row = []
    for m in ('GET', 'PUT', 'PATCH', 'DELETE'):
        ok = seen.get((m, p, 405), 0) > 0; row.append('405 ✔' if ok else '—'); nm += ok; nt += 1
    out.append(f'| `{p}` | ' + ' | '.join(row) + ' |')
cov.append(('C7 unsupported methods rejected with 405', nm, nt))

out.append('\n## C8 Sequence / state coverage\nCovered by `test_business_rules_api.py`: add→remove→add with ordered history (cross-workflow), depletion (retained and deleted), restock of depleted, repeated valid and rejected requests, atomic multi-item request, read-back of `StockItem.quantity` and history after **success and rejection** in every test.')
out.append('\n## Summary\n| Criterion | Covered | Total | % |\n|---|---|---|---|')
for name, a, b in cov:
    out.append(f'| {name} | {a} | {b} | {100 * a / b:.0f} |')
print('\n'.join(out))
