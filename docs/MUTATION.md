# MUTATION ANALYSIS (Phase 11)

## 1. Tool and scope
- **Scope:** the business-rule functions of `docs/TEST_BASIS.md` §7 (32 functions in `stock/serializers.py`, `stock/models.py`, `InvenTree/fields.py`, `InvenTree/permissions.py`) — exactly the set whose coverage is gated.
- **Tool:** `tools/mutate.py` — AST-based mutation runner of our own, executed in 5 isolated parallel copies of the backend; every mutant is judged by the **real unit suite** (`tests/team/unit`, `-x`, killed = first failing test). The repository and `upstream/` are never modified; the analyses ran on clean `git archive` exports.
- **mutmut was tried first** (`scripts/mutation_setup.sh`; config keys `source_paths`, `pytest_add_cli_args_test_selection`, `also_copy` (all top-level directories), `mutate_only_covered_lines`): its coverage-gathering child process exits with code 1 on this Django project although the identical pytest command passes (143 tests in the copy; `evidence/mutation/mutmut_attempt.log` holds the traceback; the child's own pytest output is not surfaced by mutmut 3.8). Cosmic Ray would need one full-suite run per whole-file mutant and was not attempted. **We state plainly that the statement's tool list names mutmut/Cosmic Ray; the custom runner implements the same standard operators plus our four custom ones** (disclosed in the AI-use record).
- **Standard operators:** ROR relational, LCR and/or, UOI remove `not`, CRP constants, RET boolean returns, AOR +/-, SDL statement deletion, NEG if-condition negation.
- **Custom operators from OUR business rules (≥ 2 required):** **CBR-1 LIMIT_CLAMP** `min()`↔`max()` (BR-1 removal limit), **CBR-2 REFERENCE_CHECK** flip `x is None` on sales_order/belongs_to/customer/consumed_by (BR-2 adjustability), **CBR-3 DEPLETE_RULE** `delete_on_deplete`/`can_delete()` replaced by constants (BR-3), **CBR-4 POSITIVE_GUARD** `quantity <= 0` ↔ `< 0` on quantity guards (BR-1/FR-03). A custom mutant replaces the identical standard (ROR) mutant so no mutation is counted twice.

## 2. Scores — two analyses
| Analysis | Mutants | Killed | Survived | Raw score |
|---|---|---|---|---|
| **First analysis** (code before PR #13) — before improving the tests | 244 | 217 | 27 | **88.9 %** |
| First analysis — after 9 killing tests (12 survivors killed, 15 equivalents) | 244 | 229 | 15 | 93.9 % |
| **Final analysis** (final code incl. the DEF-01 fix and the dedupe of CBR-4/ROR) — before the second test round | 248 | 234 | 14 | **94.4 %** |
| Final analysis — after 7 more killing tests (4 survivors killed, 10 equivalents) | 248 | 238 | 10 | 96.0 % |
| **Final, adjusted** (the 10 survivors proven equivalent are excluded) | 238 | 238 | 0 | **100.0 %** |

## 3. Results by operator (final analysis, before the second test round)
| Operator | Mutants | Killed | Survived | Note |
|---|---|---|---|---|
| AOR | 3 | 2 | 1 |  |
| CBR-1 | 2 | 2 | 0 | custom — limit clamp |
| CBR-2 | 5 | 5 | 0 | custom — reference conditions |
| CBR-3 | 3 | 3 | 0 | custom — deplete rule |
| CBR-4 | 8 | 5 | 3 | custom — positive guard (3 survivors are equivalent: redundant guards) |
| CRP | 26 | 22 | 4 |  |
| LCR | 15 | 13 | 2 |  |
| NEG | 42 | 42 | 0 |  |
| RET | 20 | 20 | 0 |  |
| ROR | 21 | 21 | 0 |  |
| SDL | 94 | 90 | 4 |  |
| UOI | 9 | 9 | 0 |  |

## 4. Results by function (final analysis, before the second test round)
| Function | Mutants | Killed | Survived |
|---|---|---|---|
| `ModelPermission._queryset` | 6 | 6 | 0 |
| `PrefetchedPrimaryKeyRelatedField.__init__` | 2 | 2 | 0 |
| `PrefetchedPrimaryKeyRelatedField.to_internal_value` | 7 | 7 | 0 |
| `RolePermission.has_permission` | 14 | 14 | 0 |
| `StockAddSerializer.save` | 14 | 12 | 2 |
| `StockAdjustView.get_serializer_context` | 2 | 1 | 1 |
| `StockAdjustmentItemSerializer.__init__` | 5 | 5 | 0 |
| `StockAdjustmentItemSerializer.validate_pk` | 14 | 12 | 2 |
| `StockAdjustmentItemSerializer.validate_quantity` | 7 | 7 | 0 |
| `StockAdjustmentSerializer.to_internal_value` | 4 | 4 | 0 |
| `StockAdjustmentSerializer.validate` | 6 | 5 | 1 |
| `StockItem._apply_model_reference_fields` | 5 | 5 | 0 |
| `StockItem._apply_optional_transfer_fields` | 4 | 4 | 0 |
| `StockItem._apply_status_change` | 10 | 10 | 0 |
| `StockItem._audit_deltas` | 1 | 1 | 0 |
| `StockItem._is_empty_tracking_event` | 6 | 6 | 0 |
| `StockItem._resolve_status_kwarg` | 1 | 1 | 0 |
| `StockItem._tracking_deltas` | 7 | 7 | 0 |
| `StockItem.add_stock` | 14 | 12 | 2 |
| `StockItem.can_delete` | 14 | 14 | 0 |
| `StockItem.delete` | 11 | 10 | 1 |
| `StockItem.is_in_stock` | 14 | 13 | 1 |
| `StockItem.lock_quantity` | 10 | 10 | 0 |
| `StockItem.save` | 14 | 14 | 0 |
| `StockItem.take_stock` | 14 | 13 | 1 |
| `StockItem.tracking_event` | 5 | 5 | 0 |
| `StockItem.updateQuantity` | 14 | 14 | 0 |
| `StockRemoveSerializer.save` | 14 | 12 | 2 |
| `StockRemoveSerializer.validate` | 9 | 8 | 1 |

## 5. Analysis of the surviving mutants (27 + 14 = 41 analysed; ≥ 15 required): equivalent / missing test / weak assertion
### 5.1 Final analysis (14 survivors)
| ID | Operator | Function (line) | Mutation | Classification | Action / argument | After the second test round |
|---|---|---|---|---|---|---|
| M010 | CRP | `StockAdjustmentItemSerializer.validate_pk` (L1839) | False -> True | **Equivalent** | `backup_value=False` of `get_global_setting`: it only applies when the setting is not defined, which cannot happen for `STOCK_ALLOW_OUT_OF_STOCK_TRANSFER` (a declared global setting with a default) — unobservable. (The `cache=False` constant of the same call IS observable and is killed by `test_validate_pk_does_not_use_a_cached_setting_value`.) | survives (equivalent) |
| M011 | CRP | `StockAdjustmentItemSerializer.validate_pk` (L1839) | False -> True | **Missing test (cache=False)** | a direct DB update of the setting exposes a stale cached read (`test_validate_pk_does_not_use_a_cached_setting_value`); the `backup_value` constant is equivalent | **killed** |
| M031 | SDL | `StockAdjustmentSerializer.validate` (L1940) | delete statement: super().validate(data) | **Equivalent** | The base `serializers.Serializer.validate` returns its argument unchanged and its return value is discarded: deleting the call has no effect. | survives (equivalent) |
| M044 | LCR | `StockAddSerializer.save` (L2032) | or -> and | **Equivalent** | Redundant guard: for quantity 0 (or negative) `add_stock` itself returns False (model-level guard), so skipping the item in `save()` is unobservable. | survives (equivalent) |
| M045 | CBR-4 | `StockAddSerializer.save` (L2032) | POSITIVE_GUARD quantity <= 0 boundary moved | **Equivalent** | Redundant guard (see above): the model-level `quantity <= 0` check returns False anyway. | survives (equivalent) |
| M051 | SDL | `StockRemoveSerializer.validate` (L2055) | delete statement: data = super().validate(data) | **Missing test** | base validation of the remove serializer: empty list rejected and error index follows the pk-sorted order (`test_remove_rejects_an_empty_items_list`, `test_remove_reports_the_error_index_of_the_pk_sorted_entry`) | **killed** |
| M067 | LCR | `StockRemoveSerializer.save` (L2100) | or -> and | **Equivalent** | Redundant guard: for quantity 0 `take_stock` itself returns False, so the serializer-level skip is unobservable. | survives (equivalent) |
| M068 | CBR-4 | `StockRemoveSerializer.save` (L2100) | POSITIVE_GUARD quantity <= 0 boundary moved | **Equivalent** | Redundant guard (see above): `take_stock(0)` returns False. | survives (equivalent) |
| M075 | CRP | `StockItem.is_in_stock` (L2317) | True -> False | **Weak assertion** | defaults test: each of the three checks is ON by default (`test_is_in_stock_defaults_check_status_quantity_and_production`) | **killed** |
| M123 | SDL | `StockItem.add_stock` (L3429) | delete statement: tracking_info['quantity'] = float(sel | **Equivalent** | The quantity delta is dropped from the stored audit data: the observed entry is `additional_data={'deltas': {'added': 2.5}}` and `changes={'quantity': ['10.00000','12.50000'], …}` (the quantity is recorded as a FIELD CHANGE, asserted by `test_add_records_history_with_deltas_and_notes`), so the value of `tracking_info['quantity']` is inert. | survives (equivalent) |
| M124 | AOR | `StockItem.add_stock` (L3429) | + -> - | **Equivalent** | Same statement: the arithmetic of the inert `tracking_info['quantity']` value (see above) is unobservable. | survives (equivalent) |
| M130 | CBR-4 | `StockItem.take_stock` (L3466) | POSITIVE_GUARD quantity <= 0 boundary moved | **Equivalent** | First `quantity <= 0` guard: the second guard after the `min()` clamp rejects the same input, so moving this boundary has no effect. | survives (equivalent) |
| M193 | CRP | `StockItem.delete` (L578) | False -> True | **Missing test (cache=False)** | same technique for `STOCK_ALLOW_DELETE_SERIALIZED` (`test_delete_does_not_use_a_cached_setting_value`) | **killed** |
| M219 | SDL | `StockAdjustView.get_serializer_context` (L240) | delete statement: context['request'] = self.request | **Equivalent** | DRF `GenericAPIView.get_serializer_context` already supplies `request`; the explicit assignment is redundant. | survives (equivalent) |

### 5.2 First analysis (27 survivors, code before PR #13)
| ID | Operator | Function | Mutation | Classification | Action | Result |
|---|---|---|---|---|---|---|
| M009 | CRP | `StockAdjustmentItemSerializer.validate_pk` | False -> True | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |
| M010 | CRP | `StockAdjustmentItemSerializer.validate_pk` | False -> True | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |
| M031 | NEG | `StockAdjustmentSerializer.to_internal_value` | negate if-condition | **Missing test** | query-count test: the pk prefetch performs one bulk query (`test_prefetch_loads_all_referenced_items_with_a_single_stock_query`) | killed |
| M032 | SDL | `StockAdjustmentSerializer.to_internal_value` | delete statement: self.context['_stockitems'] = {o | **Missing test** | query-count test: the pk prefetch performs one bulk query (`test_prefetch_loads_all_referenced_items_with_a_single_stock_query`) | killed |
| M033 | SDL | `StockAdjustmentSerializer.validate` | delete statement: super().validate(data) | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |
| M045 | LCR | `StockAddSerializer.save` | or -> and | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |
| M046 | CBR-4 | `StockAddSerializer.save` | POSITIVE_GUARD quantity <= 0 boundary moved | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |
| M047 | ROR | `StockAddSerializer.save` | <= -> < | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |
| M060 | LCR | `StockRemoveSerializer.save` | or -> and | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |
| M061 | CBR-4 | `StockRemoveSerializer.save` | POSITIVE_GUARD quantity <= 0 boundary moved | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |
| M062 | ROR | `StockRemoveSerializer.save` | <= -> < | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |
| M106 | SDL | `StockItem.updateQuantity` | delete statement: trigger_event(StockEvents.ITEM_Q | **Missing test** | event test: `trigger_event(ITEM_QUANTITY_UPDATED, id, quantity)` is called (`test_update_quantity_triggers_the_quantity_updated_event`) | killed |
| M120 | SDL | `StockItem.add_stock` | delete statement: tracking_info['quantity'] = floa | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |
| M126 | CBR-4 | `StockItem.take_stock` | POSITIVE_GUARD quantity <= 0 boundary moved | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |
| M127 | ROR | `StockItem.take_stock` | <= -> < | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |
| M149 | SDL | `StockItem._apply_status_change` | delete statement: deltas['status_logical'] = self. | **Weak assertion** | asserted the complete delta dict of the helper (`test_apply_status_change_fills_all_status_deltas`) | killed |
| M150 | SDL | `StockItem._apply_status_change` | delete statement: deltas['old_status'] = old_custo | **Weak assertion** | asserted the complete delta dict of the helper (`test_apply_status_change_fills_all_status_deltas`) | killed |
| M151 | SDL | `StockItem._apply_status_change` | delete statement: deltas['old_status_logical'] = o | **Weak assertion** | asserted the complete delta dict of the helper (`test_apply_status_change_fills_all_status_deltas`) | killed |
| M155 | SDL | `StockItem._apply_optional_transfer_fields` | delete statement: deltas[field] = kwargs[field] | **Weak assertion** | asserted the recorded deltas and applied values (`test_apply_optional_transfer_fields_records_deltas_and_applies_values`) | killed |
| M166 | CRP | `StockItem.can_delete` | True -> False | **Weak assertion** | the monkeypatch stubs record their arguments: only ACTIVE allocations are queried (`test_can_delete_queries_only_active_allocations`) | killed |
| M167 | CRP | `StockItem.can_delete` | True -> False | **Weak assertion** | the monkeypatch stubs record their arguments: only ACTIVE allocations are queried (`test_can_delete_queries_only_active_allocations`) | killed |
| M170 | SDL | `StockItem.save` | delete statement: self.validate_unique() | **Missing test** | tests for duplicate serial (`validate_unique`), item cannot belong to itself (`clean`), `serial_int` (`update_serial_number`) | killed |
| M171 | SDL | `StockItem.save` | delete statement: self.clean() | **Missing test** | tests for duplicate serial (`validate_unique`), item cannot belong to itself (`clean`), `serial_int` (`update_serial_number`) | killed |
| M172 | SDL | `StockItem.save` | delete statement: self.update_serial_number() | **Missing test** | tests for duplicate serial (`validate_unique`), item cannot belong to itself (`clean`), `serial_int` (`update_serial_number`) | killed |
| M179 | LCR | `StockItem.save` | and -> or | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |
| M189 | CRP | `StockItem.delete` | False -> True | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |
| M215 | SDL | `StockAdjustView.get_serializer_context` | delete statement: context['request'] = self.reques | **Equivalent** | redundant guard, inert audit value, infrastructure argument or base-class call (same arguments as 5.1) | equivalent |

## 6. Gate in CI
The `mutation` job runs the same runner on a deterministic sample (`--workers 3 --max-per-function 7`, all custom mutants kept) and `tools/mutation_gate.py` requires an **adjusted score ≥ 90 %**, where adjusted = killed ÷ (total − equivalents listed in `docs/mutation_equivalents.json`); the key is `function|mutation|original code` (line-independent but specific). Every surviving mutant that is not a documented equivalent counts against the score.
**CI-produced scores (sampled runs, `evidence/ci/`):** before the killing tests — 159 mutants, 140 killed, **88.1 %** (gate then 85 %, passed); after the first killing tests (PR #13 run 43920009616) — 166 mutants, 157 killed, 9 survivors of which 7 documented → **98.7 % adjusted** (gate 90 %, passed). The 90 % threshold is justified by these distributions: the pre-improvement suite scores 88.1 % (below), the improved suite 98.7 % (above), leaving ~9 points of tolerance for sampling variation and new code. **Pull request #16** removes the killing tests: the baseline still passes but the score falls below 90 % → the pipeline blocks it on the **mutation threshold itself** (see `docs/CI_QUALITY_GATE.md`).

## 7. Reproduce
`scripts/mutation_setup.sh` then `python tools/mutate.py --workers 5 --max-per-function 14` (≈ 25 min); `python tools/mutate.py --only stock/models.py::StockItem.take_stock` for one function; `python tools/mutate.py --rerun-survivors evidence/mutation/results_final_run.json` re-runs the survivors. Raw data: `evidence/mutation/` (`results_round1.json`, `results_round2.json` = first analysis; `results_final_run.json`, `results_final_round2.json`, `results.json` = final).

