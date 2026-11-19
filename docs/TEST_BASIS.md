# TEST BASIS — InvenTree Stock Module (Add Stock / Remove Stock)

System: InvenTree 1.8.0 dev (API v580), commit `1f51dfe64bf4717fd95df51f1055ffb7a991a01d`, MIT. See `docs/BASELINE.md`.
Team: M1 = 24I-3166, M2 = 24I-3015, M3 = 24I-3106.

## 1. Scope
Module: **Stock** (`src/backend/InvenTree/stock`). Two related workflows over the same shared record.

| ID | Workflow | Starting condition | User action | Expected outcome |
|---|---|---|---|---|
| WF-A | Add stock | StockItem "Keyboard", quantity 10, location Main Warehouse, adjustable | `stock_manager` adds N units (UI dialog or `POST /api/stock/add/`) | 201; quantity = 10 + N; history (audit) entry `STOCK_ADD` with added=N and resulting quantity |
| WF-B | Remove stock | StockItem "Keyboard", quantity q > 0, adjustable | `stock_manager` removes N units (`POST /api/stock/remove/`) | If N ≤ q: 201; quantity = q − N; history (audit) entry `STOCK_REMOVE`. If N > q: **rejected (400)**, quantity still q |

**Shared record:** `StockItem.quantity` — WF-A changes it; WF-B reads it (limit check) and changes it.

## 2. Shared records read/changed
| Record | WF-A | WF-B |
|---|---|---|
| StockItem.quantity | changes | reads (limit) + changes |
| StockItem (existence / pk) | reads | reads; **deleted** when depleted and `delete_on_deplete` |
| StockItem.serialized, customer, belongs_to, consumed_by, sales_order | reads (adjustability) | reads |
| AuditLogEntry (history; `audit_auditlogentry`, event_type 11 = STOCK_ADD, 12 = STOCK_REMOVE) | creates `STOCK_ADD` | creates `STOCK_REMOVE` |
| User / Group / RuleSet (`stock` role) | reads (permission) | reads |

## 3. Functional requirements (≥ 8, ≥ 3 per workflow; FR-03a/b count as one requirement FR-03 for numbering)
| ID | Workflow | Requirement | Source |
|---|---|---|---|
| FR-01 | A | Adding a positive quantity N increases `quantity` by exactly N | **DOC** (`docs/docs/stock/adjust.md`: stock is "increased by the given amount") + CODE `StockItem.add_stock` |
| FR-02 | A | A successful add records a `STOCK_ADD` history entry (added, resulting quantity, user, notes) | **CODE**: `add_stock` tracking_info |
| FR-03a | A | A negative, non-numeric, over-precision (> 5 decimals) or too-large (> 10 digits total) quantity is rejected with HTTP 400 and no change | **CODE**: DRF `DecimalField(max_digits=15, decimal_places=5, min_value=0)` in `StockAdjustmentItemSerializer.quantity` |
| FR-03b | A | A zero quantity is rejected (HTTP 400, no change, no history) | **Assumption A-2** (upstream accepts 0 as a silent no-op; defect DEF-02) |
| FR-04 | A | An item that is not adjustable (assigned to customer / installed / consumed / on sales order) is rejected with "Stock item is not in stock" | **CODE**: `validate_pk` |
| FR-05 | B | Removing N ≤ available decreases `quantity` by exactly N | **DOC** (`adjust.md`: stock is "decreased by the given amount") + CODE `take_stock` |
| FR-06 | B | A successful removal records a `STOCK_REMOVE` history entry (removed, resulting quantity) | **CODE**: `take_stock` deltas |
| FR-07 | B | Removing N > available is **rejected (HTTP 400)** and quantity is unchanged | **Justified assumption A-1** (upstream clamps — see §6) |
| FR-08 | B | Removing exactly all available quantity depletes the item (see BR-3) | **CODE**: `updateQuantity` |
| FR-09 | A,B | Requests without the `stock` role's **add** right are rejected with 403 (both endpoints are POST → `add`; a role with only `change` cannot add or remove), unauthenticated with 401/403, no change | **CODE**: DRF `ModelPermission` (`DjangoModelPermissions`) on the view queryset model `StockItem`: POST requires the Django permission `stock.add_stockitem`, which `update_group_roles` derives from the group's `stock` RuleSet `can_add`. `RolePermission` is a no-op for these views (the serializer has no `Meta.model`, so it returns True) — verified by `test_role_permission_stock_adjust_views_have_no_model_and_do_not_restrict` |
| FR-10 | A,B | A multi-item request is atomic: if any item is invalid, no item changes | **CODE**: `transaction.atomic` + serializer validation |
| FR-11 | A,B | Add/Remove on a serialized item changes nothing | **CODE**: `add_stock`/`take_stock` serialized guard; empirically: 201, no change, no history |

## 4. Business rules (4)
| ID | Type | Rule |
|---|---|---|
| BR-1 | **Boundary/limit** | Add: `0 < N ≤ 9 999 999 999.99999` per request (DecimalField max_digits=15, decimal_places=5) **and the resulting quantity must stay representable** (≤ 9 999 999 999.99999). Remove: `0 < N ≤ available quantity`. Exactly-at-limit allowed; just above rejected. *Upstream deviations: N = 0 accepted (DEF-02); N > available clamped (DEF-01); resulting quantity not bounded — adding 9 999 999 999.99999 to 10 stores 10 000 000 009.99999 and `GET /api/stock/1/` then returns HTTP 500 (DEF-03).* |
| BR-2 | **Decision, ≥ 2 Boolean conditions** | `validate_pk` rejects ("Stock item is not in stock") iff `¬ALLOW ∧ ¬A` where `ALLOW = STOCK_ALLOW_OUT_OF_STOCK_TRANSFER` (global setting, default False; the seed does not change it) and `A = (sales_order is None) ∧ (belongs_to is None) ∧ (customer is None) ∧ (consumed_by is None)` (the structural part of `StockItem.is_in_stock` called with `check_status=False, check_quantity=False, check_in_production=False`, so **status, quantity, location and `is_building` do not matter**). Conditions: 5 Booleans. When `ALLOW` is true the adjustability check is **skipped entirely** (no `is_in_stock` call). This is the MCC/MC/DC target. Empirically verified branch: `belongs_to` set → 400 "Stock item is not in stock"; `customer`, `consumed_by`, `sales_order` branches are exercised in Phase 4/6. |
| BR-3 | **Change of state** | Removing all quantity: if `delete_on_deplete` and `can_delete()` the StockItem is deleted (state DELETED); otherwise it remains with quantity 0 (state DEPLETED, `in_stock` false). Adding to a DEPLETED item returns it to IN_STOCK. Removing from DEPLETED is invalid. |
| BR-4 | **Role permission** | `POST /api/stock/add/` and `/remove/` require role `stock` with `add` right. |

### Roles (2 with different permissions)
| Role (group) | stock.view | stock.add | stock.change | stock.delete | Test user |
|---|---|---|---|---|---|
| `stock_manager` | ✔ | ✔ | ✔ (seeded, not exercised) | ✔ (seeded, not exercised) | `manager` |
| `stock_viewer` | ✔ | ✘ | ✘ | ✘ | `viewer` |
| (superuser) | all | all | all | all | `admin` (setup only) |
Verified empirically (2026-11-16) with curl: manager list/add/remove = 200/201/201; viewer list/add/remove = 200/403/403 (evidence in `evidence/phase1/roles.txt`). `stock_viewer` has `stock.view` via the seeded RuleSet (`can_view=True`); BR-4: both endpoints are POST, which requires the `add` right.

## 5. State model (for state-transition testing)
States of a StockItem w.r.t. adjustment: `IN_STOCK (q>0)`, `DEPLETED (q=0, retained)`, `DELETED`, `NON_ADJUSTABLE (customer/installed/consumed/sales order)`.
| From | Event | To |
|---|---|---|
| IN_STOCK | add N | IN_STOCK |
| IN_STOCK | remove N<q | IN_STOCK |
| IN_STOCK | remove q (delete_on_deplete=false) | DEPLETED |
| IN_STOCK | remove q (delete_on_deplete=true) | DELETED |
| DEPLETED | add N | IN_STOCK |
| DEPLETED | remove N | **disallowed**: nothing is available, so any removal exceeds the available quantity → 400 "Cannot remove more than the available quantity (0)" (baseline upstream: 201, silent no-op — the same defect as DEF-01; fixed together with it in PR #13) |
| DELETED | add / remove | **disallowed** (400 `Invalid pk … object does not exist`) |
| NON_ADJUSTABLE | add / remove | **disallowed** (400) |
| IN_STOCK | remove N>q | **disallowed** (400, assumption A-1) — state-level evidence for the IN_STOCK disallowed case: `test_non_adjustable_item_disallowed_transition_unchanged` (IN_STOCK → NON_ADJUSTABLE) and the strict-xfail DEF-01 tests |

## 6. Justified assumptions and verified upstream behaviour
- **A-1 (over-removal).** The task example requires rejection when removing more than available ("try to dispatch seven more. Verify the rejection and confirm the balance is still six."). Upstream behaviour observed on the baseline: `POST /api/stock/remove/ {pk:1, quantity:100}` on quantity 10 → **201**, quantity clamped to 10 → depleted (`take_stock`: `quantity = min(quantity, self.quantity)`); the item is then **deleted** if `delete_on_deplete` is true (observed with the default setting) or retained at 0 if false (the seed sets false explicitly). Either way the excess is silently discarded. We therefore treat FR-07/BR-1 as the expected behaviour and log the upstream behaviour as defect **DEF-01**. The history entry records the clamped amount (`removed: 10`), not the requested one (100) (high severity: silent data loss). The documented fix (Phase 12) adds the rejection.
- **A-2 (zero/negative).** Upstream silently ignores `quantity == 0` for add/remove (HTTP 201, no change, no history) because `StockAdjustmentItemSerializer` uses `min_value=0` so 0 passes validation (the `quantity < 0` branch of `validate_quantity` is dead code), and `save()` skips `quantity <= 0`. We treat quantity 0 as invalid per FR-03 (expected 400) and log as weakness candidate. Confirmed from source (`min_value=Decimal(0)`; `save()` skips `quantity <= 0`); empirical confirmation in `evidence/phase1/over_removal.txt`.
- **A-3 (serialized).** Add/Remove on serialized items returns 201 with no change upstream; FR-11 asserts only "no change".
- **A-4 (database).** SQLite is used (no PostgreSQL available). `select_for_update` is not expected to provide row locks on SQLite (not tested); concurrency behaviour is out of scope except the k6 load test.
- **A-5 (users).** Test users are created by `scripts/seed_data.py` and are synthetic.

- **DEF candidates found during basis analysis** (logged as GitHub Issues in our repository; see `docs/DEFECTS.md`): DEF-01 over-removal clamped/silent data loss; DEF-02 zero quantity accepted as silent 201 no-op; DEF-03 resulting quantity overflow → 500 on read.

## 7. Unit-test scope (server-side business logic on the add/remove path; single source of truth = `SCOPE` in `tools/scope_coverage.py`)
Measured per function with coverage.py (branch mode); every function is listed:
1. `stock/serializers.py`: `StockAdjustmentItemSerializer.{__init__, validate_pk, validate_quantity}`, `StockAdjustmentSerializer.{to_internal_value, validate}`, `StockAddSerializer.save`, `StockRemoveSerializer.validate` (the DEF-01 fix, PR #13), `StockRemoveSerializer.save`
2. `stock/models.py`: `StockItem.{is_in_stock, lock_quantity, updateQuantity, add_stock, take_stock, optional_transfer_fields, model_reference_fields, _apply_model_reference_fields, _resolve_status_kwarg, _apply_status_change, _apply_optional_transfer_fields, can_delete, installed_item_count, save, delete, tracking_event, _tracking_deltas, _audit_deltas, _is_empty_tracking_event}`
3. `stock/api.py`: `StockAdjustView.get_serializer_context` (class bodies `StockAdd`/`StockRemove` hold declarations only)
4. `InvenTree/fields.py`: `PrefetchedPrimaryKeyRelatedField.{__init__, to_internal_value}` (the pk lookup behind `validate_pk`)
5. `InvenTree/permissions.py`: `ModelPermission._queryset`, `RolePermission.has_permission` (BR-4 enforcement path; see §4 note)
**Not in scope (justified in `docs/COVERAGE_JUSTIFICATION.md`):** OAuth2-token scope wrapper (our workflows authenticate with Basic/session), `StockItem.save/delete` (generic persistence, exercised but not measured as business rules), status helpers in `generic/states` (called by `_apply_status_change`; third-level utility), merge/disassemble/serialization/transfer/count workflows.
**Critical module (complete MCC, then MC/DC pairs):** BR-2 `validate_pk` (5 conditions, 32 rows) is the primary critical decision. In addition `tools/mcdc.py` enumerates and the suite executes every feasible row of these multi-condition decisions: `is_in_stock` (status, location, quantity, production), BR-3 deletion in `updateQuantity` (`quantity == 0 ∧ delete_on_deplete ∧ can_delete()`), BR-1 `take_stock` guards, `validate_quantity`, the prefetch-field fallback, `_apply_status_change`, `_resolve_status_kwarg` and `_is_empty_tracking_event` — see `docs/MCC_MCDC.md`. Decisions with short-circuit coupling are reported with their infeasible/masked rows. Decisions not enumerated: `_apply_model_reference_fields` (`deltas.pop(f) or kwargs.pop(f)` — a dictionary-default idiom, not a business decision) and the serializer `save` guard `quantity is None or quantity <= 0` (operand `is None` is unreachable: the field is `required=True` and non-nullable; defended in `docs/COVERAGE_JUSTIFICATION.md`).

## 8. Test data and reset
`scripts/reset.sh` rebuilds the SQLite DB and seeds: users `admin/manager/viewer`; category "Peripherals"; location "Main Warehouse"; parts Keyboard (10), Mouse (25), Monitor (0).

## 9. Entry in the shared sheet (registration of the repository URL and project description)
The team entered the repository URL and the project description on the course sheet at the start of the project (the confirmation is held by the team; no screenshot is stored in this repository).
- Original GitHub Repository URL: https://github.com/inventree/InvenTree
- Project Description: InvenTree is an open-source (MIT) inventory management system built with Python/Django and a React web interface, with a REST API, database and role-based permissions. We test its Stock module with two related workflows, adding and removing stock. Both read and change the same shared record, the item's stock quantity, and removal is rejected if it exceeds the available quantity.
