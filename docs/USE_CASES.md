# USE CASE SPECIFICATION — Stock Add / Remove (6 use cases, 2 per member)

Actor roles: **Manager** = `manager` (group `stock_manager`), **Viewer** = `viewer` (group `stock_viewer`). All data synthetic (`scripts/reset.sh`). Each use case has preconditions, main flow, ≥ 2 alternative flows (AF), ≥ 2 exception flows (EF) and postconditions. Every flow maps to one automated Playwright test (`tests/team/e2e/`), ID in brackets. Traceability: FR/BR in `docs/TEST_BASIS.md`.

Ownership: M1 = 24I-3166 (UC-01, UC-02), M2 = 24I-3015 (UC-03, UC-04), M3 = 24I-3106 (UC-05, UC-06).

---
## UC-01 Add stock to an item (M1) — WF-A — FR-01, FR-02, BR-1
- **Pre:** Manager logged in; Keyboard StockItem quantity 10.
- **Main flow [UC01-MAIN]:** open Keyboard stock item → Stock actions → Add stock → enter 5 → submit → success shown; quantity 15; history shows a "stock added" entry.
- **AF-1 [UC01-AF1]:** add a decimal quantity 0.5 → quantity 15.5.
- **AF-2 [UC01-AF2]:** add with notes "restock" → history entry contains the note.
- **EF-1 [UC01-EF1]:** quantity 0 → rejected with message; quantity unchanged.
- **EF-2 [UC01-EF2]:** negative quantity −3 → rejected; unchanged.
- **Post:** (main) quantity = 15, one new `STOCK_ADD` tracking entry; (EF) quantity and history unchanged.

## UC-02 Remove stock from an item (M1) — WF-B — FR-05, FR-06, FR-07, BR-1
- **Pre:** Manager logged in; Keyboard quantity 10.
- **Main flow [UC02-MAIN]:** Stock actions → Remove stock → 4 → submit → quantity 6; history shows removal.
- **AF-1 [UC02-AF1]:** remove exactly the available quantity minus 1 (9) → quantity 1.
- **AF-2 [UC02-AF2]:** remove with notes → history entry contains the note.
- **EF-1 [UC02-EF1]:** remove 7 when quantity 6 → **rejected**, quantity still 6 (assumption A-1; expected to FAIL on baseline → DEF-01).
- **EF-2 [UC02-EF2]:** quantity 0 → rejected; unchanged.
- **Post:** (main) quantity 6, `STOCK_REMOVE` entry; (EF) unchanged.

## UC-03 Deplete an item (M2) — WF-B — FR-08, BR-3
- **Pre:** Manager logged in; Mouse quantity 25 (`delete_on_deplete` as configured).
- **Main flow [UC03-MAIN]:** remove 25 with delete_on_deplete = false → item remains at quantity 0 and shows out of stock.
- **AF-1 [UC03-AF1]:** with delete_on_deplete = true → item no longer exists (404 on its page).
- **AF-2 [UC03-AF2]:** remove 24 then 1 in two actions → depleted only after the second.
- **EF-1 [UC03-EF1]:** remove from the already-depleted item → no change, no new history entry.
- **EF-2 [UC03-EF2]:** attempt to remove 26 (> 25) → rejected, quantity still 25.
- **Post:** quantity 0 (retained) or item deleted; history consistent with actions.

## UC-04 Restock a depleted item (M2) — WF-A→B — BR-3, FR-01
- **Pre:** Manager logged in; Monitor quantity 0 (retained).
- **Main flow [UC04-MAIN]:** add 8 → quantity 8, item in stock again.
- **AF-1 [UC04-AF1]:** add 8 then remove 3 (cross-workflow) → quantity 5 (shared record read back).
- **AF-2 [UC04-AF2]:** add the maximum representable value 9 999 999 999.99999 → accepted.
- **EF-1 [UC04-EF1]:** add above the maximum → rejected; quantity 0.
- **EF-2 [UC04-EF2]:** add a value with more than 5 decimals (0.000001) → rejected; quantity 0.
- **Post:** quantity as computed; history shows add then remove entries.

## UC-05 Role-restricted adjustment (M3) — BR-4, FR-09
- **Pre:** users manager, viewer exist; Keyboard quantity 10.
- **Main flow [UC05-MAIN]:** viewer opens Keyboard → stock action menu has no add/remove actions (or they are rejected) → quantity still 10.
- **AF-1 [UC05-AF1]:** manager can perform add (quantity 11) — same item.
- **AF-2 [UC05-AF2]:** admin (superuser) can perform remove.
- **EF-1 [UC05-EF1]:** viewer calls add through the API directly → 403; quantity 10.
- **EF-2 [UC05-EF2]:** unauthenticated request → 401/403 and redirect to login in the UI; quantity 10.
- **Post:** quantity changes only for authorized actions.

## UC-06 Correct a rejected removal (M3) — WF-B — FR-07, BR-1 (usability)
- **Pre:** Manager logged in; Keyboard quantity 10.
- **Main flow [UC06-MAIN]:** enter 15 → rejected, error explains the available quantity → correct to 10 → success → quantity 0/retained per setting.
- **AF-1 [UC06-AF1]:** correct to 5 instead → quantity 5.
- **AF-2 [UC06-AF2]:** correct by keyboard-only navigation (Tab order: quantity → notes → submit; Enter submits).
- **EF-1 [UC06-EF1]:** correct to 0 → rejected again with message.
- **EF-2 [UC06-EF2]:** correct to non-numeric text → rejected.
- **Post:** quantity matches last accepted action; rejected attempts left no history.
