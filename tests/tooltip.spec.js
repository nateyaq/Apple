const { test, expect } = require('@playwright/test');

// Update the path if your demo.html is served from a different location
const DEMO_URL = 'http://localhost:8000/demo.html';

test.describe('Dashboard Tooltips', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DEMO_URL);
    // Wait for dashboard to load
    await page.waitForSelector('#dashboard', { state: 'visible' });
  });

  test('All info icons show tooltips with correct structure', async ({ page }) => {
    const infoIcons = await page.$$('i[data-lucide="info"]');
    for (const icon of infoIcons) {
      await icon.hover();
      // Wait for tooltip to appear
      const tooltip = await page.waitForSelector('.custom-tooltip', { state: 'visible', timeout: 2000 });
      // Check tooltip structure
      const arrow = await tooltip.$('.custom-tooltip-arrow');
      expect(arrow).not.toBeNull();
      // Check font size and padding
      const style = await tooltip.evaluate(node => window.getComputedStyle(node));
      expect(style.fontSize).toBe('16px'); // 1rem default
      expect(style.padding).toBe('16px 20px');
      // Hide tooltip for next iteration
      await page.mouse.move(0, 0);
    }
  });
}); 