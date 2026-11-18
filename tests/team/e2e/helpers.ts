import { APIRequestContext, Page, expect, request } from '@playwright/test';

const BASE = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8000';
const basic = (u: string, p: string) => 'Basic ' + Buffer.from(`${u}:${p}`).toString('base64');

/** API client with Basic auth (used to PREPARE state and to READ BACK postconditions independently of the UI). */
export async function api(user = 'admin', password = `${user}12345`): Promise<APIRequestContext> {
  return request.newContext({ baseURL: BASE, extraHTTPHeaders: { Authorization: basic(user, password) } });
}

/** Create a fresh stock item of the seeded 'Keyboard' part and return its pk (tests are independent and order-free). */
export async function newItem(a: APIRequestContext, quantity: number | string, extra: Record<string, unknown> = {}): Promise<number> {
  const r = await a.post('/api/stock/', { data: { part: 1, location: 1, quantity: String(quantity), delete_on_deplete: false, ...extra } });
  expect(r.status(), await r.text()).toBe(201);
  const body = await r.json();
  return (Array.isArray(body) ? body[0] : body).pk;
}

export async function quantity(a: APIRequestContext, pk: number): Promise<number | null> {
  const r = await a.get(`/api/stock/${pk}/`);
  if (r.status() === 404) return null;
  expect(r.status()).toBe(200);
  return Number((await r.json()).quantity);
}

/** History entries (audit log) of ONE item; the audit endpoint ignores the object_pk filter (W-06) so filter client-side. */
export async function history(a: APIRequestContext, pk: number, eventType?: 11 | 12) {
  const types = eventType ? [eventType] : [11, 12];
  const out: any[] = [];
  for (const t of types) {
    let url: string | null = `/api/audit/?model_type=stock.stockitem&event_type=${t}&limit=1000`;
    while (url) {
      const r = await a.get(url);
      const d = await r.json();
      out.push(...d.results.filter((e: any) => String(e.object_pk) === String(pk)));
      url = d.next ? d.next.replace(BASE, '') : null;
    }
  }
  return out;
}

export async function openItem(page: Page, pk: number) {
  await page.goto(`/web/stock/item/${pk}/details`);
  await expect(page.getByText('Stock Details').first()).toBeVisible();
}

export type Op = 'Add Stock' | 'Remove Stock';

/** Open the Stock Operations menu and the dialog; returns the dialog locator. */
export async function openOp(page: Page, op: Op) {
  await page.getByLabel('action-menu-stock-operations').click();
  await page.getByText(op, { exact: true }).click();
  const dlg = page.getByRole('dialog');
  await expect(dlg).toBeVisible();
  return dlg;
}

/** Fill quantity (typed like a user) and optional notes, then press Submit. */
export async function fillAndSubmit(page: Page, value: string, notes?: string) {
  const q = page.getByLabel('number-field-quantity');
  await q.fill('');
  await q.pressSequentially(value);
  if (notes) await page.getByLabel('text-field-notes').fill(notes);
  await page.getByRole('button', { name: 'Submit' }).click();
}

export async function doOp(page: Page, op: Op, value: string, notes?: string) {
  await openOp(page, op);
  await fillAndSubmit(page, value, notes);
}

/** The "Quantity: N" badge in the page header. */
export function quantityBadge(page: Page) {
  return page.getByText(/^quantity:/i).first();
}

/** Toast notifications of the UI. */
export function toast(page: Page) {
  return page.locator('.mantine-Notification-root');
}

/** Assert the dialog stayed open and shows the validation error ON THE QUANTITY FIELD (the real error element, not any text); no success toast appears. */
export async function expectRejected(page: Page, message?: RegExp | string) {
  const dlg = page.getByRole('dialog');
  await expect(dlg).toBeVisible();
  const err = dlg.locator('.mantine-InputWrapper-error').first();
  await expect(err).toBeVisible();
  if (message) await expect(err).toContainText(message);
  await page.waitForTimeout(600);                                            // give a (wrong) success toast time to appear before asserting it did not
  await expect(toast(page).filter({ hasText: /^Success/ })).toHaveCount(0);
}

/** Assert success: the dialog closes and the confirmation toast is shown. */
export async function expectSuccess(page: Page, what: 'Stock added' | 'Stock removed') {
  await expect(toast(page).filter({ hasText: what })).toBeVisible();
  await expect(page.getByRole('dialog')).toHaveCount(0);
}

export async function expectBadge(page: Page, n: number | string) {
  const txt = String(n).replace('.', '\\.');
  await expect(page.getByText(new RegExp(`^quantity:\\s*${txt}$`, 'i')).first()).toBeVisible();
}

/** Newest history entry of one event type with its decoded facts: delta, quantity before/after, notes, actor. */
export async function lastEntry(a: APIRequestContext, pk: number, type: 11 | 12) {
  const h = (await history(a, pk, type)).sort((x: any, y: any) => y.pk - x.pk);
  expect(h.length).toBeGreaterThan(0);
  const e = h[0];
  const q = e.changes?.quantity ?? [null, null];
  return { delta: e.deltas?.added ?? e.deltas?.removed, from: Number(q[0]), to: Number(q[1]), notes: e.notes, actor: e.actor_username, count: h.length };
}

export async function inStock(a: APIRequestContext, pk: number): Promise<boolean | null> {
  const r = await a.get(`/api/stock/${pk}/`);
  return r.status() === 200 ? Boolean((await r.json()).in_stock) : null;
}
