import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  use: { baseURL: 'http://127.0.0.1:5173', browserName: 'chromium', trace: 'retain-on-failure' },
  workers: 1,
  retries: 0,
  webServer: {
    command: 'node scripts/dev.mjs',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: false,
    timeout: 60000,
  },
});
