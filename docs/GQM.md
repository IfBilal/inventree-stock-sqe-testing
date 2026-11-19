# GQM metrics (Goal–Question–Metric) with targets
| Goal | Question | Metric (formula) | Target / threshold | Data source |
|---|---|---|---|---|
| G1 Find defects effectively | How dense are defects in the tested code? | Defect density = confirmed defects ÷ KLOC of the in-scope code. KLOC = SonarQube `ncloc` of the analysed Stock module files (5.165 KLOC in the final scan) | Reported, not minimised: ≥ 3 confirmed defects found is expected (DEF-01..03 already known); density > 1.0 defect/KLOC triggers extra exploratory testing | GitHub Issues (label `defect`), `evidence/sonar/project_measures.json` |
| G2 Cover all requirements | How much of the requirements is tested? | Requirements coverage = requirements with ≥ 1 passing test ÷ 16 (FR-01, FR-02, FR-03a/b, FR-04…FR-11, BR-1…BR-4) | 100 % by the end of Phase 13; < 60 % at Phase 6 triggers a control action | `docs/TRACEABILITY.md` |
| G3 Keep the defect process healthy | How often are fixed defects reopened? | Reopen rate = reopened defects ÷ closed defects | ≤ 10 %; > 10 % triggers root-cause review of the fix process | GitHub Issues timeline |
| G4 Keep tests effective | Do tests detect injected faults? | Mutation score = killed ÷ (total − equivalent) | ≥ 85 % on the business-rule module (CI gate justified in Phase 12) | `docs/MUTATION.md` (own runner; mutmut attempted) |
