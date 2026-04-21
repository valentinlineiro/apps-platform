import { test, expect } from '@playwright/test';

test.describe('profile preferences', () => {
  test('profile page loads', async ({ page }) => {
    await page.goto('https://localhost/profile');
    await expect(page.locator('button', { hasText: 'Guardar preferencias' }).first()).toBeVisible();
  });

  test('theme preference persists after reload', async ({ page }) => {
    await page.goto('https://localhost/profile');
    await expect(page.locator('button', { hasText: 'Guardar preferencias' }).first()).toBeVisible();

    const themeSelect = page.locator('select.select').first();
    const currentTheme = await themeSelect.inputValue();
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    await themeSelect.selectOption(newTheme);
    await page.locator('button', { hasText: 'Guardar preferencias' }).first().click();
    await expect(page.locator('.banner--ok, .banner')).toBeVisible({ timeout: 5000 });

    await page.reload();
    await expect(page.locator('select.select').first()).toHaveValue(newTheme);

    // Restore original
    await page.locator('select.select').first().selectOption(currentTheme);
    await page.locator('button', { hasText: 'Guardar preferencias' }).first().click();
  });
});
