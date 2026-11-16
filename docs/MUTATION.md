# MUTATION ANALYSIS (Phase 11)

## 1. Tool and scope
- **Scope:** the business-rule functions of `docs/TEST_BASIS.md` §7 (31 functions in `stock/serializers.py`, `stock/models.py`, `InvenTree/fields.py`, `InvenTree/permissions.py`) — exactly the set whose coverage is gated.
- **Tool:** `tools/mutate.py` — AST-based mutation runner of our own, executed in 5 isolated parallel copies of the backend; each mutant is judged by the **real unit suite** (`tests/team/unit`, `-x`, killed = first failing test). The repository and `upstream/` are never modified; the analysis runs on a clean `git archive` export.
- **mutmut was tried first** (`scripts/mutation_setup.sh`, config keys `source_paths`, `pytest_add_cli_args_test_selection`, `also_copy`, `mutate_only_covered_lines`): its coverage-gathering child exits with code 1 on this Django project although the identical pytest command passes (`evidence/mutation/mutmut_attempt.log`). Cosmic Ray would need a full-suite run per whole-file mutant. We therefore implemented the same standard operators and our custom ones in our own runner (disclosed in the AI-use record).
- **Standard operators (mutmut/Cosmic-Ray style):** ROR relational, LCR and/or, UOI remove `not`, CRP constants, RET boolean returns, AOR +/-, SDL statement deletion, NEG if-condition negation.
- **Custom operators from OUR business rules (≥ 2 required):** **CBR-1 LIMIT_CLAMP** `min()`↔`max()` (BR-1 removal limit), **CBR-2 REFERENCE_CHECK** flip `x is None` on sales_order/belongs_to/customer/consumed_by (BR-2 adjustability), **CBR-3 DEPLETE_RULE** `delete_on_deplete`/`can_delete()` replaced by constants (BR-3), **CBR-4 POSITIVE_GUARD** `quantity <= 0` ↔ `< 0` (BR-1/FR-03).

## 2. Score
| Stage | Mutants | Killed | Survived | Score |
|---|---|---|---|---|
| Round 1 (before improving tests) | 244 | 217 | 27 | **88.9 %** |
| Round 2 (after 9 new killing tests) | 244 | 229 | 15 | 93.9 % raw |
| **Final, adjusted** (survivors proven equivalent excluded: 15) | 229 | 229 | 0 | **100.0 %** |

## 3. Results by operator (round 1)
| Operator | Mutants | Killed | Survived | Note |
|---|---|---|---|---|
| AOR | 1 | 1 | 0 |  |
| CBR-1 | 2 | 2 | 0 | custom — limit clamp |
| CBR-2 | 5 | 5 | 0 | custom — reference conditions |
| CBR-3 | 3 | 3 | 0 | custom — deplete rule |
| CBR-4 | 8 | 5 | 3 | custom — positive guard (3 survivors are equivalent: redundant guards) |
| CRP | 37 | 32 | 5 |  |
| LCR | 16 | 13 | 3 |  |
| NEG | 42 | 41 | 1 |  |
| RET | 13 | 13 | 0 |  |
| ROR | 26 | 23 | 3 |  |
| SDL | 83 | 71 | 12 |  |
| UOI | 8 | 8 | 0 |  |

## 4. Results by function (round 1)
| Function | Mutants | Killed | Survived |
|---|---|---|---|
| `ModelPermission._queryset` | 6 | 6 | 0 |
| `PrefetchedPrimaryKeyRelatedField.__init__` | 2 | 2 | 0 |
| `PrefetchedPrimaryKeyRelatedField.to_internal_value` | 7 | 7 | 0 |
| `RolePermission.has_permission` | 14 | 14 | 0 |
| `StockAddSerializer.save` | 14 | 11 | 3 |
| `StockAdjustView.get_serializer_context` | 2 | 1 | 1 |
| `StockAdjustmentItemSerializer.__init__` | 5 | 5 | 0 |
| `StockAdjustmentItemSerializer.validate_pk` | 14 | 12 | 2 |
| `StockAdjustmentItemSerializer.validate_quantity` | 9 | 9 | 0 |
| `StockAdjustmentSerializer.to_internal_value` | 4 | 2 | 2 |
| `StockAdjustmentSerializer.validate` | 6 | 5 | 1 |
| `StockItem._apply_model_reference_fields` | 5 | 5 | 0 |
| `StockItem._apply_optional_transfer_fields` | 4 | 3 | 1 |
| `StockItem._apply_status_change` | 10 | 7 | 3 |
| `StockItem._audit_deltas` | 1 | 1 | 0 |
| `StockItem._is_empty_tracking_event` | 6 | 6 | 0 |
| `StockItem._resolve_status_kwarg` | 1 | 1 | 0 |
| `StockItem._tracking_deltas` | 7 | 7 | 0 |
| `StockItem.add_stock` | 14 | 13 | 1 |
| `StockItem.can_delete` | 14 | 12 | 2 |
| `StockItem.delete` | 11 | 10 | 1 |
| `StockItem.is_in_stock` | 14 | 14 | 0 |
| `StockItem.lock_quantity` | 13 | 13 | 0 |
| `StockItem.save` | 14 | 10 | 4 |
| `StockItem.take_stock` | 14 | 12 | 2 |
| `StockItem.tracking_event` | 5 | 5 | 0 |
| `StockItem.updateQuantity` | 14 | 13 | 1 |
| `StockRemoveSerializer.save` | 14 | 11 | 3 |

## 5. Analysis of the 27 surviving mutants (≥ 15 required): equivalent / missing test / weak assertion
| ID | Operator | Function (line) | Mutation | Classification | Action | Result after round 2 |
|---|---|---|---|---|---|---|
| M009 | CRP | `StockAdjustmentItemSerializer.validate_pk` (L1839) | False -> True | **Equivalent** | `get_global_setting(..., backup_value=False, cache=False)`: `backup_value` only applies when the setting row is missing (never) and `cache` only changes caching of a setting read; no observable difference. | survives (equivalent) |
| M010 | CRP | `StockAdjustmentItemSerializer.validate_pk` (L1839) | False -> True | **Equivalent** | `get_global_setting(..., backup_value=False, cache=False)`: `backup_value` only applies when the setting row is missing (never) and `cache` only changes caching of a setting read; no observable difference. | survives (equivalent) |
| M031 | NEG | `StockAdjustmentSerializer.to_internal_value` (L1928) | negate if-condition | **Missing test** | query-count test: the pk prefetch performs one bulk query (`test_prefetch_loads_all_referenced_items_with_a_single_stock_query`) | **killed** |
| M032 | SDL | `StockAdjustmentSerializer.to_internal_value` (L1929) | delete statement: self.context['_stockitems'] = {obj.pk: obj | **Missing test** | query-count test: the pk prefetch performs one bulk query (`test_prefetch_loads_all_referenced_items_with_a_single_stock_query`) | **killed** |
| M033 | SDL | `StockAdjustmentSerializer.validate` (L1940) | delete statement: super().validate(data) | **Equivalent** | The base `Serializer.validate` returns its argument unchanged: deleting the call has no effect. | survives (equivalent) |
| M045 | LCR | `StockAddSerializer.save` (L2032) | or -> and | **Equivalent** | Redundant guard: for quantity 0 (or negative) `add_stock` itself returns False (model-level guard), so skipping the item in `save()` is unobservable. | survives (equivalent) |
| M046 | CBR-4 | `StockAddSerializer.save` (L2032) | POSITIVE_GUARD quantity <= 0 boundary moved | **Equivalent** | Redundant guard: for quantity 0 (or negative) `add_stock` itself returns False (model-level guard), so skipping the item in `save()` is unobservable. | survives (equivalent) |
| M047 | ROR | `StockAddSerializer.save` (L2032) | <= -> < | **Equivalent** | Redundant guard: for quantity 0 (or negative) `add_stock` itself returns False (model-level guard), so skipping the item in `save()` is unobservable. | survives (equivalent) |
| M060 | LCR | `StockRemoveSerializer.save` (L2067) | or -> and | **Equivalent** | Redundant guard: for quantity 0 `take_stock` itself returns False, so the serializer-level skip is unobservable. | survives (equivalent) |
| M061 | CBR-4 | `StockRemoveSerializer.save` (L2067) | POSITIVE_GUARD quantity <= 0 boundary moved | **Equivalent** | Redundant guard: for quantity 0 `take_stock` itself returns False, so the serializer-level skip is unobservable. | survives (equivalent) |
| M062 | ROR | `StockRemoveSerializer.save` (L2067) | <= -> < | **Equivalent** | Redundant guard: for quantity 0 `take_stock` itself returns False, so the serializer-level skip is unobservable. | survives (equivalent) |
| M106 | SDL | `StockItem.updateQuantity` (L3289) | delete statement: trigger_event(StockEvents.ITEM_QUANTITY_UP | **Missing test** | event test: `trigger_event(ITEM_QUANTITY_UPDATED, id, quantity)` is called (`test_update_quantity_triggers_the_quantity_updated_event`) | **killed** |
| M120 | SDL | `StockItem.add_stock` (L3429) | delete statement: tracking_info['quantity'] = float(self.qua | **Equivalent** | The quantity delta is dropped from `additional_data` (it is recorded as a field change, `changes['quantity']`, which the tests assert), so the value is inert. | survives (equivalent) |
| M126 | CBR-4 | `StockItem.take_stock` (L3466) | POSITIVE_GUARD quantity <= 0 boundary moved | **Equivalent** | First `quantity <= 0` guard: the second guard after the `min()` clamp rejects the same input, so moving this boundary has no effect. | survives (equivalent) |
| M127 | ROR | `StockItem.take_stock` (L3466) | <= -> < | **Equivalent** | First `quantity <= 0` guard: the second guard after the `min()` clamp rejects the same input, so moving this boundary has no effect. | survives (equivalent) |
| M149 | SDL | `StockItem._apply_status_change` (L3112) | delete statement: deltas['status_logical'] = self.status | **Weak assertion** | asserted the complete delta dict of the helper (`test_apply_status_change_fills_all_status_deltas`) | **killed** |
| M150 | SDL | `StockItem._apply_status_change` (L3113) | delete statement: deltas['old_status'] = old_custom_status i | **Weak assertion** | asserted the complete delta dict of the helper (`test_apply_status_change_fills_all_status_deltas`) | **killed** |
| M151 | SDL | `StockItem._apply_status_change` (L3116) | delete statement: deltas['old_status_logical'] = old_status_ | **Weak assertion** | asserted the complete delta dict of the helper (`test_apply_status_change_fills_all_status_deltas`) | **killed** |
| M155 | SDL | `StockItem._apply_optional_transfer_fields` (L3125) | delete statement: deltas[field] = kwargs[field] | **Weak assertion** | asserted the recorded deltas and applied values (`test_apply_optional_transfer_fields_records_deltas_and_applies_values`) | **killed** |
| M166 | CRP | `StockItem.can_delete` (L1881) | True -> False | **Weak assertion** | the monkeypatch stubs now record their arguments: only ACTIVE allocations are queried (`test_can_delete_queries_only_active_allocations`) | **killed** |
| M167 | CRP | `StockItem.can_delete` (L1884) | True -> False | **Weak assertion** | the monkeypatch stubs now record their arguments: only ACTIVE allocations are queried (`test_can_delete_queries_only_active_allocations`) | **killed** |
| M170 | SDL | `StockItem.save` (L529) | delete statement: self.validate_unique() | **Missing test** | tests for duplicate serial (`validate_unique`), item cannot belong to itself (`clean`), `serial_int` (`update_serial_number`) | **killed** |
| M171 | SDL | `StockItem.save` (L530) | delete statement: self.clean() | **Missing test** | tests for duplicate serial (`validate_unique`), item cannot belong to itself (`clean`), `serial_int` (`update_serial_number`) | **killed** |
| M172 | SDL | `StockItem.save` (L531) | delete statement: self.update_serial_number() | **Missing test** | tests for duplicate serial (`validate_unique`), item cannot belong to itself (`clean`), `serial_int` (`update_serial_number`) | **killed** |
| M179 | LCR | `StockItem.save` (L552) | and -> or | **Equivalent** | `(user or notes) and not has_pending_event`: with `or`, an extra `audit_event(...)` context is opened; the audit layer attaches it to the same entry, so the number and content of audit entries are identical (checked by `test_update_save_inside_a_pending_event_adds_exactly_one_audit_entry`). | survives (equivalent) |
| M189 | CRP | `StockItem.delete` (L578) | False -> True | **Equivalent** | `cache=False` argument of `get_global_setting` (caching of a setting read): no observable difference. | survives (equivalent) |
| M215 | SDL | `StockAdjustView.get_serializer_context` (L240) | delete statement: context['request'] = self.request | **Equivalent** | DRF `GenericAPIView.get_serializer_context` already supplies `request`; the explicit assignment is redundant. | survives (equivalent) |

## 6. Gate in CI
The `mutation` job runs the same runner on a deterministic sample (`--workers 3 --max-per-function 7`, all custom mutants kept) and `tools/mutation_gate.py` requires an **adjusted score ≥ 90 %**, where adjusted = killed ÷ (total − mutants listed in `docs/mutation_equivalents.json`). *Justification:* the final full-set score is 100 % adjusted and 93.9 % raw; round 1 (before the test improvements) scored 88.9 % raw, so 90 % separates the improved suite from the earlier one while leaving ~10 points of tolerance for the sample (fewer mutants per function) and for new, not-yet-killed mutants of future changes. Any surviving mutant that is not a documented equivalent counts against the score. See `docs/CI_QUALITY_GATE.md`.

## 7. Reproduce
`scripts/mutation_setup.sh` then `python tools/mutate.py --workers 5 --max-per-function 14` (≈ 25 min); `python tools/mutate.py --only stock/models.py::StockItem.take_stock` for one function; `python tools/mutate.py --rerun-survivors evidence/mutation/results_round1.json` re-runs the survivors. Raw data: `evidence/mutation/results_round1.json`, `results_round2.json`, `results.json`.

