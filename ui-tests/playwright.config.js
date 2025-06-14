// playwright.config.js
// Basic Playwright config for CI

/** @type {import('@playwright/test').PlaywrightTestConfig} */
const config = {
  timeout: 30000,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    headless: true,
    baseURL: 'http://localhost:8000',
  },
};

module.exports = config; 