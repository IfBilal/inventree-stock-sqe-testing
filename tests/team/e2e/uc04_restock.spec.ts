// UC-04 Restock a depleted item (owner M2, 24I-3015) — WF-A and WF-B — BR-3, BR-1, FR-01.
import { test, expect } from '@playwright/test';
import { api, newItem, quantity, history, lastEntry, inStock, openItem, doOp, expectSuccess, expectRejected, expectBadge } from './helpers';

test.use({ storageState: 'e2e/.auth/manager.json' });

test('UC04-MAIN add 8 to a depleted item', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 0);
  await openItem(page, pk);
  await doOp(page, 'Add Stock', '8');
  await expectSuccess(page, 'Stock added'); await expectBadge(page, 8);
  expect(await quantity(a, pk)).toBe(8);
  expect(await inStock(a, pk)).toBe(true);                                   // in stock again
  expect(await lastEntry(a, pk, 11)).toMatchObject({ delta: 8, from: 0, to: 8, actor: 'manager', count: 1 });
});

test('UC04-AF1 add 8 then remove 3 (cross-workflow) reads back 5 and ordered history', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 0);
  await openItem(page, pk);
  await doOp(page, 'Add Stock', '8'); await expectSuccess(page, 'Stock added'); await expectBadge(page, 8);
  await doOp(page, 'Remove Stock', '3'); await expect(page.locator('.mantine-Notification-root').filter({ hasText: 'Stock removed' }).first()).toBeVisible();
  await expectBadge(page, 5);
  expect(await quantity(a, pk)).toBe(5);
  const h = (await history(a, pk)).sort((x, y) => x.pk - y.pk);
  expect(h.map((e: any) => e.event_type)).toEqual([11, 12]);
  expect(h.map((e: any) => [e.deltas.added ?? e.deltas.removed, Number(e.changes.quantity[0]), Number(e.changes.quantity[1])])).toEqual([[8, 0, 8], [3, 8, 5]]);   // (8) then (3), with the balances
});

test('UC04-AF2 add 8 then add 2 (repeated action) gives 10 with two add entries', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 0);
  await openItem(page, pk);
  await doOp(page, 'Add Stock', '8'); await expectBadge(page, 8);
  await doOp(page, 'Add Stock', '2'); await expectBadge(page, 10);
  expect(await quantity(a, pk)).toBe(10);
  expect(await history(a, pk, 11)).toHaveLength(2);                          // no duplicate entry
});

test('UC04-EF1 adding 10 000 000 000 (above the maximum) is rejected', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 0);
  await openItem(page, pk);
  await doOp(page, 'Add Stock', '10000000000');
  await expectRejected(page, /no more than 10 digits before the decimal point/i);
  expect(await quantity(a, pk)).toBe(0); expect(await history(a, pk)).toHaveLength(0);
});

test('UC04-EF2 adding 0.000001 (6 decimals) is rejected', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 0);
  await openItem(page, pk);
  await doOp(page, 'Add Stock', '0.000001');
  await expectRejected(page, /no more than 5 decimal places/i);
  expect(await quantity(a, pk)).toBe(0); expect(await history(a, pk)).toHaveLength(0);
});
