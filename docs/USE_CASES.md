# USE CASE SPECIFICATION — Stock Add / Remove (6 use cases, 2 per member)

Actors: **Manager** = `manager` (group `stock_manager`), **Viewer** = `viewer` (group `stock_viewer`), **Admin** = `admin` (superuser).
**Independence:** every flow is one Playwright test (`tests/team/e2e/`) that first creates its **own fresh item** of the seeded "Keyboard" part through the API with the quantity stated in the flow's precondition (so flows are order-free and need no reset); postconditions are read back **independently of the UI** through the API (`GET /api/stock/{id}/`, history via `/api/audit/`). The seeded values (Keyboard 10, Mouse 25, Monitor 0) only illustrate the starting states.
"Baseline" = predicted result on the unmodified upstream build; **FAIL** = the flow exposes a defect there. After PR #13 (DEF-01 fixed) the over-removal flows pass; the DEF-02 flows (zero quantity) pass since PR #17. No flow is an expected failure any more.
Ownership: M1 = 24I-3166 (UC-01, UC-02), M2 = 24I-3015 (UC-03, UC-04), M3 = 24I-3106 (UC-05, UC-06).

**Common structure per use case:** *Actor*, *Trigger*, *Precondition*, *Main flow*, *Alternative flows (≥ 2)*, *Exception flows (≥ 2)*, *Postcondition (success)*, *Postcondition (exception)*.

---
## UC-01 Add stock to an item (M1) — WF-A — FR-01, FR-02, FR-03, BR-1
- **Actor / trigger:** Manager records received units. **Precondition:** logged in as manager; an adjustable item exists with quantity 10, no history.
- **Postcondition (success):** quantity = old + N, exactly one `STOCK_ADD` history entry (added N, before/after, actor `manager`, notes if given), success toast shown. **Postcondition (exception):** quantity unchanged, no history entry, dialog stays open with the error.
Actor: Manager. Trigger: wants to record received units. Pre (all flows): logged in as manager, Keyboard qty 10, no prior history entries for the item. Post (main): qty 15 and one new `Stock added` history entry (added 5, resulting 15, user `manager`).
| ID | Flow | Steps | Expected | Baseline |
|---|---|---|---|---|
| UC01-MAIN | Main | Open Keyboard → Stock actions → Add stock → quantity 5 → Submit | Success message shown; item page shows 15; history has 1 add entry (5, 15) | PASS |
| UC01-AF1 | Alternative | Same, quantity 0.5 (decimal) | qty 10.5; history entry added 0.5 | PASS |
| UC01-AF2 | Alternative | Same, quantity 5 with notes "restock" | qty 15; history entry carries note "restock" | PASS |
| UC01-EF1 | Exception | quantity 0 | The dialog stays open and an error message is shown; qty stays 10; **no** history entry (baseline: "Success — Stock added", silent no-op) | baseline FAIL (DEF-02) → PASS after PR #17 |
| UC01-EF2 | Exception | typed quantity −3 | An error message is shown; qty stays 10; no history entry (baseline: the field accepts −3, the UI reports "Success — Stock added" and nothing changes) | baseline FAIL (DEF-02 family) → PASS after PR #17 |

## UC-02 Remove stock from an item (M1) — WF-B — FR-05, FR-06, FR-07, BR-1
- **Actor / trigger:** Manager records consumed/removed units. **Precondition:** logged in as manager; an item with quantity 10, no history.
- **Postcondition (success):** quantity = old − N, one `STOCK_REMOVE` entry (removed N, before/after, actor, notes). **Postcondition (exception):** quantity unchanged, no history entry, error names the rule (available quantity).
Actor: Manager. Pre: logged in as manager, Keyboard qty 10.
| ID | Flow | Steps | Expected | Baseline |
|---|---|---|---|---|
| UC02-MAIN | Main | Stock actions → Remove stock → 4 → Submit | success; qty 6; history has 1 remove entry (4, 6) | PASS |
| UC02-AF1 | Alternative | remove 9 | qty 1; history (9, 1) | PASS |
| UC02-AF2 | Alternative | remove 4 with notes "damaged" | qty 6; history note "damaged" | PASS |
| UC02-EF1 | Exception | remove 11 (> 10) | **Rejected** with a message naming the available quantity (10); qty stays 10; no history entry (baseline: "Success — Stock removed", quantity becomes 0) | baseline FAIL (DEF-01) → PASS after PR #13 |
| UC02-EF2 | Exception | quantity 0 | Error shown; qty stays 10; no history entry | baseline FAIL (DEF-02) → PASS after PR #17 |
**Post (main):** qty 6, one `STOCK_REMOVE` history (audit) entry. **Post (EF):** qty and history unchanged.

## UC-03 Deplete an item (M2) — WF-B — FR-08, BR-3
- **Actor / trigger:** Manager removes everything. **Precondition:** logged in as manager; an item with quantity 25 (`delete_on_deplete=false` unless stated).
- **Postcondition (success):** quantity 0 and `in_stock=false` (or item deleted: GET 404, history survives); history entries as removed. **Postcondition (exception):** quantity/state unchanged, no history entry.
Actor: Manager. Pre: logged in as manager, Mouse qty 25 and `delete_on_deplete=False` (seed).
| ID | Flow | Steps | Expected | Baseline |
|---|---|---|---|---|
| UC03-MAIN | Main | Remove 25 | Item page still exists with qty 0 and shown as out of stock; history has remove (25, 0) | PASS |
| UC03-AF1 | Alternative | Pre: set `delete_on_deplete=True` through the API (PATCH by manager) → remove 25 | Item no longer exists: item page 404, `GET /api/stock/2/` = 404 | PASS |
| UC03-AF2 | Alternative | Remove 24, then remove 1 | After 1st: qty 1 (still in stock); after 2nd: qty 0 | PASS |
| UC03-EF1 | Exception | Pre: item with qty 0 → open Remove Stock | The dialog lists **no entries** ("No entries available", no quantity field); qty 0, no history entry (the baseline API alone would accept the call as a silent 201 no-op; after the DEF-01 fix it answers 400) | PASS |
| UC03-EF2 | Exception | remove 26 (> 25) | Rejected; qty stays 25; no history entry | baseline FAIL (DEF-01) → PASS after PR #13 |
**Post:** exactly as each flow's Expected column.

## UC-04 Restock a depleted item (M2) — WF-A and WF-B — BR-3, BR-1, FR-01
- **Actor / trigger:** Manager restocks an empty item. **Precondition:** logged in as manager; item with quantity 0 (retained), no history.
- **Postcondition (success):** `in_stock=true`, quantity as computed, history entries in order with the correct balances. **Postcondition (exception):** quantity 0, no history entry.
Actor: Manager. Pre: logged in as manager, Monitor pk3 qty 0 (retained).
| ID | Flow | Steps | Expected | Baseline |
|---|---|---|---|---|
| UC04-MAIN | Main | Add 8 | qty 8; item is in stock again | PASS |
| UC04-AF1 | Alternative | Add 8 then remove 3 (cross-workflow) | qty 5; history shows add (8) then remove (3) in that order | PASS |
| UC04-AF2 | Alternative | Add 8, then add 2 (repeated action) | qty 10; two add entries; no duplicate entry | PASS |
| UC04-EF1 | Exception | Add 10 000 000 000 (above the maximum representable value of the field) | Rejected with "Ensure that there are no more than 10 digits before the decimal point."; qty stays 0 | PASS |
| UC04-EF2 | Exception | Add 0.000001 (6 decimals) | Rejected with "Ensure that there are no more than 5 decimal places."; qty stays 0 | PASS |
Boundary value of the field (9 999 999 999.99999) is covered by BVA at API level.

## UC-05 Role-restricted adjustment (M3) — BR-4, FR-09
- **Actor / trigger:** a user of each role (viewer, manager, admin, anonymous) tries to see or change stock. **Precondition:** an item with quantity 10; the user is logged in with the role of the flow (anonymous: not logged in).
- **Postcondition (success, allowed roles):** the change is applied and recorded with the actor. **Postcondition (exception, denied roles):** quantity 10, no history entry; API 403 (viewer) / 401 (anonymous); UI shows no operations menu / redirects to `/web/login`.
Pre: Keyboard qty 10.
| ID | Flow | Steps | Expected | Baseline |
|---|---|---|---|---|
| UC05-MAIN | Main | Viewer logs in, opens Keyboard | The page shows `QUANTITY: 10` but **no Stock Operations menu** (no Add/Remove Stock actions); qty still 10 | PASS |
| UC05-AF1 | Alternative | Manager adds 1 on the same item | qty 11 | PASS |
| UC05-AF2 | Alternative | Admin removes 1 | qty 9 | PASS |
| UC05-EF1 | Exception | Viewer `POST /api/stock/add/` pk1 qty 1 | HTTP 403; qty 10; no history entry | PASS |
| UC05-EF2 | Exception | Unauthenticated `POST /api/stock/remove/`; and `/web/stock/item/1/details` without login | API 401; UI redirected to `/web/login`; qty 10 | PASS |

## UC-06 Correct a rejected adjustment (M3) — WF-A and WF-B — FR-03a, FR-07, BR-1 (usability)
- **Actor / trigger:** Manager entered an invalid value and corrects it. **Precondition:** logged in as manager; an item with quantity 10; the Add/Remove dialog is open.
- **Postcondition (success):** after the correction the change is applied exactly once (one history entry); **(exception):** every rejected attempt leaves quantity and history unchanged.
Actor: Manager. Pre: logged in as manager, fresh item with qty 10.
| ID | Flow | Steps | Expected | Baseline |
|---|---|---|---|---|
| UC06-MAIN | Main (Add) | Add 1.123456 → rejected, the error says "Ensure that there are no more than 5 decimal places." → change to 1.12345 → Submit | Error first (dialog open, qty unchanged); then success "Stock added"; qty 11.12345; one history entry | PASS |
| UC06-AF1 | Alternative (Remove) | Remove 15 → rejected with a message that names the available quantity (10) → correct to 10 → Submit | Error first (qty 10, no history); then success; qty 0 (item retained); one history entry | baseline FAIL (DEF-01) → PASS after PR #13 |
| UC06-AF2 | Alternative (keyboard) | Keyboard only: focus reaches quantity → notes → Submit in that order; Enter inside the quantity field does not submit (UX-01); Tab to Submit and Enter submits | Focus order as stated; dialog still open after Enter in the field; form submitted from the Submit button; qty 12 | PASS |
| UC06-EF1 | Exception | After the 6-decimal rejection correct to 0 | Rejected again with a message; qty stays 10 | baseline FAIL (DEF-02) → PASS after PR #17 |
| UC06-EF2 | Exception | After the rejection enter text "abc" | "A valid number is required."; qty stays 10 | PASS |
Post: rejected attempts leave no history entries.
