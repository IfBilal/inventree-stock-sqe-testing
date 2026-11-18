#!/usr/bin/env python3
"""Markdown tables of the k6 results: baseline (before the DEF-06 fix) and the re-measurements after it (docs/PERFORMANCE.md §7)."""
import json, os
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SETS = [('baseline (before the fix), Basic auth on every request, dev server', 'reports/performance/baseline'),
        ('after the DEF-06 fix, Basic auth on every request (same script as the baseline), dev server', 'reports/performance'),
        ('after the fix, **API token** auth (client logs in once), dev server — **the EC-3 measurement**', 'reports/performance/token'),
        ('after the fix, Basic auth, **gunicorn with 4 worker processes**', 'reports/performance/gunicorn')]
out = ['| Set | Run | Requests (60 s hold) | Requests/s | median ms | **p95 ms** | **Failures** |', '|---|---|---|---|---|---|---|']
for name, d in SETS:
    for vu in (1, 5):
        for run in (1, 2):
            p = os.path.join(R, d, f'summary_{vu}vu_run{run}.json')
            if not os.path.exists(p): continue
            m = json.load(open(p))['metrics']
            h, f, n = m['http_req_duration{phase:hold}'], m['http_req_failed{phase:hold}'], m['http_reqs{phase:hold}']
            fr = f.get('value', f.get('rate'))
            out.append(f"| {name} | {vu} user{'s' if vu > 1 else ''}, run {run} | {n['count']} | {n['count'] / 60:.1f} | {h['med']:.0f} | **{h['p(95)']:.0f}** | **{100 * fr:.2f} %** |")
print('\n'.join(out))
