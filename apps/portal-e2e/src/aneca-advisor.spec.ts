import { test, expect } from '@playwright/test';

test.describe('aneca-advisor', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('https://localhost/aneca-advisor');
    await page.waitForSelector('aneca-advisor-app', { timeout: 15000 });
  });

  test('page loads the web component', async ({ page }) => {
    await expect(page.locator('aneca-advisor-app')).toBeVisible();
  });

  test('fields load from API (no 401)', async ({ page }) => {
    // The field selector should be populated if /api/aneca/fields returned data
    const fieldSelect = page.locator('aneca-advisor-app select').nth(1);
    await expect(fieldSelect).toBeVisible();
    const optionCount = await fieldSelect.locator('option').count();
    expect(optionCount).toBeGreaterThan(0);
  });

  test('evaluate button is present on the Evaluar tab', async ({ page }) => {
    // Navigate to the evaluation tab
    await page.locator('aneca-advisor-app button.tab-btn', { hasText: 'Evaluar' }).click();
    await expect(page.locator('aneca-advisor-app button.btn-primary', { hasText: 'Evaluar ahora' })).toBeVisible();
  });

  test('submitting evaluation returns a verdict', async ({ page }) => {
    await page.locator('aneca-advisor-app button.tab-btn', { hasText: 'Evaluar' }).click();

    await page.locator('aneca-advisor-app button.btn-primary', { hasText: 'Evaluar ahora' }).click();

    // Wait for APTO or NO APTO verdict
    await expect(page.locator('aneca-advisor-app .verdict-text')).toBeVisible({ timeout: 10000 });
    const verdict = await page.locator('aneca-advisor-app .verdict-text').textContent();
    expect(['APTO', 'NO APTO']).toContain(verdict?.trim());
  });
});
