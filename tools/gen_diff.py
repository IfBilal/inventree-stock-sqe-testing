#!/usr/bin/env python3
"""Show the effect of spec changes on generated data. Usage: gen_diff.py before.json after.json > diff.md"""
import json, sys
b = {c['id']: c for c in json.load(open(sys.argv[1]))['cases']}
a = {c['id']: c for c in json.load(open(sys.argv[2]))['cases']}
print(f'# Generator diff\n\nBefore: {len(b)} cases · After: {len(a)} cases\n')
print('| Case id | Before (value → expected) | After (value → expected) |\n|---|---|---|')
def show(c):
    v = str(c['value']); v = v if len(v) < 30 else f'{v[:12]}…({len(v)} chars)'
    return f"`{v}` → {c['expected']}"
n = 0
for k in sorted(set(a) | set(b)):
    if k not in a: print(f'| {k} | {show(b[k])} | *removed* |'); n += 1
    elif k not in b: print(f'| {k} | *new* | {show(a[k])} |'); n += 1
    elif (a[k]['value'], a[k]['expected']) != (b[k]['value'], b[k]['expected']): print(f'| {k} | {show(b[k])} | {show(a[k])} |'); n += 1
print(f'\n**{n} cases changed.**')
