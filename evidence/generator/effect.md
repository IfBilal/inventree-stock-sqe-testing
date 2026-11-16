# Generator diff

Before: 103 cases · After: 103 cases

| Case id | Before (value → expected) | After (value → expected) |
|---|---|---|
| stockAdd:items[].quantity:BVA:max-above | `10000000000.00000` → invalid | `1000.00001` → invalid |
| stockAdd:items[].quantity:BVA:max-at | `9999999999.99999` → valid | `1000` → valid |
| stockAdd:items[].quantity:BVA:max-below | `9999999999.99998` → valid | `999.99999` → valid |
| stockAdd:items[].quantity:EP:above-range | `10000000000.99999` → invalid | `1001` → invalid |
| stockAdd:notes:BVA:maxlen-above | `aaaaaaaaaaaa…(513 chars)` → invalid | `aaaaaaaaaaaa…(101 chars)` → invalid |
| stockAdd:notes:BVA:maxlen-at | `aaaaaaaaaaaa…(512 chars)` → valid | `aaaaaaaaaaaa…(100 chars)` → valid |
| stockAdd:notes:BVA:maxlen-below | `aaaaaaaaaaaa…(511 chars)` → valid | `aaaaaaaaaaaa…(99 chars)` → valid |
| stockRemove:items[].quantity:BVA:max-above | `10000000000.00000` → invalid | `1000.00001` → invalid |
| stockRemove:items[].quantity:BVA:max-at | `9999999999.99999` → valid | `1000` → valid |
| stockRemove:items[].quantity:BVA:max-below | `9999999999.99998` → valid | `999.99999` → valid |
| stockRemove:items[].quantity:EP:above-range | `10000000000.99999` → invalid | `1001` → invalid |
| stockRemove:notes:BVA:maxlen-above | `aaaaaaaaaaaa…(513 chars)` → invalid | `aaaaaaaaaaaa…(101 chars)` → invalid |
| stockRemove:notes:BVA:maxlen-at | `aaaaaaaaaaaa…(512 chars)` → valid | `aaaaaaaaaaaa…(100 chars)` → valid |
| stockRemove:notes:BVA:maxlen-below | `aaaaaaaaaaaa…(511 chars)` → valid | `aaaaaaaaaaaa…(99 chars)` → valid |

**14 cases changed.**
