import { test, expect } from '@playwright/test';

test.describe('exam-corrector', () => {
  test.beforeEach(async ({ page }) => {
    // networkidle ensures Angular has bootstrapped and registry API has resolved
    await page.goto('https://localhost/exam-corrector', { waitUntil: 'networkidle', timeout: 20000 });
    // Wait for the web component: mfe-loader fetches script → customElements.define → createElement
    await page.waitForSelector('exam-corrector-app', { timeout: 30000 });
  });

  test('page loads the web component', async ({ page }) => {
    await expect(page.locator('exam-corrector-app')).toBeVisible();
  });

  test('individual tab is active by default', async ({ page }) => {
    await expect(page.locator('button.tab-active', { hasText: 'Individual' })).toBeVisible();
  });

  test('template selector is visible', async ({ page }) => {
    await expect(page.locator('select[name="template_id"]')).toBeVisible();
  });

  test('batch and templates tabs are present', async ({ page }) => {
    await expect(page.locator('button', { hasText: 'Lote' })).toBeVisible();
    await expect(page.locator('button', { hasText: 'Plantillas' })).toBeVisible();
  });
});
