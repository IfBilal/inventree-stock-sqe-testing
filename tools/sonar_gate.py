#!/usr/bin/env python3
"""Quality gate on SonarQube measures (explicit thresholds, justified in docs/CI_QUALITY_GATE.md). Exit 1 when violated.
Usage: sonar_gate.py <host> <token> <project>"""
import json, sys, urllib.request, base64
host, token, project = sys.argv[1:4]
METRICS = 'bugs,vulnerabilities,code_smells,security_hotspots,reliability_rating,security_rating,sqale_rating,coverage,duplicated_lines_density'
req = urllib.request.Request(f'{host}/api/measures/component?component={project}&metricKeys={METRICS}', headers={'Authorization': 'Basic ' + base64.b64encode(f'{token}:'.encode()).decode()})
m = {x['metric']: float(x['value']) for x in json.load(urllib.request.urlopen(req))['component']['measures']}
# threshold, comparator, why
GATE = [('bugs', '==', 0, 'baseline 0; any bug fails'), ('vulnerabilities', '==', 0, 'baseline 0'), ('security_hotspots', '==', 0, 'baseline 0'),
        ('code_smells', '<=', 0, 'baseline 0 smells'), ('reliability_rating', '==', 1.0, 'rating A'), ('security_rating', '==', 1.0, 'rating A'), ('sqale_rating', '==', 1.0, 'rating A'),
        ('coverage', '>=', 38.0, 'whole-module coverage measured 40.2 % at Phase 4; 38 leaves a 2-point tolerance and catches regressions (in-scope logic is gated separately at 100 %)'),
        ('duplicated_lines_density', '<=', 1.0, 'baseline 0.6 %')]
ok = True
for k, op, thr, why in GATE:
    v = m.get(k, 0.0)
    passed = {'==': v == thr, '<=': v <= thr, '>=': v >= thr}[op]
    print(f"{'PASS' if passed else 'FAIL'} {k} = {v} (required {op} {thr}) — {why}")
    ok &= passed
sys.exit(0 if ok else 1)
