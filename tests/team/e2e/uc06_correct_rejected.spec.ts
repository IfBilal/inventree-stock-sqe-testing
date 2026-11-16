// UC-06 Correct a rejected adjustment (owner M3, 24I-3106) — WF-A and WF-B — usability: errors explain what to correct; keyboard operation.
import { test, expect } from '@playwright/test';
import { api, newItem, quantity, history, lastEntry, openItem, openOp, fillAndSubmit, expectSuccess, expectRejected, expectBadge, knownDefect } from './helpers';

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
  expect(await lastEntry(a, pk, 11)).toMatchObject({ delta: 1.12345, from: 10, count: 1 });   // exactly one entry: the rejected attempt left none
});

test('UC06-AF1 remove 15 from 10 -> rejected naming the available quantity -> 10 -> success', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await openOp(page, 'Remove Stock');
  await fillAndSubmit(page, '15');
  await expectRejected(page, /available quantity \(10\)/);
  expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
  await fillAndSubmit(page, '10');
  await expectSuccess(page, 'Stock removed'); await expectBadge(page, 0);
  expect(await quantity(a, pk)).toBe(0); expect(await history(a, pk, 12)).toHaveLength(1);
});

test('UC06-AF2 keyboard only: Tab order quantity -> ... -> notes -> Cancel -> Submit; the keyboard submits the form', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  await openItem(page, pk);
  await openOp(page, 'Add Stock');
  const label = () => page.evaluate(() => { const e = document.activeElement as HTMLElement; return (e.getAttribute('aria-label') || e.innerText || e.tagName).trim(); });
  // From the moment the dialog opens (focus is on the modal's close button) the Tab key must reach the required field, the notes field and the Submit button in this exact order
  const seq: string[] = [];
  for (let i = 0; i < 10; i++) { await page.keyboard.press('Tab'); seq.push(await label()); if (seq[seq.length - 1] === 'Submit') break; }
  expect(seq).toEqual(['number-field-quantity', 'action-button-change-status', 'action-button-remove-this-row', 'text-field-notes', 'Cancel', 'Submit']);
  // Back to the quantity field with the keyboard (the focus trap wraps: Submit -> close -> quantity), type a value
  await page.keyboard.press('Tab'); await page.keyboard.press('Tab');
  expect(await label()).toBe('number-field-quantity');
  await page.keyboard.type('2');
  // UX-01 (documented behaviour): Enter inside the quantity field does NOT submit the dialog
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible(); expect(await quantity(a, pk)).toBe(10);
  // ...but the keyboard CAN submit: Tab to the Submit button and press Enter
  for (let i = 0; i < 10 && (await label()) !== 'Submit'; i++) await page.keyboard.press('Tab');
  expect(await label()).toBe('Submit');
  await page.keyboard.press('Enter');
  await expectSuccess(page, 'Stock added'); await expectBadge(page, 12);
  expect(await quantity(a, pk)).toBe(12);
  expect(await lastEntry(a, pk, 11)).toMatchObject({ delta: 2, from: 10, to: 12, actor: 'manager', count: 1 });
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
