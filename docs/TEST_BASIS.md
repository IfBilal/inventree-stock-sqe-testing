# TEST BASIS — InvenTree Stock Module (Add Stock / Remove Stock)

System: InvenTree 1.8.0 dev (API v580), commit `1f51dfe64bf4717fd95df51f1055ffb7a991a01d`, MIT. See `docs/BASELINE.md`.
Team: M1 = 24I-3166, M2 = 24I-3015, M3 = 24I-3106.

## 1. Scope
Module: **Stock** (`src/backend/InvenTree/stock`). Two related workflows over the same shared record.

| ID | Workflow | Starting condition | User action | Expected outcome |
|---|---|---|---|---|
| WF-A | Add stock | StockItem "Keyboard", quantity 10, location Main Warehouse, adjustable | `stock_manager` adds N units (UI dialog or `POST /api/stock/add/`) | 201; quantity = 10 + N; history entry `STOCK_ADD` with added=N and resulting quantity |
| WF-B | Remove stock | StockItem "Keyboard", quantity q > 0, adjustable | `stock_manager` removes N units (`POST /api/stock/remove/`) | If N ≤ q: 201; quantity = q − N; history entry `STOCK_REMOVE`. If N > q: **rejected (400)**, quantity still q |

**Shared record:** `StockItem.quantity` — WF-A changes it; WF-B reads it (limit check) and changes it.

## 2. Shared records read/changed
| Record | WF-A | WF-B |
|---|---|---|
| StockItem.quantity | changes | reads (limit) + changes |
| StockItem (existence / pk) | reads | reads; **deleted** when depleted and `delete_on_deplete` |
| StockItem.serialized, customer, belongs_to, consumed_by, sales_order | reads (adjustability) | reads |
| StockItemTracking (history) | creates `STOCK_ADD` | creates `STOCK_REMOVE` |
| User / Group / RuleSet (`stock` role) | reads (permission) | reads |

## 3. Functional requirements (≥ 8, ≥ 3 per workflow)
| ID | Workflow | Requirement | Source |
|---|---|---|---|
| FR-01 | A | Adding a positive quantity N increases `quantity` by exactly N | `StockItem.add_stock`; docs `docs/docs/stock/adjust.md` |
| FR-02 | A | A successful add records a `STOCK_ADD` history entry (added, resulting quantity, user, notes) | `add_stock` tracking_info |
| FR-03 | A | A non-positive, negative, non-numeric or over-precision quantity is rejected with HTTP 400 and no change | `StockAdjustmentItemSerializer.quantity` / `validate_quantity` |
| FR-04 | A | An item that is not adjustable (assigned to customer / installed / consumed / on sales order) is rejected with "Stock item is not in stock" | `validate_pk` |
| FR-05 | B | Removing N ≤ available decreases `quantity` by exactly N | `take_stock` |
| FR-06 | B | A successful removal records a `STOCK_REMOVE` history entry (removed, resulting quantity) | `take_stock` deltas |
| FR-07 | B | Removing N > available is **rejected (HTTP 400)** and quantity is unchanged | **Justified assumption A-1** (upstream clamps — see §6) |
| FR-08 | B | Removing exactly all available quantity depletes the item (see BR-3) | `updateQuantity` |
| FR-09 | A,B | Requests without `stock.add` permission are rejected with 403, unauthenticated with 401/403, no change | `RolePermission` |
| FR-10 | A,B | A multi-item request is atomic: if any item is invalid, no item changes | `transaction.atomic` + serializer validation |
| FR-11 | A,B | Add/Remove on a serialized item changes nothing | `add_stock`/`take_stock` serialized guard |

## 4. Business rules (4)
| ID | Type | Rule |
|---|---|---|
| BR-1 | **Boundary/limit** | Add: `0 < N ≤ 9 999 999 999.99999` (DecimalField max_digits=15, decimal_places=5). Remove: `0 < N ≤ available quantity`. Exactly-at-limit allowed; just above rejected. |
| BR-2 | **Decision, ≥ 2 Boolean conditions** | An item is adjustable iff `customer is None ∧ belongs_to is None ∧ consumed_by is None ∧ sales_order is None` (and, when `STOCK_ALLOW_OUT_OF_STOCK_TRANSFER` is false, the `is_in_stock` structural checks). Else rejected "Stock item is not in stock". |
| BR-3 | **Change of state** | Removing all quantity: if `delete_on_deplete` and `can_delete()` the StockItem is deleted (state DELETED); otherwise it remains with quantity 0 (state DEPLETED, `in_stock` false). Adding to a DEPLETED item returns it to IN_STOCK. Removing from DEPLETED is invalid. |
| BR-4 | **Role permission** | `POST /api/stock/add/` and `/remove/` require role `stock` with `add` right. |

### Roles (2 with different permissions)
| Role (group) | stock.view | stock.add | stock.change | stock.delete | Test user |
|---|---|---|---|---|---|
| `stock_manager` | ✔ | ✔ | ✔ | ✔ | `manager` |
| `stock_viewer` | ✔ | ✘ | ✘ | ✘ | `viewer` |
| (superuser) | all | all | all | all | `admin` (setup only) |
Verified empirically (2026-11-16): manager add=201/remove=201; viewer list=200, add=403, remove=403.

## 5. State model (for state-transition testing)
States of a StockItem w.r.t. adjustment: `IN_STOCK (q>0)`, `DEPLETED (q=0, retained)`, `DELETED`, `NON_ADJUSTABLE (customer/installed/consumed/sales order)`.
| From | Event | To |
|---|---|---|
| IN_STOCK | add N | IN_STOCK |
| IN_STOCK | remove N<q | IN_STOCK |
| IN_STOCK | remove q (delete_on_deplete=false) | DEPLETED |
| IN_STOCK | remove q (delete_on_deplete=true) | DELETED |
| DEPLETED | add N | IN_STOCK |
| DEPLETED | remove N | **disallowed** (nothing to remove; no change) |
| DELETED | add / remove | **disallowed** (404/400 invalid pk) |
| NON_ADJUSTABLE | add / remove | **disallowed** (400) |
| IN_STOCK | remove N>q | **disallowed** (400, assumption A-1) |

## 6. Justified assumptions and verified upstream behaviour
- **A-1 (over-removal).** The task example requires rejection when removing more than available ("try to dispatch seven more. Verify the rejection and confirm the balance is still six."). Upstream behaviour observed on the baseline: `POST /api/stock/remove/ {pk:1, quantity:100}` on quantity 10 → **201**, quantity clamped to 10 → depleted → **item deleted** (`take_stock`: `quantity = min(quantity, self.quantity)`). We therefore treat FR-07/BR-1 as the expected behaviour and log the upstream behaviour as defect **DEF-01** (high severity: silent data loss). The documented fix (Phase 12) adds the rejection.
- **A-2 (zero/negative).** Upstream silently ignores `quantity == 0` for add/remove (HTTP 201, no change, no history) because `StockAdjustmentItemSerializer` uses `min_value=0`. We treat quantity 0 as invalid per FR-03 (expected 400) and log as weakness candidate. (To be confirmed against the running system in Phase 6.)
- **A-3 (serialized).** Add/Remove on serialized items returns 201 with no change upstream; FR-11 asserts only "no change".
- **A-4 (database).** SQLite is used (no PostgreSQL available). `select_for_update` is a no-op on SQLite; concurrency behaviour is therefore out of scope.
- **A-5 (users).** Test users are created by `scripts/seed_data.py` and are synthetic.

## 7. Unit-test scope (server-side business logic, "100% statement + branch")
Defined precisely (functions only, measured per function with coverage.py branch mode):
1. `stock/serializers.py`: `StockAdjustmentItemSerializer.validate_pk`, `validate_quantity`, `StockAdjustmentSerializer.validate`, `.to_internal_value`, `StockAddSerializer.save`, `StockRemoveSerializer.save`
2. `stock/models.py`: `StockItem.add_stock`, `take_stock`, `updateQuantity`, `is_in_stock`, `lock_quantity`
3. `stock/api.py`: `StockAdjustView`, `StockAdd`, `StockRemove`
**Critical module (MCC / MC/DC):** `StockItem.is_in_stock` + `validate_pk` (BR-2) and `take_stock` limit logic (BR-1).

## 8. Test data and reset
`scripts/reset.sh` rebuilds the SQLite DB and seeds: users `admin/manager/viewer`; category "Peripherals"; location "Main Warehouse"; parts Keyboard (10), Mouse (25), Monitor (0).

## 9. Entry in the shared sheet (to submit)
- Original GitHub Repository URL: https://github.com/inventree/InvenTree
- Project Description: InvenTree is an open-source (MIT) inventory management system built with Python/Django and a React web interface, with a REST API, database and role-based permissions. We test its Stock module with two related workflows, adding and removing stock. Both read and change the same shared record, the item's stock quantity, and removal is rejected if it exceeds the available quantity.
