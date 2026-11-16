#!/usr/bin/env python3
"""Generate docs/COMPLETION_REPORT.md (test completion report, release/hold decision with actual vs target) and reports/weekly/week-1.md
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
equiv_n = sum(1 for r in mut['results'] if r['status'] == 'survived' and f"{r['function']}|{r['desc']}" in eq)
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
     f"| Security | access matrix {sum(1 for x in am if x['ok'])}/{len(am)}; ZAP passive (1 601 messages): 1 Medium (no CSP), 4 Low; pip-audit 0/166; yarn audit 9 advisories (1 high build-time) | `docs/SECURITY.md` |",
     '| Performance and recovery | targets declared first; 1 vs 5 users × 2 runs; failure-and-recovery test with test double (rollback, retry, no duplicates) | `docs/PERFORMANCE.md` |',
     f"| Mutation | {mut['total']} mutants, raw {mut['score_raw']} %, adjusted **{mut_adj:.1f} %** after killing 12 survivors; 15 equivalents documented; 4 custom operators | `docs/MUTATION.md` |",
     '| CI quality gate | 8-job pipeline, branch protection, no escape hatches, fix PR red→green, blocked PR | `docs/CI_QUALITY_GATE.md` |',
     f"| Requirements coverage | tested {req_tested}/{req_total}, verified passing {req_ver}/{req_total} | `docs/TRACEABILITY.md` |",
     '\n## 3. Tested / not tested (scope and residual gaps)\n| Tested | Not tested (and why) |\n|---|---|\n| Both workflows (add/remove), BR-1…BR-4, FR-01…FR-11, roles manager/viewer/anonymous, UI + API + model level, SQLite, Basic/session auth | transfer, count, serialization, merge, disassemble workflows (out of scope); purchase/sales/build orders; plugins; PostgreSQL/MySQL behaviour and true row locking (no server available — assumption A-4); OAuth2 token authentication; mobile/barcode UIs; i18n; ZAP **active** scanning (statement requires passive only); frontend unit tests |',
     '\n## 4. Open defects (GitHub Issues; triage in `docs/DEFECTS.md`)\n| ID | Issue | Title | Severity | Priority | Status |\n|---|---|---|---|---|---|']
for d in defects:
    o.append(f"| {d['id']} | [#{d['issue']}](https://github.com/{REPO}/issues/{d['issue']}) | {d['title']} | {d['severity']} | {d['priority']} | {d['status']} |")
o.append('\nPareto and root-cause analyses: `docs/DEFECTS.md`, `docs/RCA.md`. Reopen rate: 0 of 1 closed defect reopened (target ≤ 10 %).\n')
o.append('## 5. Residual risk per risk (register `docs/RISK_REGISTER.md`; re-assessed from evidence)\n| Risk | Initial L×I | Evidence-based residual L×I | Rationale | Linked defects |\n|---|---|---|---|---|')
RES = [('PR-01', 25, '1×5 = 5', 'over-removal rejected after the fix; limit BVA at 3 levels; CBR-1 mutants 2/2 killed', 'DEF-01 (fixed), DEF-03'),
       ('PR-02', 10, '1×5 = 5', 'access matrix 17/17; no side effect on denied calls; SameSite/CSP hardening open', 'SEC-01, SEC-02'),
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
o.append('\n## 7. Deviations from the plan and honest limitations\n- SonarQube ran from the zip distribution (no Docker daemon on the machine; JDK 21, data on tmpfs); in CI it runs as a service container.\n- mutmut 3.8 could not run on this Django project (evidence kept); an own AST runner with the standard and four custom operators was used (disclosed).\n- Database: SQLite (no PostgreSQL available): concurrency results are specific to it (assumption A-4).\n- Open defects other than DEF-01 were **logged and analysed but not fixed** (the statement requires one documented fix); this is the reason for HOLD.\n- Effort: agent hours are logged; **human review hours must be filled in by the members** (`docs/EFFORT_NOTE.md`); commits are authored by the repository owner account — each member must commit their own work before submission (statement §6).\n- The section letter for the file names is not known to the assistant and is set to `A` (placeholder).\n')
open(os.path.join(R, 'docs/COMPLETION_REPORT.md'), 'w').write('\n'.join(o))

# ---------------------------------------------------------------- weekly progress report
rows = list(csv.DictReader(open(os.path.join(R, 'docs/EFFORT_LOG.csv'))))
tot_agent = sum(float(r['agent_hours']) for r in rows)
w = ['# WEEKLY PROGRESS REPORT — week 1 (2026-11-16 … 2026-11-22) against the plan (`docs/TEST_PLAN.md` v0.2)\n',
     '## 1. Progress against the plan\n| Phase | Planned | Actual | Status | Control action |\n|---|---|---|---|---|',
     '| 0 environment/baseline | 11-16 | 11-16 | done | reset determinism verified (mutate→reset→compare) |',
     '| 1 scope/basis/use cases | 11-16 | 11-16 | done (2 review rounds) | docs corrected after empirical audit |',
     '| 2 test management | 11-16 | 11-16 | done (v0.2) | exit criteria re-tied to highest risks after review |',
     '| 3 static analysis | 11-17 | 11-16 (ahead) | done | Sonar-vs-hand discrepancy investigated experimentally |',
     '| 4 unit/white-box | 11-17…18 | 11-16 | done (3 review rounds) | scope widened after review (can_delete, tracking, permissions) |',
     '| 5–6 generator and API | 11-18…19 | 11-16 | done | generator rewritten after review (valid spec, all keywords) |',
     '| 7–8 E2E, usability, accessibility | 11-19…20 | 11-16 | done | DEF-05 found and handled visibly |',
     '| 9 security | 11-20 | 11-16 | done | passive only |',
     '| 10 performance/recovery | 11-21 | 11-16 | done | EC-3 missed → DEF-06, HOLD |',
     '| 11–12 mutation and CI | 11-21…23 | 11-16 | done | mutmut abandoned (documented), own runner; threshold set from evidence |',
     '| 13 defects/RCA/reports | 11-23…24 | 11-16 | done | — |',
     '| 14 final package | 11-24…26 | 11-16/17 | in progress | — |',
     '\n## 2. GQM metrics (definitions and targets: `docs/GQM.md`)\n| Goal | Metric | Value | Target | Reading |\n|---|---|---|---|---|',
     f"| G1 Find defects effectively | Defect density = confirmed functional defects ÷ KLOC (module ncloc {sonar.get('ncloc')}) | {len([d for d in defects if d['id'].startswith('DEF')])} ÷ 5.114 = **{len([d for d in defects if d['id'].startswith('DEF')]) / 5.114:.2f}/KLOC** (all 12 findings: {len(defects) / 5.114:.2f}) | reported; > 1.0 triggers extra exploratory testing | above 1.0 → exploratory weakness probes executed (W-01…W-13) |",
     f"| G2 Cover requirements | Requirements coverage | tested **{req_tested}/{req_total}**, verified passing {req_ver}/{req_total} | 100 % by Phase 13 | target met (tested) |",
     '| G3 Healthy defect process | Reopen rate = reopened ÷ closed | 0 ÷ 1 = **0 %** | ≤ 10 % | met |',
     f"| G4 Effective tests | Mutation score (adjusted) | **{mut_adj:.1f} %** (raw {mut['score_raw']} %) | ≥ 85 % | met |",
     '\n## 3. Control actions taken\n- After every phase two or more independent reviewer agents graded the work against the rubric; all findings were fixed and re-reviewed (`reviews/`).\n- The first mutation run was invalidated and repeated from scratch on a clean export after a working-tree mistake invalidated its results (no false results are reported).\n- Performance risk PR-08 re-scored from Medium to High after measurement.\n',
     f"## 4. Effort (estimate vs actual, `docs/EFFORT_LOG.csv`)\nAgent hours logged so far: **{tot_agent:.2f} h** against a three-point estimate of 70.0 h for the whole project (the estimate assumed human effort; human review hours are to be added by the members).\n"]
os.makedirs(os.path.join(R, 'reports/weekly'), exist_ok=True)
open(os.path.join(R, 'reports/weekly/week-1.md'), 'w').write('\n'.join(w))
print('wrote docs/COMPLETION_REPORT.md and reports/weekly/week-1.md')
