#!/usr/bin/env python3
"""Mutation testing of the in-scope business-rule functions (tools/scope_coverage.py SCOPE) with our own AST-based runner.

Why not mutmut / Cosmic Ray alone: mutmut 3.8 was tried first (scripts/mutation_setup.sh, evidence/mutation/mutmut_attempt.log) but its coverage-gathering child
process exits with code 1 on this Django project even though the identical pytest command passes; Cosmic Ray needs one full-suite run per mutant of whole files.
This runner mutates ONLY the in-scope functions, runs the real unit suite for each mutant in isolated parallel copies of the backend, and reports the score.

STANDARD operators (as in mutmut/Cosmic Ray): ROR relational, LCR and/or, UOI remove `not`, CRP constant, RET return flip, AOR +/-, SDL statement deletion, NEG if-condition negation.
CUSTOM operators derived from OUR business rules (>= 2 required by the project statement):
  CBR-1 LIMIT_CLAMP     min(requested, available) <-> max(...)                    (BR-1: removal limited to the available quantity)
  CBR-2 REFERENCE_CHECK flip `x is None` / `x is not None` on sales_order, belongs_to, customer, consumed_by   (BR-2: adjustability decision)
  CBR-3 DEPLETE_RULE    `delete_on_deplete` and `can_delete()` replaced by True / False   (BR-3: deletion on depletion)
  CBR-4 POSITIVE_GUARD  `quantity <= 0` -> `quantity < 0` and `< 0` -> `<= 0` on quantity guards   (BR-1/FR-03: zero and negative quantities)
Usage: python tools/mutate.py --workers 4 --max-per-function 14 [--only stock/models.py::StockItem.take_stock]
"""
import argparse, ast, concurrent.futures as cf, json, os, random, re, shutil, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
from scope_coverage import SCOPE, function_ranges, BASE  # noqa: E402

REF_ATTRS = {'sales_order', 'belongs_to', 'customer', 'consumed_by'}
CMP = {ast.Lt: ('<', '<='), ast.LtE: ('<=', '<'), ast.Gt: ('>', '>='), ast.GtE: ('>=', '>'), ast.Eq: ('==', '!='), ast.NotEq: ('!=', '=='),
       ast.Is: (' is ', ' is not '), ast.IsNot: (' is not ', ' is '), ast.In: (' in ', ' not in '), ast.NotIn: (' not in ', ' in ')}


class Mut:
    def __init__(self, op, start, end, repl, line, desc):
        self.op, self.start, self.end, self.repl, self.line, self.desc = op, start, end, repl, line, desc


def offsets(src):
    lines = src.splitlines(keepends=True)
    starts, pos = [], 0
    for l in lines:
        starts.append(pos); pos += len(l)
    return starts


def generate(src, lo, hi):
    tree = ast.parse(src)
    starts = offsets(src)
    muts = []

    def off(line, col):
        return starts[line - 1] + len(src.splitlines(keepends=True)[line - 1].encode()[:col].decode(errors='ignore'))

    def seg(n):
        return off(n.lineno, n.col_offset), off(n.end_lineno, n.end_col_offset)

    def inside(n):
        return hasattr(n, 'lineno') and lo <= n.lineno <= hi

    def add(op, s, e, repl, line, desc):
        muts.append(Mut(op, s, e, repl, line, desc))

    for fn in ast.walk(tree):
        if not (isinstance(fn, ast.FunctionDef) and lo == fn.lineno):
            continue
        docstring_ids = set()
        if fn.body and isinstance(fn.body[0], ast.Expr) and isinstance(getattr(fn.body[0], 'value', None), ast.Constant):
            docstring_ids.add(id(fn.body[0].value))
        for n in ast.walk(fn):
            if not inside(n):
                continue
            if isinstance(n, ast.Compare):
                left_end = seg(n.left)[1]
                for i, op in enumerate(n.ops):
                    right = n.comparators[i]
                    s = left_end if i == 0 else seg(n.comparators[i - 1])[1]
                    e = seg(right)[0]
                    piece = src[s:e]
                    a, b = CMP[type(op)]
                    if a.strip() in piece:
                        new = piece.replace(a.strip(), b.strip(), 1) if a.strip() != 'is' or 'is not' not in piece else piece.replace('is not', 'is', 1)
                        if type(op) is ast.Is: new = piece.replace('is', 'is not', 1)
                        if type(op) is ast.IsNot: new = piece.replace('is not', 'is', 1)
                        if type(op) is ast.In: new = piece.replace('in', 'not in', 1)
                        if type(op) is ast.NotIn: new = piece.replace('not in', 'in', 1)
                        add('ROR', s, e, new, n.lineno, f'{a.strip()} -> {b.strip()}')
                        # CBR-2 reference check flip on the four adjustability attributes
                        if isinstance(op, (ast.Is, ast.IsNot)) and isinstance(n.left, ast.Attribute) and n.left.attr in REF_ATTRS:
                            add('CBR-2', s, e, new, n.lineno, f'REFERENCE_CHECK {n.left.attr} {a.strip()} None flipped')
                        # CBR-4 positive guard on quantity comparisons
                        if isinstance(op, (ast.LtE, ast.Lt)) and 'quantity' in ast.unparse(n.left):
                            add('CBR-4', s, e, new, n.lineno, f'POSITIVE_GUARD {ast.unparse(n)} boundary moved')
            elif isinstance(n, ast.BoolOp):
                kw, other = ('and', 'or') if isinstance(n.op, ast.And) else ('or', 'and')
                for i in range(len(n.values) - 1):
                    s, e = seg(n.values[i])[1], seg(n.values[i + 1])[0]
                    piece = src[s:e]
                    if kw in piece:
                        add('LCR', s, e, piece.replace(kw, other, 1), n.lineno, f'{kw} -> {other}')
            elif isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
                s, e = seg(n)
                add('UOI', s, e, src[seg(n.operand)[0]:seg(n.operand)[1]], n.lineno, 'remove not')
            elif isinstance(n, ast.Constant) and id(n) not in docstring_ids:
                s, e = seg(n)
                if isinstance(n.value, bool):
                    add('CRP', s, e, 'False' if n.value else 'True', n.lineno, f'{n.value} -> {not n.value}')
                elif isinstance(n.value, int) and not isinstance(n.value, bool):
                    add('CRP', s, e, str(n.value + 1), n.lineno, f'{n.value} -> {n.value + 1}')
            elif isinstance(n, ast.Return) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, bool):
                s, e = seg(n.value)
                add('RET', s, e, 'False' if n.value.value else 'True', n.lineno, f'return {n.value.value} -> {not n.value.value}')
            elif isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub)):
                s, e = seg(n.left)[1], seg(n.right)[0]
                piece = src[s:e]
                a, b = ('+', '-') if isinstance(n.op, ast.Add) else ('-', '+')
                if a in piece:
                    add('AOR', s, e, piece.replace(a, b, 1), n.lineno, f'{a} -> {b}')
            elif isinstance(n, ast.If):
                s, e = seg(n.test)
                add('NEG', s, e, f'not ({src[s:e]})', n.lineno, 'negate if-condition')
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ('min', 'max'):
                s, e = seg(n.func)
                other = 'max' if n.func.id == 'min' else 'min'
                add('CBR-1', s, e, other, n.lineno, f'LIMIT_CLAMP {n.func.id}() -> {other}()')
            elif isinstance(n, ast.Attribute) and n.attr == 'delete_on_deplete' and isinstance(getattr(n, 'ctx', None), ast.Load) and isinstance(n.value, ast.Name) and n.value.id == 'self':
                s, e = seg(n)
                add('CBR-3', s, e, 'True', n.lineno, 'DEPLETE_RULE delete_on_deplete -> True')
                add('CBR-3', s, e, 'False', n.lineno, 'DEPLETE_RULE delete_on_deplete -> False')
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'can_delete':
                s, e = seg(n)
                add('CBR-3', s, e, 'True', n.lineno, 'DEPLETE_RULE can_delete() -> True')
        # statement deletion (side-effect statements) at function level
        for st in ast.walk(fn):
            if isinstance(st, (ast.Assign, ast.AugAssign)) or (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)):
                if not inside(st) or id(getattr(st, 'value', None)) in docstring_ids:
                    continue
                s = starts[st.lineno - 1] + (st.col_offset)
                e = off(st.end_lineno, st.end_col_offset)
                add('SDL', s, e, 'pass', st.lineno, 'delete statement: ' + ast.unparse(st)[:60])
    # drop duplicates and invalid (syntax-breaking) mutants
    seen, out = set(), []
    for m in muts:
        key = (m.op, m.start, m.end, m.repl)
        if key in seen:
            continue
        seen.add(key)
        new = src[:m.start] + m.repl + src[m.end:]
        try:
            compile(new, '<mut>', 'exec')
        except SyntaxError:
            continue
        if new == src:
            continue
        out.append(m)
    return out


def run_pytest(workdir, db, timeout):
    env = dict(os.environ, INVENTREE_DB_NAME=db, TESTING='1')
    t = time.time()
    try:
        p = subprocess.run([sys.executable, '-m', 'pytest', 'tests_team/unit', '-x', '-q', '-p', 'no:warnings', '-p', 'no:cacheprovider', '--no-migrations'],
                           cwd=workdir, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 'timeout', 'TIMEOUT', time.time() - t
    out = p.stdout + p.stderr
    if p.returncode == 0:
        return 'survived', '', time.time() - t
    m = re.search(r'^(FAILED|ERROR) (\S+)', out, re.M)
    return 'killed', (m.group(2) if m else 'collection/other error'), time.time() - t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--max-per-function', type=int, default=14)
    ap.add_argument('--only')
    ap.add_argument('--rerun-survivors', help='results.json of an earlier run: re-run exactly its surviving mutants (same generation, no sampling)')
    ap.add_argument('--seed', type=int, default=20261116)
    ap.add_argument('--timeout', type=int, default=240)
    ap.add_argument('--out', default=os.path.join(ROOT, 'evidence', 'mutation', 'results.json'))
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    # --- plan the mutants
    survivors_key = set()
    if a.rerun_survivors:
        for r in json.load(open(a.rerun_survivors))['results']:
            if r['status'] == 'survived':
                survivors_key.add((r['file'], r['function'], r['op'], r['line'], r['desc']))
    plan = []
    for rel, funcs in SCOPE.items():
        src = open(os.path.join(ROOT, BASE, rel)).read()
        ranges = function_ranges(os.path.join(ROOT, BASE, rel))
        for f in funcs:
            if a.only and a.only != f'{rel}::{f}':
                continue
            lo, hi = ranges[f]
            ms = generate(src, lo, hi)
            if a.rerun_survivors:
                prior = survivors_key
                chosen = [m for m in ms if (rel, f, m.op, m.line, m.desc) in prior]
                for m in sorted(chosen, key=lambda m: m.start):
                    plan.append({'file': rel, 'function': f, 'op': m.op, 'line': m.line, 'desc': m.desc, 'start': m.start, 'end': m.end, 'repl': m.repl})
                continue
            custom = [m for m in ms if m.op.startswith('CBR')]
            std = [m for m in ms if not m.op.startswith('CBR')]
            rnd.shuffle(std)
            chosen = custom + std[:max(0, a.max_per_function - len(custom))]      # every custom mutant is always kept
            for m in sorted(chosen, key=lambda m: m.start):
                plan.append({'file': rel, 'function': f, 'op': m.op, 'line': m.line, 'desc': m.desc, 'start': m.start, 'end': m.end, 'repl': m.repl})
    for i, p in enumerate(plan):
        p['id'] = f'M{i + 1:03d}'
    print(f'planned mutants: {len(plan)} (standard + custom), workers: {a.workers}', flush=True)
    # --- isolated worker copies of the backend (the repo is never modified)
    base = os.path.join(ROOT, 'mutation')
    workers = []
    for w in range(a.workers):
        wd = os.path.join(base, f'w{w}')
        if not os.path.exists(os.path.join(wd, 'stock')):
            shutil.rmtree(wd, ignore_errors=True)
            shutil.copytree(os.path.join(base, 'work'), wd, ignore=shutil.ignore_patterns('mutants', '__pycache__'))
        workers.append(wd)
    # --- baseline must pass in every worker copy
    for w, wd in enumerate(workers):
        st, info, secs = run_pytest(wd, os.path.join(base, f'db{w}.sqlite3'), 900)
        assert st == 'survived', f'baseline FAILS in worker {w}: {info}'
        print(f'baseline ok in worker {w} ({secs:.0f}s)', flush=True)
    originals = {}
    for rel in SCOPE:
        originals[rel] = open(os.path.join(ROOT, BASE, rel)).read()

    def do(job):
        w, p = job
        wd = workers[w]
        path = os.path.join(wd, rel_in_work(p['file']))
        src = originals[p['file']]
        new = src[:p['start']] + p['repl'] + src[p['end']:]
        open(path, 'w').write(new)
        try:
            st, info, secs = run_pytest(wd, os.path.join(base, f'db{w}.sqlite3'), a.timeout)
        finally:
            open(path, 'w').write(src)
        return p, st, info, secs

    def rel_in_work(rel):
        return rel                                   # work copies mirror upstream/src/backend/InvenTree/

    results, t0 = [], time.time()
    # round-robin jobs onto worker slots with a queue per worker (each worker runs its jobs sequentially)
    queues = [[] for _ in workers]
    for i, p in enumerate(plan):
        queues[i % len(workers)].append((i % len(workers), p))

    def run_queue(q):
        out = []
        for job in q:
            p, st, info, secs = do(job)
            out.append({**{k: v for k, v in p.items() if k not in ('start', 'end', 'repl')}, 'status': st, 'killed_by': info, 'seconds': round(secs, 1),
                        'original': originals[p['file']][p['start']:p['end']][:80], 'mutated': p['repl'][:80]})
            print(f"{p['id']} {p['op']:6s} {p['function'][:38]:38s} L{p['line']:<5d} {st:8s} ({secs:.0f}s) {p['desc'][:50]}", flush=True)
        return out

    with cf.ThreadPoolExecutor(max_workers=len(workers)) as ex:
        for r in ex.map(run_queue, queues):
            results += r
    results.sort(key=lambda r: r['id'])
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    killed = sum(r['status'] in ('killed', 'timeout') for r in results)
    json.dump({'total': len(results), 'killed': killed, 'survived': len(results) - killed, 'score_raw': round(100 * killed / len(results), 1),
               'seconds': round(time.time() - t0), 'results': results}, open(a.out, 'w'), indent=1)
    print(f'DONE total={len(results)} killed={killed} survived={len(results) - killed} score={100 * killed / len(results):.1f}% in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
