// Phase 9: access matrix of the two workflows verified with Playwright (R-41): role x action, expected vs observed, evidence.
// Routes/data: GET /api/stock/{id}/ (read), POST /api/stock/add|remove/ (WF-A/B), PATCH|DELETE /api/stock/{id}/ (change/delete rights),
// audit read. Records every decision to evidence/security/access_matrix_results.json.
import { test, expect, request } from '@playwright/test';
import fs from 'node:fs';
import { api, newItem, quantity, history, openItem } from './helpers';

const OUT = '../../evidence/security/access_matrix_results.json';
type Row = { role: string; action: string; route: string; expected: number | string; observed: number | string; ok: boolean; evidence: string };
const rows: Row[] = [];
const BASE = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8000';

async function client(role: string) {
  if (role === 'anonymous') return request.newContext({ baseURL: BASE });
  return api(role);
}
function record(r: Omit<Row, 'ok'>) { rows.push({ ...r, ok: r.expected === r.observed, decision: (typeof r.expected === 'number' && r.expected < 400) || r.expected === 1 ? 'ALLOWED' : 'DENIED' } as any); }

const MATRIX: { role: string; action: string; route: string; call: (c: any, pk: number) => Promise<any>; expected: number; verify?: (a: any, pk: number) => Promise<string> }[] = [];   // expected: 2xx = ALLOWED, 401/403 = DENIED
for (const [role, view, add, remove, patch, del] of [['manager', 200, 201, 201, 200, 204], ['viewer', 200, 403, 403, 403, 403], ['anonymous', 401, 401, 401, 401, 401]] as const) {
  MATRIX.push({ role, action: 'view item', route: 'GET /api/stock/{id}/', call: (c, pk) => c.get(`/api/stock/${pk}/`), expected: view });
  MATRIX.push({ role, action: 'add stock (WF-A)', route: 'POST /api/stock/add/', call: (c, pk) => c.post('/api/stock/add/', { data: { items: [{ pk, quantity: '1' }] } }), expected: add,
    verify: async (a, pk) => `quantity after = ${await quantity(a, pk)}` });
  MATRIX.push({ role, action: 'remove stock (WF-B)', route: 'POST /api/stock/remove/', call: (c, pk) => c.post('/api/stock/remove/', { data: { items: [{ pk, quantity: '1' }] } }), expected: remove,
    verify: async (a, pk) => `quantity after = ${await quantity(a, pk)}` });
  MATRIX.push({ role, action: 'edit item (change right)', route: 'PATCH /api/stock/{id}/', call: (c, pk) => c.patch(`/api/stock/${pk}/`, { data: { batch: 'X' } }), expected: patch });
  MATRIX.push({ role, action: 'delete item (delete right)', route: 'DELETE /api/stock/{id}/', call: (c, pk) => c.delete(`/api/stock/${pk}/`), expected: del });
  MATRIX.push({ role, action: 'read history (audit)', route: 'GET /api/audit/', call: (c) => c.get('/api/audit/?model_type=stock.stockitem&limit=1'), expected: view });
}

test.describe.configure({ mode: 'serial' });
for (const m of MATRIX) {
  test(`access: ${m.role} / ${m.action} -> ${m.expected}`, async () => {
    const a = await api(); const pk = await newItem(a, 10);
    const c = await client(m.role);
    const r = await m.call(c, pk);
    const observed = r.status();
    const ev = m.verify ? await m.verify(a, pk) : '';
    record({ role: m.role, action: m.action, route: m.route, expected: m.expected, observed, evidence: `HTTP ${observed}${ev ? '; ' + ev : ''}; item pk ${pk}` });
    expect(observed).toBe(m.expected);
    if (m.expected >= 400 && /^(add|remove) stock/.test(m.action)) { expect(await quantity(a, pk)).toBe(10); expect(await history(a, pk)).toHaveLength(0); }   // denied => no side effect
  });
}

test.describe('UI decisions', () => {
  test.describe('viewer', () => {
    test.use({ storageState: 'e2e/.auth/viewer.json' });
    test('access: viewer UI offers no stock operations (denied)', async ({ page }) => {
      const a = await api(); const pk = await newItem(a, 10);
      await openItem(page, pk);
      const n = await page.getByLabel('action-menu-stock-operations').count();
      record({ role: 'viewer', action: 'stock operations menu in the UI', route: '/web/stock/item/{id}/details', expected: 0, observed: n, evidence: `menu elements = ${n}; item pk ${pk}` });
      expect(n).toBe(0);
    });
  });
  test.describe('manager', () => {
    test.use({ storageState: 'e2e/.auth/manager.json' });
    test('access: manager UI offers stock operations (allowed)', async ({ page }) => {
      const a = await api(); const pk = await newItem(a, 10);
      await openItem(page, pk);
      const n = await page.getByLabel('action-menu-stock-operations').count();
      record({ role: 'manager', action: 'stock operations menu in the UI', route: '/web/stock/item/{id}/details', expected: 1, observed: n, evidence: `menu elements = ${n}; item pk ${pk}` });
      expect(n).toBe(1);
    });
  });
});

test.afterAll(async () => {
  fs.mkdirSync('../../evidence/security', { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(rows, null, 1));
});
