// PINS of the observed BASELINE behaviour of the DEF-02 flows that are marked `test.fail` elsewhere: an expected failure must fail for the intended
// reason (the UI reports success and nothing changes), not because of a missing selector or a server error. These tests are removed/inverted when DEF-02 is fixed.
import { test, expect } from '@playwright/test';
import { api, newItem, quantity, history, openItem, openOp, doOp, fillAndSubmit, toast } from './helpers';

test.use({ storageState: 'e2e/.auth/manager.json' });

test('PIN DEF-02 Add 0 reports success and changes nothing (UC01-EF1)', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk); await doOp(page, 'Add Stock', '0');
  await expect(toast(page).filter({ hasText: 'Stock added' })).toBeVisible();
  expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
});

test('PIN DEF-02 typed -3 is accepted by the field, reports success and changes nothing (UC01-EF2)', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk); await doOp(page, 'Add Stock', '-3');
  await expect(toast(page).filter({ hasText: 'Stock added' })).toBeVisible();
  expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
});

test('PIN DEF-02 Remove 0 reports success and changes nothing (UC02-EF2)', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk); await doOp(page, 'Remove Stock', '0');
  await expect(toast(page).filter({ hasText: 'Stock removed' })).toBeVisible();
  expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
});

test('PIN DEF-02 correcting a rejected value to 0 reports success and changes nothing (UC06-EF1)', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk); await openOp(page, 'Add Stock');
  await fillAndSubmit(page, '1.123456');
  await expect(page.getByRole('dialog').locator('.mantine-InputWrapper-error').first()).toBeVisible();
  await fillAndSubmit(page, '0');
  await expect(toast(page).filter({ hasText: 'Stock added' })).toBeVisible();
  expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
});
