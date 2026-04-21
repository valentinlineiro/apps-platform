import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './apps/portal-e2e/src',
  globalSetup: './apps/portal-e2e/src/global-setup.ts',
  testMatch: '**/*.spec.ts',
  fullyParallel: false,
  forbidOnly: !!process.env['CI'],
  retries: process.env['CI'] ? 1 : 0,
  workers: 1,
  reporter: process.env['CI'] ? 'github' : 'list',
  outputDir: 'test-results/',

  use: {
    baseURL: 'https://localhost',
    ignoreHTTPSErrors: true,
    storageState: '.auth/user.json',
    trace: 'on-first-retry',
    navigationTimeout: 20000,
    actionTimeout: 10000,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
