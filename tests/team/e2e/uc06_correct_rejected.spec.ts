// UC-06 Correct a rejected adjustment (owner M3, 24I-3106) — WF-A and WF-B — usability: errors explain what to correct; keyboard operation.
import { test, expect } from '@playwright/test';
import { api, newItem, quantity, history, openItem, openOp, fillAndSubmit, expectSuccess, expectRejected, expectBadge, knownDefect } from './helpers';

test.use({ storageState: 'e2e/.auth/manager.json' });

test('UC06-MAIN add 1.123456 -> error says what to correct -> 1.12345 -> success', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await openOp(page, 'Add Stock');
  await fillAndSubmit(page, '1.123456');
  await expectRejected(page, /no more than 5 decimal places/i);              // the message explains WHAT to correct
  expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
  await fillAndSubmit(page, '1.12345');                                      // correct the value in the same dialog
  await expectSuccess(page, 'Stock added'); await expectBadge(page, 11.12345);
  expect(await quantity(a, pk)).toBeCloseTo(11.12345, 5);
  expect(await history(a, pk, 11)).toHaveLength(1);
});

test('UC06-AF1 remove 15 from 10 -> rejected naming the available quantity -> 10 -> success', async ({ page }) => {
  knownDefect(test, 'DEF-01');
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await openOp(page, 'Remove Stock');
  await fillAndSubmit(page, '15');
  await expectRejected(page, /10/);
  expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
  await fillAndSubmit(page, '10');
  await expectSuccess(page, 'Stock removed'); await expectBadge(page, 0);
  expect(await quantity(a, pk)).toBe(0); expect(await history(a, pk, 12)).toHaveLength(1);
});

test('UC06-AF2 keyboard only: focus order quantity -> notes -> Submit; the keyboard submits the form', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await openOp(page, 'Add Stock');
  const label = () => page.evaluate(() => { const e = document.activeElement as HTMLElement; return (e.getAttribute('aria-label') || e.innerText || e.tagName).trim(); });
  await page.getByLabel('number-field-quantity').focus();
  const seen: string[] = [await label()];
  for (let i = 0; i < 10 && !seen.includes('Submit'); i++) { await page.keyboard.press('Tab'); seen.push(await label()); }
  const iq = seen.indexOf('number-field-quantity'), inn = seen.indexOf('text-field-notes'), isub = seen.indexOf('Submit');
  expect(iq).toBe(0); expect(inn).toBeGreaterThan(iq); expect(isub).toBeGreaterThan(inn);   // required field, notes and submit button in the expected order
  // UX-01 (documented behaviour): Enter inside the quantity field does NOT submit the dialog
  const q = page.getByLabel('number-field-quantity');
  await q.fill(''); await q.pressSequentially('2'); await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible(); expect(await quantity(a, pk)).toBe(10);
  // ...but the keyboard CAN submit: Tab to the Submit button and press Enter
  for (let i = 0; i < 10 && (await label()) !== 'Submit'; i++) await page.keyboard.press('Tab');
  expect(await label()).toBe('Submit');
  await page.keyboard.press('Enter');
  await expectSuccess(page, 'Stock added'); await expectBadge(page, 12);
  expect(await quantity(a, pk)).toBe(12);
});

test('UC06-EF1 after a rejection, correcting to 0 is rejected again', async ({ page }) => {
  knownDefect(test, 'DEF-02');
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await openOp(page, 'Add Stock');
  await fillAndSubmit(page, '1.123456'); await expectRejected(page);
  await fillAndSubmit(page, '0');
  await expectRejected(page);                                                // baseline: success + silent no-op
  expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
});

test('UC06-EF2 after a rejection, text is rejected with "A valid number is required."', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await openOp(page, 'Add Stock');
  await fillAndSubmit(page, '1.123456'); await expectRejected(page);
  await fillAndSubmit(page, 'abc');
  await expectRejected(page, /valid number is required/i);
  expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
});
