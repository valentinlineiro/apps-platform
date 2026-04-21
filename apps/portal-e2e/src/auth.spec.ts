import { test, expect } from '@playwright/test';

test.describe('authentication', () => {
  test('unauthenticated visit redirects to Keycloak', async ({ browser }) => {
    const context = await browser.newContext({ ignoreHTTPSErrors: true });
    const page = await context.newPage();

    await page.goto('https://localhost');
    await page.waitForURL(/\/realms\/apps-platform\//, { timeout: 10000 });

    expect(page.url()).toContain('/realms/apps-platform/');
    await context.close();
  });

  test('authenticated visit lands on portal directory', async ({ page }) => {
    await page.goto('https://localhost');
    await expect(page.locator('app-shell-header, h1, main.layout')).toBeVisible();
  });
});
