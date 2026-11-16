// Lighthouse (accessibility, best-practices, SEO) on each use case's key screen WHILE LOGGED IN.
// A Playwright Chromium is launched with a DevTools port, logged in as the role, and Lighthouse attaches to it (storage is not reset).
// Usage: node a11y/lighthouse_run.mjs <phase: before|after> [baseUrl]
import { chromium } from '@playwright/test';
import lighthouse from 'lighthouse';
import fs from 'node:fs';
import path from 'node:path';

const phase = process.argv[2] ?? 'before';
const base = process.argv[3] ?? 'http://127.0.0.1:8000';
const out = path.resolve('../../evidence/a11y');
const PORT = 9333;
const SCREENS = [
  { id: 'S1-item-details-manager', role: ['manager', 'manager12345'], url: '/web/stock/item/1/details', usecases: 'UC-01..UC-04, UC-06 (add/remove/deplete/restock/correct)' },
  { id: 'S2-item-details-viewer', role: ['viewer', 'viewer12345'], url: '/web/stock/item/1/details', usecases: 'UC-05 (role-restricted view)' },
];
fs.mkdirSync(out, { recursive: true });
const summary = [];
for (const s of SCREENS) {
  const ctx = await chromium.launchPersistentContext(`/tmp/lh-profile-${s.id}-${Date.now()}`, { headless: true, args: [`--remote-debugging-port=${PORT}`], viewport: { width: 1400, height: 1000 } });
  const page = await ctx.newPage();
  await page.goto(base + '/web/login'); await page.waitForLoadState('networkidle');
  await page.getByPlaceholder('Your username').fill(s.role[0]); await page.getByPlaceholder('Your password').fill(s.role[1]);
  await page.getByRole('button', { name: 'Log In' }).click();
  try { await page.waitForURL(/\/web\/(home|dashboard)/, { timeout: 8000 }); } catch { await page.getByRole('button', { name: 'Log In' }).click(); await page.waitForURL(/\/web\/(home|dashboard)/, { timeout: 20000 }); }  // DEF-05 workaround
  await page.goto(base + s.url); await page.waitForLoadState('networkidle'); await page.waitForTimeout(2500);
  const result = await lighthouse(base + s.url, { port: PORT, output: 'json', logLevel: 'error', onlyCategories: ['accessibility', 'best-practices', 'seo'], disableStorageReset: true },
    { extends: 'lighthouse:default', settings: { formFactor: 'desktop', screenEmulation: { disabled: true }, throttlingMethod: 'provided', maxWaitForLoad: 60000, disableStorageReset: true, onlyCategories: ['accessibility', 'best-practices', 'seo'] } });
  const lhr = result.lhr;
  fs.writeFileSync(path.join(out, `lighthouse_${s.id}_${phase}.json`), JSON.stringify(lhr, null, 1));
  const sc = Object.fromEntries(Object.entries(lhr.categories).map(([k, v]) => [k, Math.round(v.score * 100)]));
  const failed = Object.values(lhr.audits).filter(a => a.score !== null && a.score < 1 && a.scoreDisplayMode !== 'informative' && a.scoreDisplayMode !== 'notApplicable').map(a => a.id);
  summary.push({ screen: s.id, finalUrl: lhr.finalDisplayedUrl, scores: sc, failedAudits: failed });
  console.log(s.id, JSON.stringify(sc), 'failed audits:', failed.join(', '));
  await ctx.close();
}
fs.writeFileSync(path.join(out, `lighthouse_summary_${phase}.json`), JSON.stringify(summary, null, 1));
