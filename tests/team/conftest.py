"""Root conftest for own tests: records outcome + requirement/risk markers of every test to evidence/traceability/<level>.json
(used by tools/gen_traceability.py, so the traceability matrix is generated from real results, never hand-edited)."""
import json, os
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_RESULTS = {}


def _level(nodeid):
    return nodeid.split('/')[0] if '/' in nodeid else 'root'


def pytest_runtest_logreport(report):
    if report.when == 'call' or (report.when == 'setup' and report.outcome != 'passed') or report.outcome == 'skipped':
        if report.when == 'teardown':
            return
        outcome = 'xfailed' if hasattr(report, 'wasxfail') and report.outcome == 'skipped' else \
                  'xpassed' if hasattr(report, 'wasxfail') and report.outcome == 'passed' else report.outcome
        _RESULTS[report.nodeid] = outcome


def pytest_collection_modifyitems(items):
    for it in items:
        it._trace = {'req': sorted({a for m in it.iter_markers('req') for a in m.args}),
                     'risk': sorted({a for m in it.iter_markers('risk') for a in m.args})}
        _RESULTS.setdefault(it.nodeid, 'not-run')
    pytest._trace_items = {it.nodeid: it._trace for it in items} if not hasattr(pytest, '_trace_items') else {**pytest._trace_items, **{it.nodeid: it._trace for it in items}}


def pytest_sessionfinish(session):
    items = getattr(pytest, '_trace_items', {})
    levels = {}
    for nodeid, outcome in _RESULTS.items():
        levels.setdefault(_level(nodeid), []).append({'id': nodeid, 'outcome': outcome, **items.get(nodeid, {'req': [], 'risk': []})})
    outdir = os.path.join(ROOT, 'evidence', 'traceability')
    os.makedirs(outdir, exist_ok=True)
    for lvl, rows in levels.items():
        path = os.path.join(outdir, f'{lvl}.json')
        old = {}
        if os.path.exists(path) and os.environ.get('TRACE_MERGE', '1') == '1':
            old = {r['id']: r for r in json.load(open(path))}
        old.update({r['id']: r for r in rows})
        json.dump(sorted(old.values(), key=lambda r: r['id']), open(path, 'w'), indent=0)
