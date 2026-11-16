# REQUIREMENTS EXTRACTION — SE3002 SQE Final Project (Fall 2026)

Source of truth: `docs/SQE_Final_Project Fall 2026.pdf` (7 pages). 120 marks. Groups of 2–3.
Team roll numbers: 24I-3166, 24I-3015, 24I-3106. Target system: InvenTree (https://github.com/inventree/InvenTree, MIT), Stock module.

Each requirement has an ID (R-xx) used by the plan, traceability matrix and final audit.

## §1 System and scope (5 marks, CLO3)
- R-01 Pick an open-source, web-based MIS on GitHub; run locally with **synthetic records**.
- R-02 Repo has: usable browser UI, HTTP API for selected workflows, persistent storage, testable source.
- R-03 Record upstream URL, licence, **exact commit hash**.
- R-04 Choose **two related workflows in ONE module**. Each: starting condition, user action, expected outcome.
- R-05 Identify **one record/value that one workflow changes and the other uses**.
- R-06 Register in the section tab of the shared Google Sheet **within 5 days of announcement**. (One repo per group per section; ERPNext banned; same repo across sections allowed but plagiarism-checked.)
- R-07 **≥ 8 functional requirements**, **≥ 3 per workflow**.
- R-08 **4 business rules** and **2 user roles with different permissions**. Rules must include: (a) a boundary/limit, (b) a decision with ≥ 2 Boolean conditions, (c) a rule governing a change of state.
- R-09 Expected behaviour from repo docs or **justified assumption recorded in the test basis**.
- R-10 Identify which **shared records** each workflow reads or changes.
- R-11 **Baseline saved in Git**; document commands for install, start, seed test data, reset between runs.
- R-12 Upstream tests earn no marks; own tests in a separate folder (e.g. `tests/team/`).

## §2 Plan and automate functional tests
### Static analysis (5 marks)
- R-13 Run **SonarQube**; report complexity, duplication, code smells, bugs, vulnerabilities, coverage, technical debt, ratings; **explain what each shows**.
- R-14 **Hand-calculate cyclomatic complexity** of ONE business-rule function from its CFG; compare with SonarQube.
### Test management (7 + 5 + 7 + 5 marks)
- R-15 Test plan: scope, approach by risk level, roles, environment, test data, schedule, entry/exit/suspension/resumption criteria, risks. **Keep updated.**
- R-16 **Three-point estimate** per area; compare with **actual effort** at end.
- R-17 Risk register: **≥ 8 product + ≥ 2 project risks**, likelihood × impact (1–5) on **5×5 matrix**. Risk level decides technique and depth.
- R-18 Exit criteria: **≥ 3**, measurable (functional, performance, usability or security); **≥ 2 tied to highest risks**.
- R-19 **Traceability matrix** with requirements coverage.
- R-20 Defects in **GitHub Issues** with severity, priority, status, triage decision. **RCA (5 Whys + fishbone) for ≥ 2 major defects** with corrective and preventive actions. **Pareto by category**.
- R-21 **Weekly progress report** vs plan, control actions, **GQM metrics** (defect density, requirements coverage, reopen rate).
- R-22 **Test completion report**: tested/not tested, deviations, open defects, residual risk per risk, **release or hold recommendation**.
### Test levels (16 + 10 + 3 + 6 marks)
- R-23 **Unit**: 100% statement AND branch coverage of ALL server-side business logic (justify any uncovered). **Critical module: complete MCC, then MC/DC pairs from MCC tables.** Cover all four business rules.
- R-24 **API/integration**: EP and **3-point BVA on every input**, using **generated data**. Meet **all API coverage criteria**. Include rule rejections, invalid transitions, repeated requests (**no duplicates**). **Read back shared records after success AND rejection**. Report endpoint weaknesses. Cross-workflow checks.
- R-25 **Browser E2E (use-case testing)**: **2 use cases per member**, from docs or written by team, each with **≥ 2 alternative and ≥ 2 exception flows**. Automate **every flow in Playwright**; assert result shown AND postconditions.
- R-26 Use case specification (3 marks): derived from requirements, preconditions, postconditions, complete alt/exception flows.
- R-27 Techniques applied wherever they fit: **EP** (every valid + invalid group, one invalid value per test); **BVA** (just below, exactly at, just above every limit); **decision tables** (every combination for rules with ≥ 2 conditions, test expected outcomes); **state transition** (every allowed transition + ≥ 1 disallowed from each state). Each executable case counted once within its level.
### Automated test data generation (7 marks)
- R-28 **OpenAPI spec** for the endpoints (or project's own if accurate).
- R-29 **Generator reads spec → EP classes + 3-point BVA values.** API tests MUST use its output.
- R-30 **Change two constraints, regenerate, show effect.** Expect updated spec in the viva.
### Mutation and CI (8 marks)
- R-31 Mutation tool on business-rule module; report score. **≥ 2 custom mutation operators** from business rules. **Analyse ≥ 15 surviving mutants** (equivalent / missing test / weak assertion); **kill killable ones**.
- R-32 **GitHub Actions on every PR**: SonarQube, all tests, mutation. **Block merge and deployment** below justified coverage/mutation/Sonar thresholds. **No escape hatches** (`continue-on-error`, `|| true`).
- R-33 **One documented fix via PR** (fails before, passes after) and **one PR the pipeline blocked**.
- Tools (R-34): pytest + coverage.py; SonarQube; mutmut or Cosmic Ray; OpenAPI + own generator; Lighthouse + axe-core/@axe-core/playwright; pytest+Requests; Playwright (Chromium) + GitHub Actions.

## §3 Usability and accessibility (5 marks)
- R-35 **Two Playwright tests, one per workflow**: open task screen, complete with test data, assert confirmation.
- R-36 In ONE test: **first submit a value the business rule rejects, verify error explains what to correct, correct it, verify success**.
- R-37 In ONE test: **keyboard navigation** — focus reaches required fields and submit button **in expected order**; keyboard can submit.
- R-38 **Lighthouse** (accessibility, best practices, SEO) on **each use case's key screen** (logged in) + **full axe-core scan** via @axe-core/playwright. Issue found by both counted once. Each issue: **element, user impact, proposed fix**.
- R-39 **Fix one screen** (in MIS or own HTML page), rerun both tools, **before/after comparison**.
- R-40 Submit scripts, Playwright report, Lighthouse + axe reports (before and after). The 2 browser tests may count toward use-case tests.

## §4 Defensive security (6 marks)
- R-41 Identify routes and data in both workflows. **Access matrix**: actions per test role. **Playwright verifies ≥ 4 access decisions across both roles, ≥ 1 allowed and ≥ 1 denied**. Record role, action, expected, observed, evidence.
- R-42 **OWASP ZAP passive mode** while the Playwright tests run both workflows. Review **≥ 2 security controls** (session cookie attributes, role checks…); corroborate with source/config.
- R-43 **Dependency audit** (OWASP Dependency-Check or pip-audit); record packages + versions checked. For each relevant observation: **component, evidence, likely impact, recommended correction**. Documented controls with no findings also earn credit.
- Safety: local copy, synthetic data, passive inspection only — no active attacks.

## §5 Performance and recovery (5 marks)
- R-44 Select ONE operation of either workflow. **Before testing**, set p95 limit and acceptable unexpected-failure % per workload; explain why limits suit the operation.
- R-45 **k6 OSS**: one script, **1 simulated user** then **≥ 5 simulated users**. **Each run twice**, **≥ 60 s per run after reaching target users**. Same build, machine, starting data. Report p95 (ms), requests/s, failure %. Compare with limits.
- R-46 **Automated failure-and-recovery test** for a state-changing operation (test double: dependency unavailable before write completes). Verify persisted state after failure, restore dependency, retry, assert final state **without duplicate records**.
- R-47 Submit scripts, raw output, environment details, interpretation vs targets.

## §6 Final package (rest of marks)
- R-48 One submission per group: **PDF report + zip of Git repo** (public GitHub link in report).
- R-49 Repo contains: upstream reference + baseline commit, reproducible setup and reset instructions, runnable scripts and test data, tool versions, CI config, the documented change and the blocked PR.
- R-50 PDF contains: scope, risk register, traceability table, results per testing activity, **area ownership**, **AI-use record**, evidence links; test management docs; **for each API, accessibility, security, performance finding: root cause, fix, risk, linked to risk register**; ends with **release or hold decision with actual vs target for each of the 3 release criteria**.
- R-51 File names: `Project_<Roll1>_<Roll2>_<Roll3>_<Section>.zip` and `.pdf` (e.g. `Project_23I-0001_23I-0002_23I-0003_A.zip`). Include `.git` folder.
- R-52 **Each member commits their own work**; commit history checked in viva.
- R-53 Free open-source tools only.
- R-54 Area ownership: (1) static analysis, white-box, mutation, CI; (2) API testing and data generation; (3) use cases, usability, accessibility, security, performance. Pairs split area 3. Test management shared.
- Viva (20 marks): each member reruns a test and explains assertions; live task = business-rule change or updated API spec → predict failing tests and pipeline gate, make the change, show result. Unexplained component → marks deducted.

## §7 AI use and plagiarism
- R-55 AI allowed only if every output checked and disclosed in **AI-use record** (tool, purpose, output, what checked/changed). **Keep prompts.**
- R-56 Prohibited: undisclosed AI, **fabricated/edited evidence** (reports, pipeline runs, screenshots), copying from other groups/upstream/online, sharing work.
- R-57 Penalty: zero for component, possibly whole project.

## Marking rubric (120)
| Component | Marks |
|---|---|
| System and scope | 5 |
| Static analysis and metrics | 5 |
| Test plan, estimation, traceability | 7 |
| Risk register and exit criteria | 5 |
| White-box unit testing | 16 |
| API and integration testing | 10 |
| Automated test data generation | 7 |
| Use case specification | 3 |
| Use case test automation | 6 |
| Mutation analysis and CI quality gate | 8 |
| Usability and accessibility | 5 |
| Defensive security | 6 |
| Performance and recovery | 5 |
| Defect management and RCA | 7 |
| Monitoring and test completion report | 5 |
| Viva, live task, AI-use record | 20 |

## Ambiguities → decisions (recorded as justified assumptions)
1. "100% statement and branch coverage of all server-side business logic": scope is the **stock adjustment business logic** of the two workflows (serializers/models/api functions that implement the selected rules), defined precisely in `docs/TEST_BASIS.md`; coverage measured per-file for that scope, uncovered lines justified.
2. "Weekly progress report": produced from real work logs per working week (dated honestly).
3. "Each member commits their own work": three git identities are configured; the maintainer must commit under the right author. Commit authorship must reflect real work by each member — see AI-use record.
