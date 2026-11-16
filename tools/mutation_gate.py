#!/usr/bin/env python3
"""Mutation-score gate. Score = killed / (total - known equivalent). Known equivalent mutants are listed (with justification) in docs/mutation_equivalents.json
keyed by `function|line|description`. Exit 1 if the score is below the threshold. Usage: mutation_gate.py results.json [threshold]"""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
res = json.load(open(sys.argv[1]))
thr = float(sys.argv[2]) if len(sys.argv) > 2 else 85.0
eq = json.load(open(os.path.join(ROOT, 'docs/mutation_equivalents.json'))) if os.path.exists(os.path.join(ROOT, 'docs/mutation_equivalents.json')) else {}
total = res['total']; killed = sum(r['status'] in ('killed', 'timeout') for r in res['results'])
equiv = sum(1 for r in res['results'] if r['status'] == 'survived' and f"{r['function']}|{r['desc']}" in eq)
score = 100 * killed / (total - equiv) if total - equiv else 100.0
print(f'mutants {total}, killed {killed}, survived {total - killed} (equivalent: {equiv}) -> adjusted score {score:.1f} % (threshold {thr} %)')
for r in res['results']:
    if r['status'] == 'survived' and f"{r['function']}|{r['desc']}" not in eq:
        print('  SURVIVOR', r['id'], r['op'], r['function'], 'L%s' % r['line'], r['desc'])
sys.exit(0 if score >= thr else 1)
