# Coverage justification (EC-1: "0 unjustified uncovered lines")
**In-scope business logic** (functions listed in `docs/TEST_BASIS.md` §7 / `tools/scope_coverage.py` `SCOPE`): **statements 100 %, branches 100 %** — no uncovered line or branch (`docs/COVERAGE_SCOPE.md`, raw `evidence/coverage/coverage.json`).

| Item | Treatment |
|---|---|
| `StockAdjustmentItemSerializer.validate_quantity`, branch `quantity < 0` | Unreachable through the serializer (DRF `min_value=0` rejects negatives first, so this is dead code in practice). **Covered by a direct call** (`test_validate_quantity_negative_branch_directly`) so the branch is executed; recorded as a design weakness (redundant check). |
| Class bodies `StockAdjustView`, `StockAdd`, `StockRemove` (`api.py`) | Executed at import and exercised by `test_api_views.py`; they hold declarations only (no branches). |
| Rest of `stock/models.py`, `serializers.py`, `api.py` (merge, disassemble, serialization, transfer, count, locations, filters, generators …) | **Out of scope by design** (other workflows). Whole-module coverage is therefore lower (coverage.py 40 %, SonarQube 39.5 % line coverage, `evidence/coverage/coverage_report.txt`). |
