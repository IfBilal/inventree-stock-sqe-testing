import { defineConfig } from '@playwright/test';

// Browser end-to-end, usability and accessibility tests (Phases 7-8). The server must be running (scripts/test_e2e.sh resets and starts it).
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { outputFolder: '../../reports/playwright-html', open: 'never' }], ['json', { outputFile: '../../reports/playwright-report.json' }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    headless: true,
    viewport: { width: 1400, height: 1000 },
    // Optional passive-security scan: route the browser through OWASP ZAP (E2E_PROXY=http://127.0.0.1:8090). Loopback must be explicitly proxied in Chromium.
    ...(process.env.E2E_PROXY ? { launchOptions: { proxy: { server: process.env.E2E_PROXY }, args: ['--proxy-bypass-list=<-loopback>'] } } : {}),
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    { name: 'chromium', use: { browserName: 'chromium' }, dependencies: ['setup'], testIgnore: /auth\.setup\.ts/ },
  ],
});
