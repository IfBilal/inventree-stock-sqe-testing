// Phase 8: full axe-core scan (@axe-core/playwright) of each use case's key screen, including the open Add/Remove dialogs.
// Measurement spec: it records every result to evidence/a11y/axe_<screen>_<phase>.json; it does not assert zero violations
// (the findings are analysed in docs/ACCESSIBILITY.md). The phase (before/after the fix) comes from A11Y_PHASE.
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs';
import { openItem, openOp } from './helpers';

const phase = process.env.A11Y_PHASE ?? 'before';
const out = '../../evidence/a11y';
fs.mkdirSync(out, { recursive: true });

async function scan(page: any, id: string) {
  const results = await new AxeBuilder({ page }).analyze();     // all rules (WCAG + best-practice), no restriction
  fs.writeFileSync(`${out}/axe_${id}_${phase}.json`, JSON.stringify({ url: results.url, violations: results.violations, passes: results.passes.length, incomplete: results.incomplete.length, inapplicable: results.inapplicable.length }, null, 1));
  return results;
}

test.describe('manager screens', () => {
  test.use({ storageState: 'e2e/.auth/manager.json' });
  test('axe S1 item details page (manager)', async ({ page }) => {
    await openItem(page, 1); await page.waitForTimeout(1500);
    const r = await scan(page, 'S1-item-details-manager');
    expect(r.passes.length).toBeGreaterThan(5);                  // the scan really ran
  });
  test('axe S1 with the Add Stock dialog open', async ({ page }) => {
    await openItem(page, 1); await openOp(page, 'Add Stock'); await page.waitForTimeout(800);
    const r = await scan(page, 'S1-add-stock-dialog');
    expect(r.passes.length).toBeGreaterThan(5);
  });
  test('axe S1 with the Remove Stock dialog open', async ({ page }) => {
    await openItem(page, 1); await openOp(page, 'Remove Stock'); await page.waitForTimeout(800);
    const r = await scan(page, 'S1-remove-stock-dialog');
    expect(r.passes.length).toBeGreaterThan(5);
  });
});

test.describe('viewer screens', () => {
  test.use({ storageState: 'e2e/.auth/viewer.json' });
  test('axe S2 item details page (viewer)', async ({ page }) => {
    await openItem(page, 1); await page.waitForTimeout(1500);
    const r = await scan(page, 'S2-item-details-viewer');
    expect(r.passes.length).toBeGreaterThan(5);
  });
});
