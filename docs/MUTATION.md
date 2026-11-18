# MUTATION ANALYSIS (Phase 11)

## 1. Tool and scope
- **Scope:** the business-rule functions of `docs/TEST_BASIS.md` §7 (32 functions in `stock/serializers.py`, `stock/models.py`, `InvenTree/fields.py`, `InvenTree/permissions.py`) — exactly the set whose coverage is gated.
- **Tool:** `tools/mutate.py` — AST-based mutation runner of our own, executed in 5 isolated parallel copies of the backend; every mutant is judged by the **real unit suite** (`tests/team/unit`, `-x`, killed = first failing test). The repository and `upstream/` are never modified; the analyses ran on clean `git archive` exports.
- **mutmut 3.8.1 was run for real** (`scripts/mutmut_run.sh`, results in §2b). Our first attempt failed and we first wrongly reported mutmut as unusable: the cause was in OUR set-up, not in mutmut — (1) mutmut reads list options in `setup.cfg` one per line, so a comma-separated `also_copy` copied nothing, and (2) InvenTree calls `sys.exit(1)` at start-up on an un-migrated database, which mutmut surfaces only as "Child exited with code 1" (reproduced by running its coverage step in-process, `evidence/mutation/mutmut_attempt.log`). With a newline-separated config and a migrated database mutmut runs. Because mutmut offers no custom operators, our own AST runner (`tools/mutate.py`) additionally implements the four business-rule operators below; both are reported.
- **Standard operators:** ROR relational, LCR and/or, UOI remove `not`, CRP constants, RET boolean returns, AOR +/-, SDL statement deletion, NEG if-condition negation.
- **Custom operators from OUR business rules (≥ 2 required):** **CBR-1 LIMIT_CLAMP** `min()`↔`max()` (BR-1 removal limit), **CBR-2 REFERENCE_CHECK** flip `x is None` on sales_order/belongs_to/customer/consumed_by (BR-2 adjustability), **CBR-3 DEPLETE_RULE** `delete_on_deplete`/`can_delete()` replaced by constants (BR-3), **CBR-4 POSITIVE_GUARD** `quantity <= 0` ↔ `< 0` on quantity guards (BR-1/FR-03). A custom mutant replaces the identical standard (ROR) mutant so no mutation is counted twice.

## 2. Scores — two analyses
| Analysis | Mutants | Killed | Survived | Raw score |
|---|---|---|---|---|
| **First analysis** (code before PR #13) — before improving the tests | 244 | 217 | 27 | **88.9 %** |
| First analysis — after 9 killing tests (12 survivors killed, 15 equivalents) | 244 | 229 | 15 | 93.9 % |
| **Final analysis** (final code incl. the DEF-01..04 fixes and the dedupe of CBR-4/ROR) — before the second test round | 263 | 253 | 10 | **96.2 %** |
| Final analysis — after more killing tests (1 survivors killed, 9 equivalents) | 263 | 254 | 9 | 96.6 % |
| **Final, adjusted** (the 9 survivors proven equivalent are excluded) | 254 | 254 | 0 | **100.0 %** |

## 3. Results by operator (final analysis, before the second test round)
| Operator | Mutants | Killed | Survived | Note |
|---|---|---|---|---|
| AOR | 5 | 5 | 0 |  |
| CBR-1 | 2 | 2 | 0 | custom — limit clamp |
| CBR-2 | 5 | 5 | 0 | custom — reference conditions |
| CBR-3 | 3 | 3 | 0 | custom — deplete rule |
| CBR-4 | 8 | 5 | 3 | custom — positive guard (3 survivors are equivalent: redundant guards) |
| CRP | 27 | 25 | 2 |  |
| LCR | 19 | 17 | 2 |  |
| NEG | 46 | 46 | 0 |  |
| RET | 18 | 18 | 0 |  |
| ROR | 23 | 23 | 0 |  |
| SDL | 95 | 92 | 3 |  |
| UOI | 12 | 12 | 0 |  |

## 2b. mutmut results (the real tool, 3.8.1)
*The mutmut run was made on the code of commit `c9bb115`, i.e. before the fixes of DEF-02/03/04/06 (PRs #17, #18); the functions changed since then (`StockAddSerializer.validate`, the `items` declarations, `to_internal_value`) are covered by the custom-operator analysis above, which was repeated on the final code.*

**mutmut 3.x — real run on `stock/serializers.py` and `stock/models.py`: 652 mutants, 509 killed, 107 survived, 0 timed out, 36 without covering tests.**
Raw score (killed ÷ (killed + survived + timeout)): **82.6 %** over all functions of both files. In-scope functions only (the 32 functions of `docs/TEST_BASIS.md` §7): 416 killed, 46 survived → **90.0 %**.
Adjusted in-scope score (survivors proven equivalent excluded, justification per mutant below): **100.0 %** (46 of the in-scope survivors are equivalent; none is a missing test). Survivors outside the scope are display/allocation/plugin helpers and the status-field wrapper, which the add/remove workflows do not use. The 36 mutants 'without covering tests' are 12 with no test reaching them plus 24 `StockStatusCustomSerializer.__init__` mutants that hang the process (out of scope; the run was stopped there).

| Function | killed | survived |
|---|---|---|
| `StockAddSerializer.save` | 32 | 5 |
| `StockAdjustmentItemSerializer.__init__` | 15 | 3 |
| `StockAdjustmentItemSerializer.validate_pk` | 28 | 9 |
| `StockAdjustmentItemSerializer.validate_quantity` | 15 | 0 |
| `StockAdjustmentSerializer.to_internal_value` | 23 | 2 |
| `StockAdjustmentSerializer.validate` | 22 | 3 |
| `StockItem.__str__` (outside scope) | 2 | 1 |
| `StockItem._apply_model_reference_fields` | 9 | 1 |
| `StockItem._apply_optional_transfer_fields` | 8 | 0 |
| `StockItem._apply_status_change` | 18 | 2 |
| `StockItem._audit_deltas` | 1 | 0 |
| `StockItem._is_empty_tracking_event` | 6 | 0 |
| `StockItem._resolve_status_kwarg` | 11 | 0 |
| `StockItem._tracking_deltas` | 18 | 0 |
| `StockItem.add_test_result` (outside scope) | 0 | 0 |
| `StockItem.add_tracking_entry` (outside scope) | 0 | 0 |
| `StockItem.can_delete` | 13 | 0 |
| `StockItem.can_merge` (outside scope) | 0 | 0 |
| `StockItem.clean` (outside scope) | 38 | 1 |
| `StockItem.convert_serial_to_int` (outside scope) | 2 | 3 |
| `StockItem.delete` | 30 | 6 |
| `StockItem.get_installed_items` (outside scope) | 0 | 0 |
| `StockItem.get_next_serialized_item` (outside scope) | 0 | 0 |
| `StockItem.get_sales_order_allocations` (outside scope) | 3 | 11 |
| `StockItem.get_test_keys` (outside scope) | 0 | 0 |
| `StockItem.get_transfer_order_allocations` (outside scope) | 3 | 9 |
| `StockItem.is_in_stock` | 20 | 0 |
| `StockItem.lock_quantity` | 15 | 0 |
| `StockItem.optional_transfer_fields` | 6 | 0 |
| `StockItem.sales_order_allocation_count` (outside scope) | 0 | 0 |
| `StockItem.save` | 50 | 11 |
| `StockItem.transfer_order_allocation_count` (outside scope) | 0 | 0 |
| `StockItem.update_serial_number` (outside scope) | 18 | 3 |
| `StockItem.validate_batch_code` (outside scope) | 0 | 2 |
| `StockItem.validate_unique` (outside scope) | 12 | 1 |
| `StockLocation.get_items` (outside scope) | 0 | 0 |
| `StockLocation.get_stock_items` (outside scope) | 0 | 0 |
| `StockLocation.stock_item_count` (outside scope) | 0 | 0 |
| `StockRemoveSerializer.save` | 34 | 3 |
| `StockRemoveSerializer.validate` | 42 | 1 |
| `StockStatusCustomSerializer.__init__` (outside scope) | 12 | 26 |
| `_default_delete_on_deplete` (outside scope) | 3 | 4 |

Survivor classification (107): Out of scope 56, Equivalent 51.

| Function | # | Mutation (+ line) | Class | Reason |
|---|---|---|---|---|
| `_default_delete_on_deplete` | `2` | `+        return get_global_setting('STOCK_DELETE_DEPLETED_DEFAULT', No` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `_default_delete_on_deplete` | `4` | `+        return get_global_setting('STOCK_DELETE_DEPLETED_DEFAULT', )` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `_default_delete_on_deplete` | `6` | `+        return get_global_setting('stock_delete_depleted_default', Tr` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `_default_delete_on_deplete` | `7` | `+        return get_global_setting('STOCK_DELETE_DEPLETED_DEFAULT', Fa` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.__str__` | `1` | `+    if self.part.trackable or self.serial:` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem._apply_model_reference_fields` | `3` | `+        instance = deltas.pop(None, None) or kwargs.pop(field, None)` | **Equivalent** | `deltas.pop(None, None)`: the dict has no `None` key, the `or kwargs.pop(field)` branch still runs. |
| `StockItem._apply_status_change` | `16` | `+        old_custom_status if (old_custom_status) and False else old_s` | **Equivalent** | custom statuses are not configured in this deployment; the value only shapes an audit delta that is empty without them. |
| `StockItem._apply_status_change` | `4` | `+    old_custom_status = None` | **Equivalent** | same: `get_custom_status()` is empty without configured custom statuses. |
| `StockItem.clean` | `13` | `+    if not get_global_setting('stock_allow_edit_serial') and self.pk:` | **Equivalent** | InvenTree upper-cases setting keys, so the lower-case key reads the same setting. |
| `StockItem.convert_serial_to_int` | `1` | `+    if InvenTree.ready.isReadOnlyCommand():` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.convert_serial_to_int` | `2` | `+        for plugin in registry.with_mixin(None):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.convert_serial_to_int` | `4` | `+    if serial not in [None, 'XXXX']:` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.delete` | `10` | `+        'stock_allow_delete_serialized', cache=False` | **Equivalent** | settings-lookup argument: the setting is defined and the cache is not enabled in the test configuration |
| `StockItem.delete` | `23` | `+            'location', 'purchase_order__supplier'` | **Equivalent** | query-optimisation argument (select_related): same rows, fewer queries |
| `StockItem.delete` | `24` | `+            'part', 'purchase_order__supplier'` | **Equivalent** | query-optimisation argument (select_related): same rows, fewer queries |
| `StockItem.delete` | `25` | `+            'part', 'location', )` | **Equivalent** | query-optimisation argument (select_related): same rows, fewer queries |
| `StockItem.delete` | `6` | `+        'STOCK_ALLOW_DELETE_SERIALIZED', cache=None` | **Equivalent** | falsy constant replaced by another falsy one (None for False/empty): no observable difference |
| `StockItem.delete` | `8` | `+        'STOCK_ALLOW_DELETE_SERIALIZED', ):` | **Equivalent** | settings-lookup argument: the setting is defined and the cache is not enabled in the test configuration |
| `StockItem.get_sales_order_allocations` | `1` | `+def get_sales_order_allocations(self, active=False, **kwargs):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_sales_order_allocations` | `10` | `+    if active is False:` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_sales_order_allocations` | `13` | `` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_sales_order_allocations` | `14` | `+            )` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_sales_order_allocations` | `3` | `+    if filter_allocations := kwargs.get(None):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_sales_order_allocations` | `4` | `+    if filter_allocations := kwargs.get('XXfilter_allocationsXX'):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_sales_order_allocations` | `5` | `+    if filter_allocations := kwargs.get('FILTER_ALLOCATIONS'):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_sales_order_allocations` | `6` | `+    if exclude_allocations := kwargs.get(None):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_sales_order_allocations` | `7` | `+    if exclude_allocations := kwargs.get('XXexclude_allocationsXX'):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_sales_order_allocations` | `8` | `+    if exclude_allocations := kwargs.get('EXCLUDE_ALLOCATIONS'):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_sales_order_allocations` | `9` | `+    if active is not True:` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_transfer_order_allocations` | `1` | `+def get_transfer_order_allocations(self, active=False, **kwargs):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_transfer_order_allocations` | `10` | `+    if active is False:` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_transfer_order_allocations` | `3` | `+    if filter_allocations := kwargs.get(None):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_transfer_order_allocations` | `4` | `+    if filter_allocations := kwargs.get('XXfilter_allocationsXX'):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_transfer_order_allocations` | `5` | `+    if filter_allocations := kwargs.get('FILTER_ALLOCATIONS'):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_transfer_order_allocations` | `6` | `+    if exclude_allocations := kwargs.get(None):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_transfer_order_allocations` | `7` | `+    if exclude_allocations := kwargs.get('XXexclude_allocationsXX'):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_transfer_order_allocations` | `8` | `+    if exclude_allocations := kwargs.get('EXCLUDE_ALLOCATIONS'):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.get_transfer_order_allocations` | `9` | `+    if active is not True:` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.save` | `26` | `+    notes = kwargs.pop('notes', None)` | **Equivalent** | `notes` default `None` vs `''`: both falsy, same branch and the same stored (empty) note. |
| `StockItem.save` | `32` | `+    event = ""` | **Equivalent** | `event = ""` vs `None`: both falsy, `event or nullcontext()` is unchanged. |
| `StockItem.save` | `33` | `+        if (user or notes) or not has_pending_event(self):` | **Equivalent** | `or not pending` only adds an `audit_event(None, notes='', actor=None)` for a bare save; the audit layer records the same field diff anyway (probe: identical entry without notes/actor). |
| `StockItem.save` | `48` | `+            deltas=None,` | **Equivalent** | the `deltas`/`quantity` arguments of the create event are redundant: the audit entry stores the full field diff (`changes` includes status and quantity; `additional_data` is empty). |
| `StockItem.save` | `50` | `+            quantity=None,` | **Equivalent** | same: `quantity=` of the create event is redundant with `changes['quantity']`. |
| `StockItem.save` | `53` | `` | **Equivalent** | same: dropping `deltas` of the create event leaves `changes` unchanged. |
| `StockItem.save` | `55` | `+            )` | **Equivalent** | same: dropping the `quantity` argument. |
| `StockItem.save` | `56` | `+            deltas={'XXstatusXX': self.status},` | **Equivalent** | same: the key name inside the redundant `deltas` is never read. |
| `StockItem.save` | `57` | `+            deltas={'STATUS': self.status},` | **Equivalent** | same. |
| `StockItem.save` | `60` | `+        super().save(**kwargs)` | **Equivalent** | argument of the base-class call is unused / identical |
| `StockItem.save` | `61` | `+        super().save(*args, )` | **Equivalent** | argument of the base-class call is unused / identical |
| `StockItem.update_serial_number` | `11` | `+    serial = str(getattr(self, 'serial', 'XXXX')).strip()` | **Equivalent** | same. |
| `StockItem.update_serial_number` | `5` | `+    serial = str(getattr(self, 'serial', None)).strip()` | **Equivalent** | `getattr(self, 'serial', default)`: the field always exists, the default is never used. |
| `StockItem.update_serial_number` | `8` | `+    serial = str(getattr(self, 'serial', )).strip()` | **Equivalent** | same. |
| `StockItem.validate_batch_code` | `1` | `+    if InvenTree.ready.isReadOnlyCommand():` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.validate_batch_code` | `2` | `+        for plugin in registry.with_mixin(None):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockItem.validate_unique` | `1` | `+    super().validate_unique(None)` | **Equivalent** | argument of the base-class call is unused / identical |
| `StockAddSerializer.save` | `21` | `+            if quantity is None and quantity <= 0:` | **Equivalent** | `quantity is None and quantity <= 0`: `quantity` is a required decimal (never None); a zero quantity is rejected again by the model guard `quantity <= 0` in `add_stock`. |
| `StockAddSerializer.save` | `23` | `+            if quantity is None or quantity < 0:` | **Equivalent** | `quantity < 0` instead of `<= 0`: zero is rejected by the model-level guard (`add_stock` returns False), so skipping it in `save()` is redundant. |
| `StockAddSerializer.save` | `29` | `+                if field_value := item.get(field_name, ):` | **Equivalent** | `item.get(field_name)` has the same default `None`. |
| `StockAddSerializer.save` | `7` | `+    notes = data.get('notes', None)` | **Equivalent** | `notes` default `None` vs `''`: both stored as an empty note. |
| `StockAddSerializer.save` | `9` | `+    notes = data.get('notes', )` | **Equivalent** | same (`get` without default returns `None`). |
| `StockAdjustmentItemSerializer.__init__` | `11` | `+    self.require_non_zero = kwargs.pop('require_non_zero', None)` | **Equivalent** | falsy constant replaced by another falsy one (None for False/empty): no observable difference |
| `StockAdjustmentItemSerializer.__init__` | `17` | `+    super().__init__(**kwargs)` | **Equivalent** | argument of the base-class call is unused / identical |
| `StockAdjustmentItemSerializer.__init__` | `18` | `+    super().__init__(*args, )` | **Equivalent** | argument of the base-class call is unused / identical |
| `StockAdjustmentItemSerializer.validate_pk` | `11` | `+            'stock_allow_out_of_stock_transfer', backup_value=False, ` | **Equivalent** | settings-lookup argument: the setting is defined and the cache is not enabled in the test configuration |
| `StockAdjustmentItemSerializer.validate_pk` | `12` | `+            'STOCK_ALLOW_OUT_OF_STOCK_TRANSFER', backup_value=True, c` | **Equivalent** | settings-lookup argument: the setting is defined and the cache is not enabled in the test configuration |
| `StockAdjustmentItemSerializer.validate_pk` | `17` | `+            check_status=None, check_quantity=False, check_in_product` | **Equivalent** | falsy constant replaced by another falsy one (None for False/empty): no observable difference |
| `StockAdjustmentItemSerializer.validate_pk` | `18` | `+            check_status=False, check_quantity=None, check_in_product` | **Equivalent** | falsy constant replaced by another falsy one (None for False/empty): no observable difference |
| `StockAdjustmentItemSerializer.validate_pk` | `19` | `+            check_status=False, check_quantity=False, check_in_produc` | **Equivalent** | falsy constant replaced by another falsy one (None for False/empty): no observable difference |
| `StockAdjustmentItemSerializer.validate_pk` | `5` | `+            'STOCK_ALLOW_OUT_OF_STOCK_TRANSFER', backup_value=None, c` | **Equivalent** | falsy constant replaced by another falsy one (None for False/empty): no observable difference |
| `StockAdjustmentItemSerializer.validate_pk` | `6` | `+            'STOCK_ALLOW_OUT_OF_STOCK_TRANSFER', backup_value=False, ` | **Equivalent** | falsy constant replaced by another falsy one (None for False/empty): no observable difference |
| `StockAdjustmentItemSerializer.validate_pk` | `8` | `+            'STOCK_ALLOW_OUT_OF_STOCK_TRANSFER', cache=False` | **Equivalent** | settings-lookup argument: the setting is defined and the cache is not enabled in the test configuration |
| `StockAdjustmentItemSerializer.validate_pk` | `9` | `+            'STOCK_ALLOW_OUT_OF_STOCK_TRANSFER', backup_value=False, ` | **Equivalent** | settings-lookup argument: the setting is defined and the cache is not enabled in the test configuration |
| `StockAdjustmentSerializer.to_internal_value` | `18` | `+                'location'` | **Equivalent** | query-optimisation argument (select_related): same rows, fewer queries |
| `StockAdjustmentSerializer.to_internal_value` | `19` | `+                'part', )` | **Equivalent** | query-optimisation argument (select_related): same rows, fewer queries |
| `StockAdjustmentSerializer.validate` | `1` | `+    super().validate(None)` | **Equivalent** | argument of the base-class call is unused / identical |
| `StockAdjustmentSerializer.validate` | `4` | `+    items = data.get('items', None)` | **Equivalent** | `data.get('items', None)` followed by `if not items`: identical for a missing key. |
| `StockAdjustmentSerializer.validate` | `6` | `+    items = data.get('items', )` | **Equivalent** | same. |
| `StockRemoveSerializer.save` | `21` | `+            if quantity is None and quantity <= 0:` | **Equivalent** | same as StockAddSerializer.save #21 (guard redundant with `take_stock`). |
| `StockRemoveSerializer.save` | `23` | `+            if quantity is None or quantity < 0:` | **Equivalent** | same as StockAddSerializer.save #23. |
| `StockRemoveSerializer.save` | `29` | `+                if field_value := item.get(field_name, ):` | **Equivalent** | same as StockAddSerializer.save #29. |
| `StockRemoveSerializer.validate` | `32` | `+            available = format(stock_item.quantity.normalize(), 'F')` | **Equivalent** | `format(Decimal, 'F')` and `'f'` give the same digits for every finite quantity (they differ only for NaN/Infinity, which the DecimalField rejects). |
| `StockStatusCustomSerializer.__init__` | `1` | `+def __init__(self, *args, include_no_change: bool = True, **kwargs):` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `10` | `+            choices = [(None, _(None)), *choices]` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `11` | `+            choices = [(None, _('XXNo ChangeXX')), *choices]` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `12` | `+            choices = [(None, _('no change')), *choices]` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `13` | `+            choices = [(None, _('NO CHANGE')), *choices]` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `17` | `+    if 'XXlabelXX' not in kwargs:` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `18` | `+    if 'LABEL' not in kwargs:` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `19` | `+    if 'label' in kwargs:` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `2` | `+    if 'XXchoicesXX' not in kwargs:` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `20` | `+        kwargs['label'] = None` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `23` | `+        kwargs['label'] = _(None)` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `24` | `+        kwargs['label'] = _('XXStatusXX')` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `25` | `+        kwargs['label'] = _('status')` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `26` | `+        kwargs['label'] = _('STATUS')` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `27` | `+    if 'XXhelp_textXX' not in kwargs:` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `28` | `+    if 'HELP_TEXT' not in kwargs:` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `29` | `+    if 'help_text' in kwargs:` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `3` | `+    if 'CHOICES' not in kwargs:` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `30` | `+        kwargs['help_text'] = None` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `33` | `+        kwargs['help_text'] = _(None)` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `34` | `+        kwargs['help_text'] = _('XXStock item status codeXX')` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `35` | `+        kwargs['help_text'] = _('stock item status code')` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `36` | `+        kwargs['help_text'] = _('STOCK ITEM STATUS CODE')` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `37` | `+    super().__init__(**kwargs)` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `7` | `+        choices = list(stock.status_codes.StockStatus.items(custom=No` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |
| `StockStatusCustomSerializer.__init__` | `8` | `+        choices = list(stock.status_codes.StockStatus.items(custom=Fa` | **Out of scope** | helper outside the add/remove path (display, allocation queries, serial/batch plugins, status field wrapper) |



## 4. Results by function (final analysis, before the second test round)
| Function | Mutants | Killed | Survived |
|---|---|---|---|
| `ModelPermission._queryset` | 6 | 6 | 0 |
| `PrefetchedPrimaryKeyRelatedField.__init__` | 2 | 2 | 0 |
| `PrefetchedPrimaryKeyRelatedField.to_internal_value` | 7 | 7 | 0 |
| `RolePermission.has_permission` | 14 | 14 | 0 |
| `StockAddSerializer.save` | 14 | 12 | 2 |
| `StockAddSerializer.validate` | 9 | 8 | 1 |
| `StockAdjustView.get_serializer_context` | 2 | 1 | 1 |
| `StockAdjustmentItemSerializer.__init__` | 5 | 5 | 0 |
| `StockAdjustmentItemSerializer.validate_pk` | 14 | 13 | 1 |
| `StockAdjustmentItemSerializer.validate_quantity` | 7 | 7 | 0 |
| `StockAdjustmentSerializer.to_internal_value` | 10 | 10 | 0 |
| `StockAdjustmentSerializer.validate` | 6 | 5 | 1 |
| `StockItem._apply_model_reference_fields` | 5 | 5 | 0 |
| `StockItem._apply_optional_transfer_fields` | 4 | 4 | 0 |
| `StockItem._apply_status_change` | 10 | 10 | 0 |
| `StockItem._audit_deltas` | 1 | 1 | 0 |
| `StockItem._is_empty_tracking_event` | 6 | 6 | 0 |
| `StockItem._resolve_status_kwarg` | 1 | 1 | 0 |
| `StockItem._tracking_deltas` | 7 | 7 | 0 |
| `StockItem.add_stock` | 14 | 14 | 0 |
| `StockItem.can_delete` | 14 | 14 | 0 |
| `StockItem.delete` | 11 | 11 | 0 |
| `StockItem.is_in_stock` | 14 | 14 | 0 |
| `StockItem.lock_quantity` | 10 | 10 | 0 |
| `StockItem.save` | 14 | 14 | 0 |
| `StockItem.take_stock` | 14 | 13 | 1 |
| `StockItem.tracking_event` | 5 | 5 | 0 |
| `StockItem.updateQuantity` | 14 | 13 | 1 |
| `StockRemoveSerializer.save` | 14 | 12 | 2 |
| `StockRemoveSerializer.validate` | 9 | 9 | 0 |

## 5. Analysis of the surviving mutants (27 + 10 = 37 analysed; ≥ 15 required): equivalent / missing test / weak assertion
### 5.1 Final analysis (10 survivors)
| ID | Operator | Function (line) | Mutation | Classification | Action / argument | After the second test round |
|---|---|---|---|---|---|---|
| M010 | CRP | `StockAdjustmentItemSerializer.validate_pk` (L1839) | False -> True | **Equivalent** | `backup_value=False` of `get_global_setting`: it only applies when the setting is not defined, which cannot happen for `STOCK_ALLOW_OUT_OF_STOCK_TRANSFER` (a declared global setting with a default) — unobservable. (The `cache=False` constant of the same call IS observable and is killed by `test_validate_pk_does_not_use_a_cached_setting_value`.) | survives (equivalent) |
| M037 | SDL | `StockAdjustmentSerializer.validate` (L1950) | delete statement: super().validate(data) | **Equivalent** | The base `serializers.Serializer.validate` returns its argument unchanged and its return value is discarded: deleting the call has no effect. | survives (equivalent) |
| M048 | SDL | `StockAddSerializer.validate` (L2045) | delete statement: stock_item = entry['pk'] | **Missing test** | two different items in one request: the limit is checked per item and the error points at the offending entry (`test_add_limit_is_checked_per_item_and_the_error_points_at_the_offending_entry`) | **killed** |
| M059 | LCR | `StockAddSerializer.save` (L2079) | or -> and | **Equivalent** | Redundant guard: for quantity 0 (or negative) `add_stock` itself returns False (model-level guard), so skipping the item in `save()` is unobservable. | survives (equivalent) |
| M060 | CBR-4 | `StockAddSerializer.save` (L2079) | POSITIVE_GUARD quantity <= 0 boundary moved | **Equivalent** | Redundant guard (see above): the model-level `quantity <= 0` check returns False anyway. | survives (equivalent) |
| M082 | LCR | `StockRemoveSerializer.save` (L2150) | or -> and | **Equivalent** | Redundant guard: for quantity 0 `take_stock` itself returns False, so the serializer-level skip is unobservable. | survives (equivalent) |
| M083 | CBR-4 | `StockRemoveSerializer.save` (L2150) | POSITIVE_GUARD quantity <= 0 boundary moved | **Equivalent** | Redundant guard (see above): `take_stock(0)` returns False. | survives (equivalent) |
| M125 | CRP | `StockItem.updateQuantity` (L3287) | False -> True | **Equivalent** | `save(add_note=False)` -> `add_note=True`: the flag only controls the 'created' audit note and is ignored for an existing row (`if self.pk`), and updateQuantity only saves existing items. | survives (equivalent) |
| M143 | CBR-4 | `StockItem.take_stock` (L3466) | POSITIVE_GUARD quantity <= 0 boundary moved | **Equivalent** | First `quantity <= 0` guard: the second guard after the `min()` clamp rejects the same input, so moving this boundary has no effect. | survives (equivalent) |
| M234 | SDL | `StockAdjustView.get_serializer_context` (L240) | delete statement: context['request'] = self.request | **Equivalent** | DRF `GenericAPIView.get_serializer_context` already supplies `request`; the explicit assignment is redundant. | survives (equivalent) |

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
The `mutation` job runs the same runner on a deterministic sample (`--workers 3 --max-per-function 7`, all custom mutants kept) and `tools/mutation_gate.py` requires an **adjusted score ≥ 95 %**, where adjusted = killed ÷ (total − equivalents listed in `docs/mutation_equivalents.json`); the key is `function|mutation|original code` (line-independent but specific). Every surviving mutant that is not a documented equivalent counts against the score.
**CI-produced scores (sampled runs, `evidence/ci/`):** before the killing tests — 159 mutants, 140 killed, **88.1 %** (gate then 85 %, passed); after the first killing tests (PR #13 run 43920009616) — 166 mutants, 157 killed, 9 survivors of which 7 documented → **98.7 % adjusted** (gate 90 %, passed). The threshold was first 85 %, then 90 %, and is now **95 %**: PR #16 (removal of the killing tests) scored **90.4 %** in CI (166 mutants, 150 killed, run 43927877708) and therefore *passed* a 90 % gate — a real weakness found by our own blocked-PR experiment. The improved suite scores 98.7 % on the same sample, the degraded one 90.4 %, so 95 % sits between them with ~3.7 points of tolerance for sampling variation. **Pull request #16** removes the killing tests: the baseline still passes but the score scores 90.4 %, below the 95 % gate → the pipeline blocks it on the **mutation threshold itself** (re-run after the threshold change; the first run at 90 % let it through) (see `docs/CI_QUALITY_GATE.md`).

## 7. Reproduce
`scripts/mutation_setup.sh` then `python tools/mutate.py --workers 5 --max-per-function 14` (≈ 25 min); `python tools/mutate.py --only stock/models.py::StockItem.take_stock` for one function; `python tools/mutate.py --rerun-survivors evidence/mutation/results_final_run.json` re-runs the survivors. Raw data: `evidence/mutation/` (`results_round1.json`, `results_round2.json` = first analysis; `results_final_run.json`, `results_final_round2.json`, `results.json` = final).

