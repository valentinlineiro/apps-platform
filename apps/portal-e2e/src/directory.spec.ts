import { test, expect } from '@playwright/test';

test.describe('directory', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('https://localhost');
  });

  test('shows exam-corrector card', async ({ page }) => {
    await expect(page.locator('a.card', { hasText: 'exam-corrector' })).toBeVisible();
  });

  test('shows aneca-advisor card', async ({ page }) => {
    await expect(page.locator('a.card', { hasText: 'ANECA Advisor' })).toBeVisible();
  });

  test('does not show disabled apps', async ({ page }) => {
    // attendance-checker is disabled in static_apps.json
    await expect(page.locator('a.card', { hasText: 'attendance-checker' })).not.toBeVisible();
  });

  test('cards link to correct routes', async ({ page }) => {
    const examCard = page.locator('a.card[href*="exam-corrector"]');
    await expect(examCard).toBeVisible();

    const anecaCard = page.locator('a.card[href*="aneca-advisor"]');
    await expect(anecaCard).toBeVisible();
  });
});
