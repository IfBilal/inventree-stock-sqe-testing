# Generator diff

Before: 223 cases · After: 223 cases

| Case id | Before (value → expected) | After (value → expected) |
|---|---|---|
| stockAdd:items:BVA:minitems-above | `2 item(s)` → valid | `3 item(s)` → valid |
| stockAdd:items:BVA:minitems-at | `1 item(s)` → valid | `2 item(s)` → valid |
| stockAdd:items:BVA:minitems-below | `0 item(s)` → invalid | `1 item(s)` → invalid |
| stockAdd:items[].quantity:BVA:min-at | `0` → invalid | `0` → valid |
| stockRemove:items:BVA:minitems-above | `2 item(s)` → valid | `3 item(s)` → valid |
| stockRemove:items:BVA:minitems-at | `1 item(s)` → valid | `2 item(s)` → valid |
| stockRemove:items:BVA:minitems-below | `0 item(s)` → invalid | `1 item(s)` → invalid |
| stockRemove:items[].quantity:BVA:min-at | `0` → invalid | `0` → valid |

**8 cases changed.**
