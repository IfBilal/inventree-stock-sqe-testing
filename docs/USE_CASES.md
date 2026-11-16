# USE CASE SPECIFICATION — Stock Add / Remove (6 use cases, 2 per member)

Actors: **Manager** = `manager` (group `stock_manager`), **Viewer** = `viewer` (group `stock_viewer`), **Admin** = `admin` (superuser). All data synthetic.
**Every flow starts from the seeded baseline** (`scripts/reset.sh`: Keyboard pk1 qty 10, Mouse pk2 qty 25, Monitor pk3 qty 0, all `delete_on_deplete=False`) — flows are independent and order-free; a flow that needs another value says so in its own precondition.
Each flow = one automated Playwright test in `tests/team/e2e/` (planned, Phase 7). "Baseline" column = predicted result on the unmodified upstream build (assumptions A-1/A-2 in `docs/TEST_BASIS.md`): **FAIL** means the test is expected to expose a defect on the baseline and to pass after the documented fix.
Ownership: M1 = 24I-3166 (UC-01, UC-02), M2 = 24I-3015 (UC-03, UC-04), M3 = 24I-3106 (UC-05, UC-06).

---
## UC-01 Add stock to an item (M1) — WF-A — FR-01, FR-02, FR-03, BR-1
Actor: Manager. Trigger: wants to record received units. Pre (all flows): logged in as manager, Keyboard qty 10, no prior history entries for the item. Post (main): qty 15 and one new `Stock added` history entry (added 5, resulting 15, user `manager`).
| ID | Flow | Steps | Expected | Baseline |
|---|---|---|---|---|
| UC01-MAIN | Main | Open Keyboard → Stock actions → Add stock → quantity 5 → Submit | Success message shown; item page shows 15; history has 1 add entry (5, 15) | PASS |
| UC01-AF1 | Alternative | Same, quantity 0.5 (decimal) | qty 10.5; history entry added 0.5 | PASS |
| UC01-AF2 | Alternative | Same, quantity 5 with notes "restock" | qty 15; history entry carries note "restock" | PASS |
| UC01-EF1 | Exception | quantity 0 | Error message shown, qty stays 10, **no** history entry | FAIL (A-2: upstream 201 silent no-op) |
| UC01-EF2 | Exception | quantity −3 | Error message shown, qty stays 10, no history entry | PASS |

## UC-02 Remove stock from an item (M1) — WF-B — FR-05, FR-06, FR-07, BR-1
Actor: Manager. Pre: logged in as manager, Keyboard qty 10.
| ID | Flow | Steps | Expected | Baseline |
|---|---|---|---|---|
| UC02-MAIN | Main | Stock actions → Remove stock → 4 → Submit | success; qty 6; history has 1 remove entry (4, 6) | PASS |
| UC02-AF1 | Alternative | remove 9 | qty 1; history (9, 1) | PASS |
| UC02-AF2 | Alternative | remove 4 with notes "damaged" | qty 6; history note "damaged" | PASS |
| UC02-EF1 | Exception | remove 11 (> 10) | **Rejected** with message naming the available quantity (10); qty stays 10; no history entry | FAIL (A-1: clamps to 0) |
| UC02-EF2 | Exception | quantity 0 | Error shown; qty stays 10; no history entry | FAIL (A-2) |
**Post (main):** qty 6, one `STOCK_REMOVE` history (audit) entry. **Post (EF):** qty and history unchanged.

## UC-03 Deplete an item (M2) — WF-B — FR-08, BR-3
Actor: Manager. Pre: logged in as manager, Mouse qty 25 and `delete_on_deplete=False` (seed).
| ID | Flow | Steps | Expected | Baseline |
|---|---|---|---|---|
| UC03-MAIN | Main | Remove 25 | Item page still exists with qty 0 and shown as out of stock; history has remove (25, 0) | PASS |
| UC03-AF1 | Alternative | Pre: set `delete_on_deplete=True` through the API (PATCH by manager) → remove 25 | Item no longer exists: item page 404, `GET /api/stock/2/` = 404 | PASS |
| UC03-AF2 | Alternative | Remove 24, then remove 1 | After 1st: qty 1 (still in stock); after 2nd: qty 0 | PASS |
| UC03-EF1 | Exception | Pre: Mouse qty 0 (after main) → remove 1 | No change: qty 0, no new history entry | PASS |
| UC03-EF2 | Exception | remove 26 (> 25) | Rejected; qty stays 25; no history entry | FAIL (A-1) |
**Post:** exactly as each flow's Expected column.

## UC-04 Restock a depleted item (M2) — WF-A and WF-B — BR-3, BR-1, FR-01
Actor: Manager. Pre: logged in as manager, Monitor pk3 qty 0 (retained).
| ID | Flow | Steps | Expected | Baseline |
|---|---|---|---|---|
| UC04-MAIN | Main | Add 8 | qty 8; item is in stock again | PASS |
| UC04-AF1 | Alternative | Add 8 then remove 3 (cross-workflow) | qty 5; history shows add (8) then remove (3) in that order | PASS |
| UC04-AF2 | Alternative | Add 8, then add 2 (repeated action) | qty 10; two add entries; no duplicate entry | PASS |
| UC04-EF1 | Exception | Add 10 000 000 000 (above the maximum representable value of the field) | Rejected; qty stays 0 | PASS |
| UC04-EF2 | Exception | Add 0.000001 (6 decimals) | Rejected; qty stays 0 | PASS |
Boundary value of the field (9 999 999 999.99999) is covered by BVA at API level.

## UC-05 Role-restricted adjustment (M3) — BR-4, FR-09
Pre: Keyboard qty 10.
| ID | Flow | Steps | Expected | Baseline |
|---|---|---|---|---|
| UC05-MAIN | Main | Viewer logs in, opens Keyboard | The page shows qty 10 and **no** "Stock actions" add/remove entries; qty still 10 | to confirm (Phase 7) |
| UC05-AF1 | Alternative | Manager adds 1 on the same item | qty 11 | PASS |
| UC05-AF2 | Alternative | Admin removes 1 | qty 9 | PASS |
| UC05-EF1 | Exception | Viewer `POST /api/stock/add/` pk1 qty 1 | HTTP 403; qty 10; no history entry | PASS |
| UC05-EF2 | Exception | Unauthenticated `POST /api/stock/remove/`; and `/web/stock/item/1` without login | API 401/403; UI redirected to login; qty 10 | PASS |

## UC-06 Correct a rejected removal (M3) — WF-B — FR-07, BR-1 (usability)
Actor: Manager. Pre: logged in as manager, Keyboard qty 10.
| ID | Flow | Steps | Expected | Baseline |
|---|---|---|---|---|
| UC06-MAIN | Main | Remove 15 → rejected → error text states the available quantity (10) → change to 10 → Submit | Error first; then success; qty 0 (item retained, out of stock); one history entry (10, 0) | FAIL (no rejection at 15) |
| UC06-AF1 | Alternative | After rejection correct to 5 | qty 5; one history entry | FAIL (same) |
| UC06-AF2 | Alternative | Same correction using the keyboard only (Tab order quantity → notes → Submit; Enter submits) | Focus order as stated; form submitted by keyboard; qty 0 | FAIL (same) |
| UC06-EF1 | Exception | After rejection, correct to 0 | Rejected again with message; qty 10 | FAIL (A-2) |
| UC06-EF2 | Exception | After rejection, enter text "abc" | Rejected; qty 10 | PASS |
Post: rejected attempts leave no history entries.
