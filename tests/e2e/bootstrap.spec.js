import { expect, test } from '@playwright/test';

test('the workspace shows a real API connection and no scanning controls', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('API connection');
  await expect(page.getByRole('status')).toHaveText('Connected to the API');
  await expect(page.getByRole('link', { name: 'View the API health response' })).toHaveAttribute('href', '/api/health');
  await expect(page.getByRole('button')).toHaveCount(0);
  await page.screenshot({ path: 'test-results/stage-1-desktop.png', fullPage: true });
});

test('an unavailable API is shown as a failure, including on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/api/health', (route) => route.fulfill({ status: 503, body: '{}' }));
  await page.goto('/');
  await expect(page.getByRole('status')).toContainText('API unavailable');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
  await page.screenshot({ path: 'test-results/stage-1-mobile.png', fullPage: true });
});
