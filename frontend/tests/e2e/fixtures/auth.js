/**
 * Authentication fixtures for E2E tests
 *
 * Provides reusable helpers for admin authentication and navigation.
 *
 * Story 1.5 - Channel Management E2E Tests
 */

/**
 * Log in as admin user
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} password - Admin password (defaults to 'admin123' for tests)
 * @returns {Promise<void>}
 */
export async function loginAsAdmin(page, password = 'admin123') {
  // Navigate to admin login page
  await page.goto('/admin/login');

  // Wait for login form to be visible
  await page.waitForSelector('form[data-form="admin-login"]', { timeout: 5000 });

  // Fill in password field
  await page.fill('input[name="password"]', password);

  // Click login button
  await page.click('button[type="submit"]');

  // Wait for redirect to admin dashboard (successful login)
  await page.waitForURL(/\/admin\//, { timeout: 5000 });
}

/**
 * Navigate to channels management page
 *
 * Assumes user is already logged in.
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<void>}
 */
export async function navigateToChannels(page) {
  await page.goto('/admin/channels');

  // Wait for channel table to be visible
  await page.waitForSelector('[data-testid="channel-table"]', {
    timeout: 10000,
    state: 'visible',
  });
}

/**
 * Count number of channels in the channel table
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<number>} Number of channels in table
 */
export async function countChannels(page) {
  const rows = await page.locator('[data-testid="channel-row"]').count();
  return rows;
}

/**
 * Log out from admin session
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<void>}
 */
export async function logoutAdmin(page) {
  // Look for logout button/link
  const logoutButton = page.locator('button:has-text("Logg ut")');

  if (await logoutButton.isVisible()) {
    await logoutButton.click();
    // Wait for redirect to login page
    await page.waitForURL(/\/admin\/login/, { timeout: 5000 });
  }
}
