import { expect, test } from '@playwright/test';

test('the workspace shows a real API connection and no scanning controls', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('אבטחת האתר');
  await expect(page.getByRole('status')).toHaveText('החיבור לשרת פעיל');
  await expect(page.getByText('המערכת עדיין אינה מבצעת סריקות או מציגה הערכות אבטחה.')).toBeVisible();
  await expect(page.getByRole('button')).toHaveCount(0);
  await page.screenshot({ path: 'test-results/stage-1-desktop.png', fullPage: true });
});

test('an unavailable API is shown as a failure, including on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/api/health', (route) => route.fulfill({ status: 503, body: '{}' }));
  await page.goto('/');
  await expect(page.getByRole('status')).toContainText('השרת אינו זמין');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
  await page.screenshot({ path: 'test-results/stage-1-mobile.png', fullPage: true });
});
