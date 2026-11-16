#!/usr/bin/env python3
"""CI hygiene gate: the pipeline must have NO escape hatches (project statement §2: `continue-on-error`, `|| true`).
Scans .github/workflows/*.yml and scripts/*.sh used by CI. Exit 1 on any hit."""
import glob, os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PATTERNS = [(re.compile(r'continue-on-error\s*:\s*(true|\$\{\{)', re.I), 'continue-on-error'),
            (re.compile(r'\|\|\s*true\b'), '|| true'),
            (re.compile(r'\|\|\s*exit\s+0\b'), '|| exit 0'),
            (re.compile(r'\|\|\s*:\s*($|;|\))'), '|| :'),
            (re.compile(r'set\s+\+e\b'), 'set +e'),
            (re.compile(r'if:\s*always\(\)'), 'if: always()')]
bad = []
files = glob.glob(os.path.join(ROOT, '.github/workflows/*.y*ml')) + [os.path.join(ROOT, 'scripts', s) for s in ('coverage_unit.sh', 'test_unit.sh', 'test_api.sh', 'test_e2e.sh', 'mutation_setup.sh')]
for f in files:
    if not os.path.exists(f):
        continue
    for n, line in enumerate(open(f), 1):
        code = line.split('#', 1)[0]
        for pat, name in PATTERNS:
            if pat.search(code):
                bad.append(f'{os.path.relpath(f, ROOT)}:{n}: {name}: {line.strip()}')
if bad:
    print('ESCAPE HATCHES FOUND:\n' + '\n'.join(bad)); sys.exit(1)
print(f'no escape hatches in {len(files)} files')
