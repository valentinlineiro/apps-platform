import { test, expect } from '@playwright/test';

test.describe('authentication', () => {
  test('unauthenticated visit redirects to Keycloak', async ({ browser }) => {
    // Create a context with no storage state so there are no session cookies.
    // Navigate directly to /auth/login (server-side 302 → Keycloak) rather than
    // relying on Angular's async JS redirect, which is harder to time reliably.
    const context = await browser.newContext({ ignoreHTTPSErrors: true, storageState: undefined });
    const page = await context.newPage();

    await page.goto('https://localhost/auth/login?next=%2F');

    expect(page.url()).toContain('/realms/apps-platform/');
    await context.close();
  });

  test('authenticated visit lands on portal directory', async ({ page }) => {
    // Wait for Angular to boot and /auth/me to resolve before asserting
    await page.goto('https://localhost', { waitUntil: 'networkidle', timeout: 20000 });
    await expect(page.locator('main.layout')).toBeVisible();
  });
});
