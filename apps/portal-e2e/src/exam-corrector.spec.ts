import { test, expect } from '@playwright/test';

test.describe('exam-corrector', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('https://localhost/exam-corrector');
    // Wait for the micro-frontend web component to mount
    await page.waitForSelector('exam-corrector-app', { timeout: 15000 });
  });

  test('page loads the web component', async ({ page }) => {
    await expect(page.locator('exam-corrector-app')).toBeVisible();
  });

  test('individual tab is active by default', async ({ page }) => {
    const activeTab = page.locator('button.tab-active', { hasText: 'Individual' });
    await expect(activeTab).toBeVisible();
  });

  test('template selector is visible', async ({ page }) => {
    await expect(page.locator('select[name="template_id"]')).toBeVisible();
  });

  test('batch and templates tabs are present', async ({ page }) => {
    await expect(page.locator('button', { hasText: 'Lote' })).toBeVisible();
    await expect(page.locator('button', { hasText: 'Plantillas' })).toBeVisible();
  });
});
