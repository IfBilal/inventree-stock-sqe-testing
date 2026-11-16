# GQM metrics (Goal–Question–Metric)
| Goal | Question | Metric (formula) | Data source |
|---|---|---|---|
| G1 Find defects in stock adjustment effectively | How dense are defects in the tested code? | Defect density = confirmed defects / KLOC of in-scope code (`stock/serializers.py`+`models.py`+`api.py` functions) | GitHub Issues (label `defect`), `cloc`/coverage line counts |
| G2 Cover all requirements | How much of the requirements is tested? | Requirements coverage = requirements with ≥ 1 passing test / total requirements (FR-01..FR-11, BR-1..BR-4) | `docs/TRACEABILITY.md` (generated) |
| G3 Keep the defect process healthy | How often are fixed defects reopened? | Reopen rate = reopened defects / closed defects | GitHub Issues timeline |
| G4 Keep tests effective | Do tests detect injected faults? | Mutation score = killed / (total − equivalent) | mutmut results |
