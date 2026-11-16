// UC-01 Add stock to an item (owner M1, 24I-3166) — WF-A — FR-01, FR-02, FR-03, BR-1. One test per flow of docs/USE_CASES.md.
import { test, expect } from '@playwright/test';
import { api, newItem, quantity, history, openItem, doOp, expectSuccess, expectRejected, expectBadge, knownDefect } from './helpers';

test.use({ storageState: 'e2e/.auth/manager.json' });

test('UC01-MAIN add 5 to an item holding 10', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await doOp(page, 'Add Stock', '5');
  await expectSuccess(page, 'Stock added');
  await expectBadge(page, 15);                                              // result shown
  expect(await quantity(a, pk)).toBe(15);                                   // postconditions via API
  const h = await history(a, pk, 11);
  expect(h).toHaveLength(1); expect(h[0].deltas.added).toBe(5); expect(h[0].actor_username).toBe('manager');
});

test('UC01-AF1 add a decimal quantity 0.5', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await doOp(page, 'Add Stock', '0.5');
  await expectSuccess(page, 'Stock added'); await expectBadge(page, 10.5);
  expect(await quantity(a, pk)).toBe(10.5);
  expect((await history(a, pk, 11))[0].deltas.added).toBe(0.5);
});

test('UC01-AF2 add 5 with notes "restock"', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await doOp(page, 'Add Stock', '5', 'restock');
  await expectSuccess(page, 'Stock added'); await expectBadge(page, 15);
  expect((await history(a, pk, 11))[0].notes).toBe('restock');
});

test('UC01-EF1 quantity 0 is rejected', async ({ page }) => {
  knownDefect(test, 'DEF-02');
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await doOp(page, 'Add Stock', '0');
  await expectRejected(page);                                               // baseline: "Success — Stock added" (silent no-op)
  expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
});

test('UC01-EF2 typed quantity -3 is rejected', async ({ page }) => {
  knownDefect(test, 'DEF-02');
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await doOp(page, 'Add Stock', '-3');
  await expectRejected(page);                                               // baseline: the field accepts -3 and reports success
  expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
});
