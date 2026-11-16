// UC-05 Role-restricted adjustment (owner M3, 24I-3106) — BR-4, FR-09. Access matrix: see also access.spec.ts (Phase 9).
import { test, expect, request } from '@playwright/test';
import { api, newItem, quantity, history, openItem, doOp, expectSuccess, expectBadge } from './helpers';

test.describe('viewer', () => {
  test.use({ storageState: 'e2e/.auth/viewer.json' });
  test('UC05-MAIN the viewer sees the quantity but has no Stock Operations menu', async ({ page }) => {
    const a = await api(); const pk = await newItem(a, 10);
    await openItem(page, pk);
    await expectBadge(page, 10);
    await expect(page.getByLabel('action-menu-stock-operations')).toHaveCount(0);
    expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
  });
});

test.describe('manager', () => {
  test.use({ storageState: 'e2e/.auth/manager.json' });
  test('UC05-AF1 the manager adds 1 to the same kind of item', async ({ page }) => {
    const a = await api(); const pk = await newItem(a, 10);
    await openItem(page, pk);
    await doOp(page, 'Add Stock', '1'); await expectSuccess(page, 'Stock added'); await expectBadge(page, 11);
    expect(await quantity(a, pk)).toBe(11);
  });
});

test.describe('admin', () => {
  test.use({ storageState: 'e2e/.auth/admin.json' });
  test('UC05-AF2 the admin (superuser) removes 1', async ({ page }) => {
    const a = await api(); const pk = await newItem(a, 10);
    await openItem(page, pk);
    await doOp(page, 'Remove Stock', '1'); await expectSuccess(page, 'Stock removed'); await expectBadge(page, 9);
    expect(await quantity(a, pk)).toBe(9);
  });
});

test('UC05-EF1 the viewer calling the add API directly gets 403 and nothing changes', async () => {
  const a = await api(); const pk = await newItem(a, 10);
  const v = await api('viewer');
  const r = await v.post('/api/stock/add/', { data: { items: [{ pk, quantity: '1' }] } });
  expect(r.status()).toBe(403);
  expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0);
});

test('UC05-EF2 an anonymous user gets 401 on the API and is redirected to the login page in the UI', async ({ page }) => {
  const a = await api(); const pk = await newItem(a, 10);
  const anon = await request.newContext({ baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8000' });
  const r = await anon.post('/api/stock/remove/', { data: { items: [{ pk, quantity: '1' }] } });
  expect(r.status()).toBe(401);
  await page.context().clearCookies();
  await page.goto(`/web/stock/item/${pk}/details`);
  await expect(page).toHaveURL(/\/web\/login/);
  expect(await quantity(a, pk)).toBe(10);
});
