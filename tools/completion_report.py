#!/usr/bin/env python3
"""Generate docs/COMPLETION_REPORT.md (test completion report, release/hold decision with actual vs target) and reports/weekly/week-2.md
from the evidence files and the GitHub API. Usage: completion_report.py"""
import collections, csv, glob, json, os, re, subprocess

R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
J = lambda p: json.load(open(os.path.join(R, p)))
REPO = 'IfBilal/inventree-stock-sqe-testing'


def gh(*args):
    try:
        return json.loads(subprocess.run(['gh', *args], capture_output=True, text=True, timeout=120, check=True).stdout)
    except Exception:
        return None


defects = J('docs/defects.json')
open_def = [d for d in defects if d['status'].startswith('Open')]
crit_high_open = [d for d in open_def if d['severity'] in ('Critical', 'High')]
mut = J('evidence/mutation/results.json')
eq = J('docs/mutation_equivalents.json')
equiv_n = sum(1 for r in mut['results'] if r['status'] == 'survived' and f"{r['function']}|{r['desc']}|{r['original']}" in eq)
mut_adj = 100 * mut['killed'] / (mut['total'] - equiv_n)
cov = open(os.path.join(R, 'docs/COVERAGE_SCOPE.md')).read()
m = re.search(r'statements (\d+)/(\d+) \(([\d.]+) %\), branches (\d+)/(\d+) \(([\d.]+) %\)', cov)
st_cov, br_cov = (m.group(3), m.group(6)) if m else ('?', '?')
fl = {}
for lv in ('unit', 'api'):
    p = os.path.join(R, f'evidence/traceability/{lv}.json')
    if os.path.exists(p):
        c = collections.Counter(r['outcome'] for r in J(f'evidence/traceability/{lv}.json'))
        fl[lv] = c
gen_tests = 29
pw = J('evidence/phase7/playwright_report_e2e.json')
pw_stats = pw.get('stats', {})
am = J('evidence/security/access_matrix_results.json')
zmsg_n = J('evidence/security/zap_number_of_messages.json')['numberOfMessages']
perf = {}
for vu in (1, 5):
    for run in (1, 2):
        d = J(f'reports/performance/summary_{vu}vu_run{run}.json')['metrics']
        perf[(vu, run)] = (d['http_req_duration{phase:hold}']['p(95)'], d['http_req_failed{phase:hold}'].get('value', d['http_req_failed{phase:hold}'].get('rate', 0)) * 100)
sonar = {x['metric']: x.get('value') for x in J('evidence/sonar/project_measures_phase4.json')['component']['measures']}
api_cov_pct = '100'
tr = open(os.path.join(R, 'docs/TRACEABILITY.md')).read()
mt = re.search(r'tested: (\d+) / (\d+).*?verified passing: (\d+) / (\d+)', tr, re.S)
req_tested, req_total, req_ver = (mt.group(1), mt.group(2), mt.group(3)) if mt else ('?', '?', '?')
prs = gh('pr', 'list', '--repo', REPO, '--state', 'all', '--json', 'number,title,state,mergedAt,headRefName,url,statusCheckRollup', '--limit', '20') or []
runs = gh('run', 'list', '--repo', REPO, '--limit', '30', '--json', 'databaseId,event,headBranch,conclusion,status,displayTitle,url,createdAt') or []

# ---------------------------------------------------------------- completion report
o = ['# TEST COMPLETION REPORT AND RELEASE / HOLD DECISION\n',
     f'System under test: InvenTree 1.8.0 dev, Stock module (WF-A Add stock, WF-B Remove stock), upstream commit `1f51dfe64bf4717fd95df51f1055ffb7a991a01d`, MIT. Repository: https://github.com/{REPO}. Team: 24I-3166, 24I-3015, 24I-3106.\n',
     '## 1. Decision\n> # **HOLD** — the build is **not recommended for release** as it stands.\n',
     f"Reasons (evidence-based): exit criteria **EC-1 (functional) and EC-3 (performance) are not met**, EC-2 (security) is met on the tested scope. Open Critical/High defects: {', '.join(d['id'] for d in crit_high_open)} (see §4). The over-removal data-loss defect DEF-01 was fixed through a pull request (§6) and verified by the unit, API and browser levels, but DEF-03 (overflow makes an item unreadable and breaks the whole stock list) and DEF-06 (concurrent adjustments fail with HTTP 500 on SQLite) remain. A release would be justified after those are fixed and the performance test is repeated on the production database (PostgreSQL).\n",
     '### 1.1 Release criteria — actual versus target (the three exit criteria of the test plan, `docs/TEST_PLAN.md` §7)\n| ID | Category | Target | Actual (evidence) | Met? |\n|---|---|---|---|---|',
     f"| EC-1 | Functional (risks PR-01, PR-03, PR-06) | 100 % of own business-rule tests pass on the fixed build; **0 open Critical/High defects**; 0 unjustified uncovered lines (in-scope statements 100 %, branches 100 % with justification); all 6 basis paths and MC/DC pairs of `validate_pk` pass; retried request yields 0 duplicates | Tests pass on the fixed build (unit/API/E2E, §2). In-scope coverage statements **{st_cov} %**, branches **{br_cov} %** (1 unreachable branch justified: `docs/COVERAGE_JUSTIFICATION.md`). MCC rows 32/32, MC/DC set and 6 basis paths pass. Recovery tests: 0 duplicates. **Open Critical/High defects: {len(crit_high_open)} ({', '.join(d['id'] for d in crit_high_open)})** | **NO** (open Critical/High) |",
     f"| EC-2 | Security (risks PR-02, PR-10) | all access-matrix decisions (≥ 4, ≥ 1 allowed, ≥ 1 denied) match; 0 unresolved High/Critical in the audited dependency set | **{sum(1 for x in am if x['ok'])}/{len(am)}** access decisions match (allowed and denied). Backend: 166 packages, 0 vulnerabilities. Frontend: 1 High advisory (`zod`, build tooling only, not in the served bundle) — dispositioned (accepted, SEC-03 / `docs/SECURITY.md` §4.2); 2 moderate `react-router` advisories in the shipped bundle (SEC-03, open, Medium) | **YES** on the tested scope (with dispositions) |",
     f"| EC-3 | Performance (risk PR-08) | `POST /api/stock/remove/` at 5 users: p95 ≤ 500 ms and unexpected failures < 1 % | 1 user: p95 {perf[(1,1)][0]:.0f} / {perf[(1,2)][0]:.0f} ms, failures {perf[(1,1)][1]:.1f} % / {perf[(1,2)][1]:.1f} % (met). **5 users: p95 {perf[(5,1)][0]:.0f} / {perf[(5,2)][0]:.0f} ms, failures {perf[(5,1)][1]:.1f} % / {perf[(5,2)][1]:.1f} %** (both runs miss both limits) — DEF-06 | **NO** |",
     '\n**Conditions to move from HOLD to RELEASE:** (1) fix DEF-03 and DEF-06 (or accept PR-08 for single-user deployments and run on PostgreSQL), (2) re-run EC-1 and EC-3, (3) address SEC-03 (`react-router`) and SEC-01 (CSP) in the deployment, (4) re-run the full pipeline green.\n',
     '## 2. Results per testing activity (what was tested)\n| Activity | Result | Evidence |\n|---|---|---|',
     f"| Static analysis (SonarQube) | bugs {sonar.get('bugs')}, smells {sonar.get('code_smells')}, vulnerabilities {sonar.get('vulnerabilities')}, ratings A, duplication {sonar.get('duplicated_lines_density')} %, coverage {sonar.get('coverage')} % (whole module); V(G) of `validate_pk` hand = 6 (radon 6, Sonar 5: `elif` not counted) | `docs/STATIC_ANALYSIS.md` |",
     f"| White-box unit tests | {fl.get('unit', {}).get('passed', '?')} passed, {fl.get('unit', {}).get('xfailed', '?')} strict-xfail (defects); in-scope coverage statements {st_cov} % / branches {br_cov} % over 31 functions; complete MCC for 12 decisions, MC/DC sets, BR-2 32 rows | `docs/UNIT_TESTING.md`, `docs/MCC_MCDC.md`, `docs/COVERAGE_SCOPE.md` |",
     f"| Test-data generation | OpenAPI 3.0.3 contract (validated), generator with {gen_tests} tests, 223 cases, two constraint-change demos | `docs/TEST_DATA_GENERATION.md` |",
     f"| API / integration | {fl.get('api', {}).get('passed', '?')} passed, {fl.get('api', {}).get('xfailed', '?')} strict-xfail; API coverage criteria all 100 % (endpoint, operation, status codes, roles, inputs, content types, methods, response schemas, sequences) | `docs/API_TESTING.md`, `docs/API_COVERAGE.md` |",
     f"| Browser E2E (6 use cases, 30 flows) + usability | Playwright: {pw_stats.get('expected', '?')} as expected, {pw_stats.get('unexpected', '?')} unexpected, {pw_stats.get('flaky', 0)} flaky (flows annotated as expected failures expose the still-open defects) | `docs/USE_CASES.md`, `docs/USABILITY.md` |",
     '| Accessibility | Lighthouse accessibility 78 → 85 and SEO 75 → 83 on the fixed screen; image-alt and landmark-one-main resolved; remaining issues logged | `docs/ACCESSIBILITY.md` |',
     f"| Security | access matrix {sum(1 for x in am if x['ok'])}/{len(am)}; ZAP passive ({zmsg_n} messages): 1 Medium (no CSP), 4 Low; pip-audit 0/166; yarn audit 9 advisories (1 high build-time) | `docs/SECURITY.md` |",
     '| Performance and recovery | targets declared first; 1 vs 5 users × 2 runs; failure-and-recovery test with test double (rollback, retry, no duplicates) | `docs/PERFORMANCE.md` |',
     f"| Mutation | {mut['total']} mutants, raw {mut['score_raw']} %, adjusted **{mut_adj:.1f} %** (10 survivors proven equivalent, 16 killed by added tests over two rounds); 4 custom operators | `docs/MUTATION.md` |",
     '| CI quality gate | 8-job pipeline, branch protection, no escape hatches, fix PR red→green, blocked PR | `docs/CI_QUALITY_GATE.md` |',
     f"| Requirements coverage | tested {req_tested}/{req_total}, verified passing {req_ver}/{req_total} | `docs/TRACEABILITY.md` |",
     '\n## 3. Tested / not tested (scope and residual gaps)\n| Tested | Not tested (and why) |\n|---|---|\n| Both workflows (add/remove), BR-1…BR-4, FR-01…FR-11, roles manager/viewer/anonymous, UI + API + model level, SQLite, Basic/session auth | transfer, count, serialization, merge, disassemble workflows (out of scope); purchase/sales/build orders; plugins; PostgreSQL/MySQL behaviour and true row locking (no server available — assumption A-4); OAuth2 token authentication; mobile/barcode UIs; i18n; ZAP **active** scanning (statement requires passive only); frontend unit tests |',
     '\n## 4. Open defects (GitHub Issues; triage in `docs/DEFECTS.md`)\n| ID | Issue | Title | Severity | Priority | Status |\n|---|---|---|---|---|---|']
for d in defects:
    o.append(f"| {d['id']} | [#{d['issue']}](https://github.com/{REPO}/issues/{d['issue']}) | {d['title']} | {d['severity']} | {d['priority']} | {d['status']} |")
o.append('\nPareto and root-cause analyses: `docs/DEFECTS.md`, `docs/RCA.md`. Reopen rate: 0 of 2 closed defects reopened (target ≤ 10 %).\n')
o.append('## 5. Residual risk per risk (register `docs/RISK_REGISTER.md`; re-assessed from evidence)\n| Risk | Initial L×I | Evidence-based residual L×I | Rationale | Linked defects |\n|---|---|---|---|---|')
RES = [('PR-01', 25, '1×5 = 5', 'over-removal rejected after the fix; limit BVA at 3 levels; CBR-1 mutants 2/2 killed', 'DEF-01 (fixed), DEF-03'),
       ('PR-02', 10, '1×5 = 5', f'access matrix {sum(1 for x in am if x["ok"])}/{len(am)}; no side effect on denied calls; SameSite/CSP hardening open', 'SEC-01, SEC-02'),
       ('PR-03', 12, '1×4 = 4', 'complete MCC 32/32 + MC/DC; CBR-2 mutants 5/5 killed', '—'),
       ('PR-04', 12, '4×3 = 12 (High)', 'zero accepted, overflow and malformed items still open', 'DEF-02, DEF-03, DEF-04'),
       ('PR-05', 8, '1×4 = 4', 'atomicity verified at unit, API and recovery level', '—'),
       ('PR-06', 12, '2×4 = 8 (Medium)', 'recovery test: retry after failure is safe; no idempotency key remains (W-03)', '—'),
       ('PR-07', 12, '2×4 = 8 (Medium)', 'history read back after success and rejection; W-01, W-06 weaknesses', '—'),
       ('PR-08', 9, '5×3 = 15 (High)', 'measured: 19.5 % failures at 5 users on SQLite', 'DEF-06'),
       ('PR-09', 8, '3×2 = 6 (Medium)', 'one screen fixed (78→85); other findings open', 'A11Y-01/02, UX-01, DEF-05'),
       ('PR-10', 12, '2×4 = 8 (Medium)', 'backend 0/166; frontend moderate advisories open', 'SEC-03'),
       ('PJ-01', 16, '1×4 = 4', 'all tools ran (SonarQube via zip, ZAP, k6, mutation, CI)', '—'),
       ('PJ-02', 15, '2×5 = 10 (High)', 'depends on the team preparing for the viva (`docs/VIVA_PREP.md`)', '—'),
       ('PJ-03', 12, '1×3 = 3', 'full mutation run took 25 min on 5 workers', '—')]
for r in RES: o.append('| ' + ' | '.join(str(x) for x in r) + ' |')
o.append('\n## 6. Pull requests and pipeline evidence (from the GitHub API)\n| PR | Title | Branch | State | Pipeline result |\n|---|---|---|---|---|')
for p in sorted(prs, key=lambda x: x['number']):
    roll = p.get('statusCheckRollup') or []
    res = ', '.join(f"{c.get('name')}: {c.get('conclusion') or c.get('status')}" for c in roll if c.get('name')) or '—'
    o.append(f"| [#{p['number']}]({p['url']}) | {p['title']} | `{p['headRefName']}` | {p['state']}{' (merged)' if p.get('mergedAt') else ''} | {res} |")
o.append('\n| Run | Event | Branch | Conclusion | Link |\n|---|---|---|---|---|')
for r in runs[:12]:
    o.append(f"| {r['databaseId']} | {r['event']} | `{r['headBranch']}` | {r['conclusion'] or r['status']} | {r['url']} |")
o.append('\n## 7. Deviations from the plan and honest limitations\n- SonarQube ran from the zip distribution (no Docker daemon on the machine; JDK 21, data on tmpfs); in CI it runs as a service container.\n- mutmut 3.8.1 ran (after two set-up problems of ours were fixed: newline-separated `setup.cfg` lists and a migrated database): 652 mutants; our own AST runner adds the four custom business-rule operators that mutmut does not offer (`docs/MUTATION.md`).\n- Database: SQLite (no PostgreSQL available): concurrency results are specific to it (assumption A-4).\n- Open defects other than DEF-01 were **logged and analysed but not fixed** (the statement requires one documented fix); this is the reason for HOLD.\n- Effort: agent hours are logged; **human review hours are recorded as estimates (32.0 h) that the members confirm** (`docs/EFFORT_NOTE.md`); commits are authored by the repository owner account — each member must commit their own work before submission (statement §6).\n')
open(os.path.join(R, 'docs/COMPLETION_REPORT.md'), 'w').write('\n'.join(o))

# ---------------------------------------------------------------- weekly progress report
rows = list(csv.DictReader(open(os.path.join(R, 'docs/EFFORT_LOG.csv'))))
tot_agent = sum(float(r['agent_hours']) for r in rows)
tot_human = sum(float(r['human_review_hours'] or 0) for r in rows)
w = ['# WEEKLY PROGRESS REPORT 2 of 2 — corrective actions and closure (2026-11-16 22:17 … 2026-11-17) against the plan (`docs/TEST_PLAN.md` v0.3)\n',
     'Continues `reports/weekly/week-1.md` (checkpoint 2026-11-16 21:48). Same note: the two reports are the two checkpoints of the real commit timeline.\n',
     '## 1. Progress against the plan\n| Planned item (from report 1 §5) | Actual (commit/PR time) | Status | Control action |\n|---|---|---|---|',
     '| Fix DEF-01 with a red → green pipeline | PR #13: tests-only 22:17 (red), fix 22:28 (red on a depleted-item test), corrected 22:35 (green), merged 22:57 | **done** | the pipeline caught my own over-reach (removal from a depleted item); fixed before merge |',
     '| One blocked pull request | PR #14 (BR-2 violation, run 43916978299) and PR #16 (killing tests removed, run 43933840489) | **done** | PR #16 passed a 90 % mutation gate at 90.4 % → gate raised to 95 % and the PR re-blocked (94.3 %) |',
     '| Fix the accessibility finding | PR #15, merged 11-17 01:23 after a green run | **done** | first version (`alt=""`) introduced an axe rule; corrected to use the aria-label; Lighthouse 78 → 85 |',
     '| Re-run mutation on the final code | 11-16 23:54: 248 mutants, 238 killed, 10 equivalents | **done** | 7 more killing tests; equivalents keyed by function + mutation + original code |',
     '| E2E in traceability | 11-17 01:38 (`tools/gen_traceability.py` reads the Playwright report) | **done** | — |',
     '| Final review round | 4 independent graders 11-17 | **done** | contradictions between documents reconciled (test counts, access matrix 20/20, mutation figures) |',
     '| Complete MCC for all four business rules | BR-4 added 11-17 08:04 | **done** | 13 decisions now covered |',
     '| Final PDF and zip | 11-17 08:04 | **done** | section B; human review hours estimated and recorded |',
     '\n## 2. GQM metrics now (definitions and targets: `docs/GQM.md`)\n| Goal | Metric | Value | Target | Reading |\n|---|---|---|---|---|',
     f"| G1 Find defects effectively | Defect density = functional defects (DEF-01…06) ÷ KLOC (module ncloc {sonar.get('ncloc')}) | {len([d for d in defects if d['id'].startswith('DEF')])} ÷ 5.114 = **{len([d for d in defects if d['id'].startswith('DEF')]) / 5.114:.2f}/KLOC** (all 12 findings: {len(defects) / 5.114:.2f}) | reported; > 1.0 triggers extra exploratory testing | unchanged: no new functional defect was found after report 1, so detection has saturated for this scope |",
     f"| G2 Cover requirements | Requirements coverage | tested **{req_tested}/{req_total}**, verified passing {req_ver}/{req_total} | 100 % tested | FR-07's over-removal rule is now passing (DEF-01 fixed); FR-03b stays unverified until DEF-02 is fixed |",
     '| G3 Healthy defect process | Reopen rate = reopened ÷ closed | 0 ÷ 2 = **0 %** (DEF-01, A11Y-01 closed) | ≤ 10 % | met, on a small sample |',
     f"| G4 Effective tests | Mutation score (adjusted) | **{mut_adj:.1f} %** (raw {mut['score_raw']} %) | ≥ 85 % (CI gate 95 %) | met; the gate itself was tightened after PR #16 |",
     '\n## 3. Control actions taken in this period\n- Mutation gate 85 → 90 → **95 %** (evidence: PR #16 run 43927877708 passed at 90.4 %, run 43933840489 blocked at 94.3 %).\n- Merge of PR #15 by admin bypass was not used; the branch was updated and the pipeline re-run to green instead (strict branch protection).\n- Keyboard test made independent of the focus-trap start state after it failed in CI only (run 43931016096).\n- Open Critical/High at the end: DEF-03, DEF-06 → release decision stays **HOLD** (`docs/COMPLETION_REPORT.md`).\n',
     f"## 4. Effort (estimate vs actual, `docs/EFFORT_LOG.csv`)\nAgent hours logged for the whole project: **{tot_agent:.2f} h** against a three-point estimate of 70.0 h (the estimate assumed human effort; human review hours are estimated at 32.0 h in `docs/EFFORT_NOTE.md`). The corrective work of this period (review rounds, PR fixes, final package) is part of the rows \"CI quality gate + PRs\", \"Defects, RCA, reports\" and \"Final PDF + package\".\n",
     '## 5. Plan for the next period (after submission)\nFix DEF-02 and DEF-04 (small validation changes), then DEF-03 (representable total) and DEF-06 (move to a database with row locks); rerun the k6 test against EC-3.\n']
os.makedirs(os.path.join(R, 'reports/weekly'), exist_ok=True)
open(os.path.join(R, 'reports/weekly/week-2.md'), 'w').write('\n'.join(w))
print('wrote docs/COMPLETION_REPORT.md and reports/weekly/week-2.md')
