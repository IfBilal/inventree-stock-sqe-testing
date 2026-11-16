import { test as setup, expect } from '@playwright/test';

// Log in once per role and keep the session (storage state) for the specs.
// KNOWN DEFECT DEF-05 (GitHub issue #5): the FIRST login after a server (re)start silently fails (POST login 200, then GET /api/user/me 401,
// the page stays on /web/login). The second click works. The workaround below is visible (test annotation) and a second failure fails the setup.
for (const [role, password] of [['manager', 'manager12345'], ['viewer', 'viewer12345'], ['admin', 'admin12345']] as const) {
  setup(`authenticate ${role}`, async ({ page }) => {
    await page.goto('/web/login');
    await page.waitForLoadState('networkidle');                       // the SPA must be fully loaded before the form is used
    await expect(page.getByPlaceholder('Your username')).toBeVisible();
    await page.getByPlaceholder('Your username').fill(role);
    await page.getByPlaceholder('Your password').fill(password);
    await page.getByRole('button', { name: 'Log In' }).click();
    try {
      await expect(page).toHaveURL(/\/web\/(home|dashboard)/, { timeout: 8_000 });
    } catch {
      setup.info().annotations.push({ type: 'DEF-05', description: 'first login attempt after server start did not complete; clicked Log In again' });
      await page.getByRole('button', { name: 'Log In' }).click();
      await expect(page).toHaveURL(/\/web\/(home|dashboard)/, { timeout: 20_000 });
    }
    await page.context().storageState({ path: `e2e/.auth/${role}.json` });
  });
}
