import { test, expect } from '@playwright/test';

test.describe('Public Access', () => {
  test('landing page loads with CTA', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('button', { name: /Start Validating|Начать валидацию|Սկսել/i })).toBeVisible();
  });

  test('login redirects to validations', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveURL(/validations/);
  });

  test('validations page is accessible', async ({ page }) => {
    await page.goto('/validations');
    await expect(page.getByRole('button', { name: /Run Validation|Запустить|Գործարկել/i })).toBeVisible();
  });

  test('dashboard loads', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.locator('h1').first()).toBeVisible();
  });

  test('projects page loads', async ({ page }) => {
    await page.goto('/projects');
    await expect(page.locator('h1').first()).toBeVisible();
  });

  test('settings page loads', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.locator('h1').first()).toBeVisible();
  });
});
