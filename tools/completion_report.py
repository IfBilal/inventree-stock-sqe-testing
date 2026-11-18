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
n_closed = sum(1 for d in defects if d['status'].startswith('Closed'))
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
pw = J('reports/playwright-report.json')
pw_stats = pw.get('stats', {})
am = J('evidence/security/access_matrix_results.json')
zmsg_n = J('evidence/security/zap_number_of_messages.json')['numberOfMessages']
perf, perf0 = {}, {}
for vu in (1, 5):
    for run in (1, 2):
        for store, folder in ((perf, 'token'), (perf0, 'baseline')):     # EC-3 uses the token-auth runs after the fix; the baseline is kept for the comparison
            d = J(f'reports/performance/{folder}/summary_{vu}vu_run{run}.json')['metrics']
            store[(vu, run)] = (d['http_req_duration{phase:hold}']['p(95)'], d['http_req_failed{phase:hold}'].get('value', d['http_req_failed{phase:hold}'].get('rate', 0)) * 100)
ec1_met = not crit_high_open
ec3_met = all(perf[(5, r)][0] <= 500 and perf[(5, r)][1] < 1 for r in (1, 2))
open_ids = ', '.join(d['id'] for d in defects if d['status'].startswith('Open') or d['status'].startswith('Accepted'))
decision = 'RELEASE' if (ec1_met and ec3_met) else 'HOLD'
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
     f"## 1. Decision\n> # **{decision}** — " + ('the build meets all three exit criteria.' if decision == 'RELEASE' else 'one exit criterion is still not met, so the build is **not recommended for release** yet.') + '\n',
     f"Reasons (evidence-based): EC-1 (functional) **{'met' if ec1_met else 'NOT met'}** (open Critical/High defects: {', '.join(d['id'] for d in crit_high_open) or 'none'}), EC-2 (security) **met** on the tested scope, EC-3 (performance) **{'met' if ec3_met else 'NOT met'}**: at 5 users the failure rate is {perf[(5,1)][1]:.1f} % / {perf[(5,2)][1]:.1f} % (was {perf0[(5,1)][1]:.1f} % / {perf0[(5,2)][1]:.1f} % before the DEF-06 fix) but p95 is {perf[(5,1)][0]:.0f} / {perf[(5,2)][0]:.0f} ms against the declared 500 ms. All five functional defects found in the add/remove workflows were fixed through pull requests that merged only after a green pipeline (DEF-01 PR #13; DEF-02, DEF-03, DEF-04 PR #17; DEF-06 PR #18), together with SEC-01, SEC-02 and the accessibility fix A11Y-01. Still open (none Critical/High): {open_ids}.\n",
     '### 1.1 Release criteria — actual versus target (the three exit criteria of the test plan, `docs/TEST_PLAN.md` §7)\n| ID | Category | Target | Actual (evidence) | Met? |\n|---|---|---|---|---|',
     f"| EC-1 | Functional (risks PR-01, PR-03, PR-06) | 100 % of own business-rule tests pass on the fixed build; **0 open Critical/High defects**; 0 unjustified uncovered lines (in-scope statements 100 %, branches 100 % with justification); all 6 basis paths and MC/DC pairs of `validate_pk` pass; retried request yields 0 duplicates | Tests pass on the fixed build (unit/API/E2E, §2). In-scope coverage statements **{st_cov} %**, branches **{br_cov} %** (1 unreachable branch justified: `docs/COVERAGE_JUSTIFICATION.md`). MCC rows 32/32, MC/DC set and 6 basis paths pass. Recovery tests: 0 duplicates. **Open Critical/High defects: {len(crit_high_open)} ({', '.join(d['id'] for d in crit_high_open) or 'none'})** | **{'YES' if ec1_met else 'NO'}** |",
     f"| EC-2 | Security (risks PR-02, PR-10) | all access-matrix decisions (≥ 4, ≥ 1 allowed, ≥ 1 denied) match; 0 unresolved High/Critical in the audited dependency set | **{sum(1 for x in am if x['ok'])}/{len(am)}** access decisions match (allowed and denied). Backend: 166 packages, 0 vulnerabilities. Frontend: 1 High advisory (`zod`, build tooling only, not in the served bundle) — dispositioned (accepted, SEC-03 / `docs/SECURITY.md` §4.2); 2 moderate `react-router` advisories in the shipped bundle (SEC-03, accepted risk: no patched 6.x release) | **YES** on the tested scope (with dispositions) |",
     f"| EC-3 | Performance (risk PR-08) | `POST /api/stock/remove/` at 5 users: p95 ≤ 500 ms and unexpected failures < 1 % | 1 user: p95 {perf[(1,1)][0]:.0f} / {perf[(1,2)][0]:.0f} ms, failures {perf[(1,1)][1]:.1f} % / {perf[(1,2)][1]:.1f} % (met). **5 users (token auth, after the DEF-06 fix): p95 {perf[(5,1)][0]:.0f} / {perf[(5,2)][0]:.0f} ms, failures {perf[(5,1)][1]:.1f} % / {perf[(5,2)][1]:.1f} %** — the failure criterion is met, the p95 criterion is not. Baseline before the fix: p95 {perf0[(5,1)][0]:.0f} / {perf0[(5,2)][0]:.0f} ms, failures {perf0[(5,1)][1]:.1f} % / {perf0[(5,2)][1]:.1f} %. Variants (Basic auth, gunicorn) in `docs/PERFORMANCE.md` §7 | **{'YES' if ec3_met else 'NO'}** |",
     '\n**Conditions to move from HOLD to RELEASE:** (1) bring the 5-user p95 under 500 ms (the write path costs about 100 ms of server time per request and SQLite serialises writers: reduce the per-request work or deploy on PostgreSQL and re-measure with `scripts/perf_run.sh`), or have the product owner approve a revised target with the evidence of `docs/PERFORMANCE.md`; (2) disposition of the remaining Medium/Low findings (DEF-05, SEC-03, A11Y-02, UX-01) in the release notes; (3) full pipeline green on the release commit.\n',
     '## 2. Results per testing activity (what was tested)\n| Activity | Result | Evidence |\n|---|---|---|',
     f"| Static analysis (SonarQube) | bugs {sonar.get('bugs')}, smells {sonar.get('code_smells')}, vulnerabilities {sonar.get('vulnerabilities')}, ratings A, duplication {sonar.get('duplicated_lines_density')} %, coverage {sonar.get('coverage')} % (whole module); V(G) of `validate_pk` hand = 6 (radon 6, Sonar 5: `elif` not counted) | `docs/STATIC_ANALYSIS.md` |",
     f"| White-box unit tests | {fl.get('unit', {}).get('passed', '?')} passed, {fl.get('unit', {}).get('xfailed', 0)} expected failures; in-scope coverage statements {st_cov} % / branches {br_cov} % over 33 functions; complete MCC for 13 decisions, MC/DC sets, BR-2 32 rows | `docs/UNIT_TESTING.md`, `docs/MCC_MCDC.md`, `docs/COVERAGE_SCOPE.md` |",
     f"| Test-data generation | OpenAPI 3.0.3 contract (validated), generator with {gen_tests} tests, 223 cases, two constraint-change demos | `docs/TEST_DATA_GENERATION.md` |",
     f"| API / integration | {fl.get('api', {}).get('passed', '?')} passed, {fl.get('api', {}).get('xfailed', '?')} strict-xfail (loose typing / audit-parameter weaknesses of upstream); API coverage criteria all 100 % (endpoint, operation, status codes, roles, inputs, content types, methods, response schemas, sequences) | `docs/API_TESTING.md`, `docs/API_COVERAGE.md` |",
     f"| Browser E2E (6 use cases, 30 flows) + usability | Playwright: {pw_stats.get('expected', '?')} tests as expected (30 use-case flows + 27 supporting tests: login set-up, access matrix, accessibility scans), {pw_stats.get('unexpected', '?')} unexpected, {pw_stats.get('flaky', 0)} flaky (no flow is an expected failure any more; DEF-05 shows as a visible annotation of the login set-up) | `docs/USE_CASES.md`, `docs/USABILITY.md` |",
     '| Accessibility | Lighthouse accessibility 78 → 85 and SEO 75 → 83 on the fixed screen; image-alt and landmark-one-main resolved; remaining issues logged | `docs/ACCESSIBILITY.md` |',
     f"| Security | access matrix {sum(1 for x in am if x['ok'])}/{len(am)}; ZAP passive ({zmsg_n} messages): 1 Medium (no CSP), 4 Low; pip-audit 0/166; yarn audit 9 advisories (1 high build-time) | `docs/SECURITY.md` |",
     '| Performance and recovery | targets declared first; 1 vs 5 users × 2 runs; failure-and-recovery test with test double (rollback, retry, no duplicates) | `docs/PERFORMANCE.md` |',
     f"| Mutation | {mut['total']} mutants, raw {mut['score_raw']} %, adjusted **{mut_adj:.1f} %** (the survivors are proven equivalent, the others were killed by added tests over two rounds); 4 custom operators | `docs/MUTATION.md` |",
     '| CI quality gate | 8-job pipeline, branch protection, no escape hatches, fix PR red→green, blocked PR | `docs/CI_QUALITY_GATE.md` |',
     f"| Requirements coverage | tested {req_tested}/{req_total}, verified passing {req_ver}/{req_total} | `docs/TRACEABILITY.md` |",
     '\n## 3. Tested / not tested (scope and residual gaps)\n| Tested | Not tested (and why) |\n|---|---|\n| Both workflows (add/remove), BR-1…BR-4, FR-01…FR-11, roles manager/viewer/anonymous, UI + API + model level, SQLite, Basic/session auth | transfer, count, serialization, merge, disassemble workflows (out of scope); purchase/sales/build orders; plugins; PostgreSQL/MySQL behaviour and true row locking (no server available — assumption A-4); OAuth2 token authentication; mobile/barcode UIs; i18n; ZAP **active** scanning (statement requires passive only); frontend unit tests |',
     '\n## 4. Defects: status of all 12 findings (GitHub Issues; triage in `docs/DEFECTS.md`)\n| ID | Issue | Title | Severity | Priority | Status |\n|---|---|---|---|---|---|']
for d in defects:
    o.append(f"| {d['id']} | [#{d['issue']}](https://github.com/{REPO}/issues/{d['issue']}) | {d['title']} | {d['severity']} | {d['priority']} | {d['status']} |")
o.append(f'\nPareto and root-cause analyses: `docs/DEFECTS.md`, `docs/RCA.md`. Reopen rate: 0 of {n_closed} closed defects reopened (target ≤ 10 %); SEC-03 was closed as an accepted risk, not fixed.\n')
o.append('## 5. Residual risk per risk (register `docs/RISK_REGISTER.md`; re-assessed from evidence)\n| Risk | Initial L×I | Evidence-based residual L×I | Rationale | Linked defects |\n|---|---|---|---|---|')
RES = [('PR-01', 25, '1×5 = 5', 'over-removal rejected after the fix; limit BVA at 3 levels; CBR-1 mutants 2/2 killed', 'DEF-01 (fixed), DEF-03'),
       ('PR-02', 10, '1×5 = 5', f'access matrix {sum(1 for x in am if x["ok"])}/{len(am)}; no side effect on denied calls; CSP header and SameSite=Lax added (PR #18)', 'SEC-01, SEC-02 (fixed)'),
       ('PR-03', 12, '1×4 = 4', 'complete MCC 32/32 + MC/DC; CBR-2 mutants 5/5 killed', '—'),
       ('PR-04', 12, '1×3 = 3', 'zero, unrepresentable totals and malformed items are rejected (PR #17); 3-point BVA at API level', 'DEF-02, DEF-03, DEF-04 (fixed)'),
       ('PR-05', 8, '1×4 = 4', 'atomicity verified at unit, API and recovery level', '—'),
       ('PR-06', 12, '2×4 = 8 (Medium)', 'recovery test: retry after failure is safe; no idempotency key remains (W-03)', '—'),
       ('PR-07', 12, '2×4 = 8 (Medium)', 'history read back after success and rejection; W-01, W-06 weaknesses', '—'),
       ('PR-08', 9, '3×3 = 9 (Medium)', 'failures 19.5 % → 0 % at 5 users after the DEF-06 fix; p95 545–556 ms still above the 500 ms limit', 'DEF-06 (fixed)'),
       ('PR-09', 8, '3×2 = 6 (Medium)', 'one screen fixed (78→85); other findings open', 'A11Y-01/02, UX-01, DEF-05'),
       ('PR-10', 12, '2×4 = 8 (Medium)', 'backend 0/166; frontend advisories dispositioned (react-router has no patched 6.x release; SEC-03 accepted)', 'SEC-03 (accepted)'),
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
for r in [x for x in runs if x.get('status') == 'completed' and x.get('conclusion') in ('success', 'failure')][:12]:
    o.append(f"| {r['databaseId']} | {r['event']} | `{r['headBranch']}` | {r['conclusion'] or r['status']} | {r['url']} |")
o.append('\n## 7. Deviations from the plan and honest limitations\n- SonarQube ran from the zip distribution (no Docker daemon on the machine; JDK 21, data on tmpfs); in CI it runs as a service container.\n- mutmut 3.8.1 ran (after two set-up problems of ours were fixed: newline-separated `setup.cfg` lists and a migrated database): 652 mutants; our own AST runner adds the four custom business-rule operators that mutmut does not offer (`docs/MUTATION.md`).\n- Database: SQLite (no PostgreSQL available): concurrency results are specific to it (assumption A-4).\n- Eight of the twelve findings were fixed through pull requests (DEF-01, 02, 03, 04, 06, SEC-01, SEC-02, A11Y-01); SEC-03 is an accepted risk and DEF-05, A11Y-02, UX-01 are open (Medium/Low, deferred). The only reason for HOLD is EC-3 (5-user p95).\n- Effort: agent hours are logged; **human review hours are recorded as estimates (32.0 h) that the members confirm** (`docs/EFFORT_NOTE.md`); commits are authored by the repository owner account — each member must commit their own work before submission (statement §6).\n')
open(os.path.join(R, 'docs/COMPLETION_REPORT.md'), 'w').write('\n'.join(o))

# ---------------------------------------------------------------- weekly progress report
rows = list(csv.DictReader(open(os.path.join(R, 'docs/EFFORT_LOG.csv'))))
tot_agent = sum(float(r['agent_hours']) for r in rows)
tot_human = sum(float(r['human_review_hours'] or 0) for r in rows)
w = ['# WEEKLY PROGRESS REPORT 2 of 2 — corrective actions and closure (2026-11-16 22:17 … 2026-11-18) against the plan (`docs/TEST_PLAN.md` v0.3)\n',
     'Continues `reports/weekly/week-1.md` (checkpoint 2026-11-16 21:48). Same note: the two reports are the two checkpoints of the real commit timeline.\n',
     '## 1. Progress against the plan\n| Planned item (from report 1 §5) | Actual (commit/PR time) | Status | Control action |\n|---|---|---|---|',
     '| Fix DEF-01 with a red → green pipeline | PR #13: tests-only 22:17 (red), fix 22:28 (red on a depleted-item test), corrected 22:35 (green), merged 22:57 | **done** | the pipeline caught my own over-reach (removal from a depleted item); fixed before merge |',
     '| One blocked pull request | PR #14 (BR-2 violation, run 43916978299) and PR #16 (killing tests removed, run 43933840489) | **done** | PR #16 passed a 90 % mutation gate at 90.4 % → gate raised to 95 % and the PR re-blocked (94.3 %) |',
     '| Fix the accessibility finding | PR #15, merged 11-17 01:23 after a green run | **done** | first version (`alt=""`) introduced an axe rule; corrected to use the aria-label; Lighthouse 78 → 85 |',
     '| Re-run mutation on the final code | 11-16 23:54: 248 mutants, 238 killed, 10 equivalents | **done** | 7 more killing tests; equivalents keyed by function + mutation + original code |',
     '| E2E in traceability | 11-17 01:38 (`tools/gen_traceability.py` reads the Playwright report) | **done** | — |',
     '| Final review round | 4 independent graders 11-17 | **done** | contradictions between documents reconciled (test counts, access matrix 20/20, mutation figures) |',
     '| Complete MCC for all four business rules | BR-4 added 11-17 08:04 | **done** | 13 decisions now covered |',
     '| Real mutmut run (the first attempt had failed because of our set-up) | 11-17/18: 652 mutants, all survivors classified | **done** | set-up fixed (newline lists, migrated DB); mutmut statuses went stale after tests were added, so every survivor was re-checked directly |',
     '| Fix the remaining functional defects (not planned in report 1 beyond DEF-01) | PR #17 DEF-02/03/04, PR #18 DEF-06 + SEC-01/02 (11-18), each merged after a green pipeline | **done** | DEF-03 (Critical) and DEF-06 (High) closed: EC-1 is met now |',
     '| Re-measure performance after DEF-06 | k6, 4 setups x 2 runs x 1/5 users (11-18) | **done** | failures 19.5 % -> 0 %; p95 545-556 ms is still above 500 ms: EC-3 stays NOT met; the Basic-auth artefact of the script was found and reported next to the token-auth result |',
     '| Re-run the custom-operator mutation analysis on the final code | 263 mutants, 254 killed, 9 equivalent (11-18) | **done** | a missing per-item overflow test was found and added |',
     '| Final PDF and zip | 11-18 | **done** | section B; human review hours estimated and recorded |',
     '\n## 2. GQM metrics now (definitions and targets: `docs/GQM.md`)\n| Goal | Metric | Value | Target | Reading |\n|---|---|---|---|---|',
     f"| G1 Find defects effectively | Defect density = functional defects (DEF-01…06) ÷ KLOC (module ncloc {sonar.get('ncloc')}) | {len([d for d in defects if d['id'].startswith('DEF')])} ÷ 5.114 = **{len([d for d in defects if d['id'].startswith('DEF')]) / 5.114:.2f}/KLOC** (all 12 findings: {len(defects) / 5.114:.2f}) | reported; > 1.0 triggers extra exploratory testing | unchanged: no new functional defect was found after report 1, so detection has saturated for this scope |",
     f"| G2 Cover requirements | Requirements coverage | tested **{req_tested}/{req_total}**, verified passing {req_ver}/{req_total} | 100 % tested | all requirements have a passing test since DEF-01 and DEF-02 are fixed |",
     f'| G3 Healthy defect process | Reopen rate = reopened ÷ closed | 0 ÷ {n_closed} = **0 %** ({n_closed} defects closed, none reopened) | ≤ 10 % | met |',
     f"| G4 Effective tests | Mutation score (adjusted) | **{mut_adj:.1f} %** (raw {mut['score_raw']} %) | ≥ 85 % (CI gate 95 %) | met; the gate itself was tightened after PR #16 |",
     '\n## 3. Control actions taken in this period\n- Mutation gate 85 → 90 → **95 %** (evidence: PR #16 run 43927877708 passed at 90.4 %, run 43933840489 blocked at 94.3 %).\n- Merge of PR #15 by admin bypass was not used; the branch was updated and the pipeline re-run to green instead (strict branch protection).\n- Keyboard test made independent of the focus-trap start state after it failed in CI only (run 43931016096).\n- No Critical/High defect is open at the end; the release decision stays **HOLD** only because EC-3 (5-user p95) is not met (`docs/COMPLETION_REPORT.md`).\n',
     f"## 4. Effort (estimate vs actual, `docs/EFFORT_LOG.csv`)\nAgent hours logged for the whole project: **{tot_agent:.2f} h** against a three-point estimate of 70.0 h (the estimate assumed human effort; human review hours are estimated at 32.0 h in `docs/EFFORT_NOTE.md`). The corrective work of this period (review rounds, PR fixes, final package) is part of the rows \"CI quality gate + PRs\", \"Defects, RCA, reports\" and \"Final PDF + package\".\n",
     '## 5. Plan for the next period (after submission)\nReduce the per-request cost of the write path or move to PostgreSQL and re-run the k6 protocol (EC-3); migrate to react-router 7 (SEC-03); keyboard Enter-to-submit and contrast fixes (UX-01, A11Y-02); investigate the first-login failure (DEF-05).\n']
# ---------------------------------------------------------------- closing section of the PDF: the decision again (actual vs target) + evidence links
dec = [l for l in o if l.startswith('### 1.1') or l.startswith('| ID |') or l.startswith('|---|---|---|---|---|') or l.startswith('| EC-')]
fd = ['# FINAL RELEASE / HOLD DECISION AND EVIDENCE LINKS\n',
      f'## Decision: **{decision}**\n',
      'The three exit criteria of the test plan (`docs/TEST_PLAN.md` §7), actual versus target (the PDF ends with the decision, as the project statement requires):\n',
      '| ID | Category | Target | Actual (evidence) | Met? |', '|---|---|---|---|---|']
fd += [l for l in o if l.startswith('| EC-')]
fd += ['\n## Evidence links (repository https://github.com/' + REPO + ')',
       '| What | Where |', '|---|---|',
       '| Source, tests, tools, scripts | `tests/team/`, `tools/`, `scripts/`, `.github/workflows/quality-gate.yml` |',
       '| Raw evidence per phase | `evidence/` (sonar, coverage, generator, api, traceability, a11y, security, mutation, ci), `reports/performance/`, `reports/playwright-report.json` |',
       '| Defects (GitHub Issues) | https://github.com/' + REPO + '/issues (12 issues, labels for severity, priority, status, triage); log in `docs/DEFECTS.md` |',
       '| Pull requests | #13 (DEF-01, red to green), #14 and #16 (blocked by the pipeline), #15 (accessibility), #17 (DEF-02/03/04), #18 (DEF-06, SEC-01/02) — https://github.com/' + REPO + '/pulls?q=is%3Apr |',
       '| Pipeline runs | https://github.com/' + REPO + '/actions (table in `docs/CI_QUALITY_GATE.md` and §6 of the completion report) |',
       '| Traceability matrix | `docs/TRACEABILITY.md` (generated from the test results) |',
       '| Weekly reports | `reports/weekly/week-1.md`, `reports/weekly/week-2.md` |',
       '| Review log of the independent graders | `reviews/README.md` |',
       '| AI-use record and effort | `docs/AI_USE_RECORD.md`, `docs/EFFORT_LOG.csv`, `docs/EFFORT_NOTE.md` |']
open(os.path.join(R, 'docs/FINAL_DECISION.md'), 'w').write('\n'.join(fd) + '\n')
os.makedirs(os.path.join(R, 'reports/weekly'), exist_ok=True)
open(os.path.join(R, 'reports/weekly/week-2.md'), 'w').write('\n'.join(w))
print('wrote docs/COMPLETION_REPORT.md and reports/weekly/week-2.md')
