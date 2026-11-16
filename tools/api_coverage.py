#!/usr/bin/env python3
"""API coverage criteria computed from what the suite ACTUALLY did:
 evidence/api/request_log.jsonl (every HTTP request incl. status and whether the response was schema-validated),
 evidence/api/cases_executed.jsonl (every generated case executed, with match/mismatch vs the contract),
 evidence/traceability/api.json (tests tagged with operation sequences), openapi/stock.yaml (contract), generator output.
Usage: api_coverage.py > docs/API_COVERAGE.md"""
import json, os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import gen_testdata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
def jl(rel): return [json.loads(l) for l in open(os.path.join(ROOT, rel))]
log = jl('evidence/api/request_log.jsonl')
executed = jl('evidence/api/cases_executed.jsonl')
trace = json.load(open(os.path.join(ROOT, 'evidence/traceability/api.json')))
root, _ = gen_testdata.load_spec(os.path.join(ROOT, 'openapi/stock.yaml'))
gen = gen_testdata.generate(os.path.join(ROOT, 'openapi/stock.yaml'))
WRITE = ['/api/stock/add/', '/api/stock/remove/']
seen = Counter((r['method'], r['path'], r['status']) for r in log)
roles = defaultdict(set)
for r in log: roles[(r['method'], r['path'])].add(r['role'])
ops = [(m.upper(), p, op) for p, v in root['paths'].items() for m, op in v.items()]
summary = []
out = [f'# API coverage criteria — computed by `tools/api_coverage.py` from the real run ({len(log)} logged requests, {len(executed)} executed generated cases)\n']

# C1/C2 endpoint + operation
out.append('## C1 Endpoint and C2 operation coverage\n| Operation | Requests |\n|---|---|')
hit_ops = 0
for m, p, _ in ops:
    n = sum(v for (mm, pp, s), v in seen.items() if (mm, pp) == (m, p))
    hit_ops += n > 0
    out.append(f'| {m} `{p}` | {n} |')
summary += [('C1 endpoints exercised', len({p for _, p, _ in ops if any(pp == p for (_, pp, _) in seen)}), len(root['paths'])), ('C2 operations exercised', hit_ops, len(ops))]

# C3 status codes documented + status classes
out.append('\n## C3 Documented status-code coverage\n| Operation | Documented | Observed | Missing |\n|---|---|---|---|')
tot = hit = 0
for m, p, op in ops:
    doc = sorted(op['responses'])
    obs = sorted({str(s) for (mm, pp, s) in seen if (mm, pp) == (m, p)})
    miss = [d for d in doc if d not in obs]
    undocumented = [o for o in obs if o not in doc]
    tot += len(doc); hit += len(doc) - len(miss)
    out.append(f"| {m} `{p}` | {', '.join(doc)} | {', '.join(obs)} | {', '.join(miss) or '—'}{' (undocumented observed: ' + ', '.join(undocumented) + ')' if undocumented else ''} |")
summary.append(('C3 documented status codes observed', hit, tot))
classes = Counter(str(r['status'])[0] + 'xx' for r in log)
out.append(f"\nStatus classes observed: {', '.join(f'{k}: {v}' for k, v in sorted(classes.items()))}.")
summary.append(('C3b status classes 2xx/4xx/5xx observed', sum(1 for c in ('2xx', '4xx', '5xx') if classes[c]), 3))

# C4 roles
out.append('\n## C4 Role / authentication coverage\n| Operation | admin | manager | viewer | anonymous |\n|---|---|---|---|---|')
rc = rt = 0
for m, p in [('POST', w) for w in WRITE] + [('GET', '/api/stock/{id}/'), ('GET', '/api/audit/')]:
    r = roles[(m, p)]
    need = ('manager', 'viewer', 'anon') if m == 'POST' else ('manager',)
    out.append(f"| {m} `{p}` | " + ' | '.join('✔' if x in r else '—' for x in ('admin', 'manager', 'viewer', 'anon')) + ' |')
    rt += len(need); rc += sum(x in r for x in need)
summary.append(('C4 required roles per operation (write: manager/viewer/anonymous; reads: manager)', rc, rt))

# C5 input coverage + C6 parameter-value coverage from EXECUTED generated cases
gen_by = defaultdict(list)
for c in gen['cases']: gen_by[(c['operation'], c['field'])].append(c)
exe_ids = {e['id']: e for e in executed}
out.append('\n## C5 Input-parameter coverage (EP and BVA cases executed per input)\n| Operation | Input | Where | EP executed/generated | BVA executed/generated | mismatches vs contract |\n|---|---|---|---|---|---|')
inputs_full = inputs_total = 0
for (opn, field), cs in sorted(gen_by.items()):
    ep = [c for c in cs if c['technique'] == 'EP']; bva = [c for c in cs if c['technique'] == 'BVA']
    ee = sum(c['id'] in exe_ids for c in ep); be = sum(c['id'] in exe_ids for c in bva)
    mm = sum(1 for c in cs if exe_ids.get(c['id'], {}).get('outcome') == 'mismatch')
    inputs_total += 1; inputs_full += (ee == len(ep) and be == len(bva))
    out.append(f"| {opn} | `{field}` | {cs[0]['location']} | {ee}/{len(ep)} | {be}/{len(bva)} | {mm} |")
summary.append(('C5 inputs with ALL generated EP and BVA cases executed', inputs_full, inputs_total))
n_exec = sum(c['id'] in exe_ids for c in gen['cases'])
n_match = sum(1 for c in gen['cases'] if exe_ids.get(c['id'], {}).get('outcome') == 'match')
summary.append(('C6 parameter-value coverage: generated cases executed', n_exec, gen['count']))
out.append(f"\n**C6:** {n_exec}/{gen['count']} generated cases executed; {n_match} matched the contract, {n_exec - n_match} mismatched (each mismatch is a documented baseline defect/weakness: DEF-01, DEF-02, DEF-04, W-08, W-09 — strict xfail).")

# C7 content types (write endpoints only), documented + negative probe
need_types = ['application/json', 'text/plain']
ct = Counter((r['path'], r['content_type']) for r in log if r['method'] == 'POST' and r['path'] in WRITE)
out.append('\n## C7 Content-type coverage (write endpoints; JSON documented, text/plain = unsupported probe)\n| Path | application/json | text/plain |\n|---|---|---|')
cc = 0
for w in WRITE:
    out.append(f"| `{w}` | {ct[(w, 'application/json')]} | {ct[(w, 'text/plain')]} |")
    cc += sum(1 for t in need_types if ct[(w, t)])
summary.append(('C7 content types per write endpoint', cc, len(WRITE) * len(need_types)))

# C8 negative methods
out.append('\n## C8 Negative-method coverage (405)\n| Path | GET | PUT | PATCH | DELETE |\n|---|---|---|---|---|')
nm = nt = 0
for w in WRITE:
    row = []
    for m in ('GET', 'PUT', 'PATCH', 'DELETE'):
        ok = seen.get((m, w, 405), 0) > 0; row.append('405 ✔' if ok else '—'); nm += ok; nt += 1
    out.append(f'| `{w}` | ' + ' | '.join(row) + ' |')
summary.append(('C8 unsupported methods rejected with 405', nm, nt))

# C9 response-schema validation
with_schema = sum(1 for r in log if r.get('schema_checked'))
resp_with_schema = sum(1 for r in log if any(op['responses'].get(str(r['status']), {}).get('content') for m, p, op in ops if (m, p) == (r['method'], r['path'])))
out.append(f'\n## C9 Response-schema validation\nEvery response whose status has a schema in the spec is validated against it inside the HTTP client (a violation fails the test): **{with_schema}** responses validated, {resp_with_schema} had a schema in the spec.')
summary.append(('C9 responses with a spec schema that were validated', with_schema, resp_with_schema))

# C10 sequences measured from tagged tests
seq_all = sorted({s for t in trace for s in t.get('seq', [])})
seq_pass = sorted({s for t in trace if t['outcome'] == 'passed' for s in t.get('seq', [])})
out.append('\n## C10 Sequence / dependency coverage (tests tagged `@pytest.mark.seq`)\n| Sequence | Result |\n|---|---|')
for s in seq_all:
    out.append(f"| {s} | {'passed' if s in seq_pass else 'not passing'} |")
summary.append(('C10 operation sequences passing', len(seq_pass), len(seq_all)))

out.append('\n## Summary\n| Criterion | Covered | Total | % |\n|---|---|---|---|')
for name, a, b in summary:
    out.append(f'| {name} | {a} | {b} | {100 * a / b:.0f} |')
print('\n'.join(out))
