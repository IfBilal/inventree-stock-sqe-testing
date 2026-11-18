// UC-02 Remove stock from an item (owner M1, 24I-3166) — WF-B — FR-05, FR-06, FR-07, BR-1.
import { test, expect } from '@playwright/test';
import { api, newItem, quantity, history, lastEntry, openItem, doOp, expectSuccess, expectRejected, expectBadge } from './helpers';

test.use({ storageState: 'e2e/.auth/manager.json' });

test('UC02-MAIN remove 4 from 10', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await doOp(page, 'Remove Stock', '4');
  await expectSuccess(page, 'Stock removed'); await expectBadge(page, 6);
  expect(await quantity(a, pk)).toBe(6);
  expect(await lastEntry(a, pk, 12)).toMatchObject({ delta: 4, from: 10, to: 6, actor: 'manager', count: 1 });
});

test('UC02-AF1 remove 9 from 10', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await doOp(page, 'Remove Stock', '9');
  await expectSuccess(page, 'Stock removed'); await expectBadge(page, 1);
  expect(await quantity(a, pk)).toBe(1);
  expect(await lastEntry(a, pk, 12)).toMatchObject({ delta: 9, from: 10, to: 1, actor: 'manager', count: 1 });
});

test('UC02-AF2 remove 4 with notes "damaged"', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await doOp(page, 'Remove Stock', '4', 'damaged');
  await expectSuccess(page, 'Stock removed'); await expectBadge(page, 6);
  expect(await quantity(a, pk)).toBe(6);
  expect(await lastEntry(a, pk, 12)).toMatchObject({ delta: 4, to: 6, notes: 'damaged', actor: 'manager', count: 1 });
});

test('UC02-EF1 removing 11 from 10 is rejected and names the available quantity', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await doOp(page, 'Remove Stock', '11');
  await expectRejected(page, /available quantity \(10\)/);                  // fixed by PR #13 (DEF-01)
  expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
});

test('UC02-EF2 quantity 0 is rejected', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await doOp(page, 'Remove Stock', '0');
  await expectRejected(page, /greater than zero/);
  expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
});
