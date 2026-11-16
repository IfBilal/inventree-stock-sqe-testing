// UC-03 Deplete an item (owner M2, 24I-3015) — WF-B — FR-08, BR-3.
import { test, expect } from '@playwright/test';
import { api, newItem, quantity, history, openItem, openOp, doOp, expectSuccess, expectRejected, expectBadge, knownDefect } from './helpers';

test.use({ storageState: 'e2e/.auth/manager.json' });

test('UC03-MAIN removing all 25 retains the item at 0 (delete_on_deplete=false)', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 25);
  await openItem(page, pk);
  await doOp(page, 'Remove Stock', '25');
  await expectSuccess(page, 'Stock removed'); await expectBadge(page, 0);
  expect(await quantity(a, pk)).toBe(0);
  const h = await history(a, pk, 12); expect(h).toHaveLength(1); expect(h[0].deltas.removed).toBe(25);
});

test('UC03-AF1 with delete_on_deplete=true the item disappears', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 25, { delete_on_deplete: true });
  await openItem(page, pk);
  await doOp(page, 'Remove Stock', '25');
  await expectSuccess(page, 'Stock removed');
  expect(await quantity(a, pk)).toBeNull();                                  // GET -> 404
  expect(await history(a, pk, 12)).toHaveLength(1);                          // history survives deletion
  await page.goto(`/web/stock/item/${pk}/details`);
  await expect(page.getByText('Stock Details')).toHaveCount(0);              // item page no longer renders
});

test('UC03-AF2 remove 24 then 1: depleted only after the second', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 25);
  await openItem(page, pk);
  await doOp(page, 'Remove Stock', '24'); await expectSuccess(page, 'Stock removed'); await expectBadge(page, 1);
  expect(await quantity(a, pk)).toBe(1);
  await doOp(page, 'Remove Stock', '1'); await expect(page.locator('.mantine-Notification-root').filter({ hasText: 'Stock removed' }).first()).toBeVisible();
  await expectBadge(page, 0); expect(await quantity(a, pk)).toBe(0);
  expect(await history(a, pk, 12)).toHaveLength(2);
});

test('UC03-EF1 an already depleted item offers nothing to remove and nothing changes', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 0);
  await openItem(page, pk);
  const dlg = await openOp(page, 'Remove Stock');
  await expect(dlg.getByText('No entries available')).toBeVisible();          // the UI excludes out-of-stock items from the dialog
  await expect(page.getByLabel('number-field-quantity')).toHaveCount(0);
  expect(await quantity(a, pk)).toBe(0); expect(await history(a, pk)).toHaveLength(0);   // no change, no history entry
});

test('UC03-EF2 removing 26 from 25 is rejected', async ({ page }) => {
  knownDefect(test, 'DEF-01');
  const a = await api(); const pk = await newItem(a, 25);
  await openItem(page, pk);
  await doOp(page, 'Remove Stock', '26');
  await expectRejected(page);
  expect(await quantity(a, pk)).toBe(25); expect(await history(a, pk)).toHaveLength(0);
});
