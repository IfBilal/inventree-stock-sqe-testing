# AI-use record (SE3002 §7)
Tool: Claude Code (Anthropic, model Claude Sonnet 5.5) driven by the team. The instructor has permitted AI use. Every output is checked against real tool runs; prompts are kept in `docs/prompts/`.

| # | Date | Phase | Purpose | AI output | What was checked / changed |
|---|---|---|---|---|---|
| 1 | 2026-11-16 | Setup | Pick a repository that satisfies the project statement | Suggested `validators` (a library), then corrected to InvenTree after reading the PDF | Verified licence/activity/stack via GitHub API; rejected `validators` for lacking UI/API/DB/roles |
| 2 | 2026-11-16 | Plan | Extract requirements and draft master plan | `docs/REQUIREMENTS.md`, `docs/PLAN.md` | Re-read against the PDF pages 1-7 |
| 3 | 2026-11-16 | 0 | Environment, seed, reset scripts | `scripts/*`, `scripts/seed_data.py` | Ran each script; verified roles (manager 201, viewer 403) and deterministic reset by mutate → reset → compare |
| 4 | 2026-11-16 | 1 | Workflows, rules, test basis, use cases | `docs/TEST_BASIS.md`, `docs/USE_CASES.md` | Source read (`stock/serializers.py`, `stock/models.py`); observed over-removal behaviour on the running system (201, item deleted) |
