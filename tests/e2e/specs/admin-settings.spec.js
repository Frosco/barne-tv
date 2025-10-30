/**
 * End-to-end tests for admin settings interface (Story 3.2).
 *
 * Tests complete user flows for configuration settings including:
 * - Authentication enforcement (TIER 1 security)
 * - Settings update workflow
 * - Reset to defaults workflow
 * - Settings persistence and immediate application
 *
 * Run with: npx playwright test tests/e2e/specs/admin-settings.spec.js
 */

import { test, expect } from '@playwright/test';

// Default admin password for tests (set during database initialization)
const ADMIN_PASSWORD = 'admin123';

/**
 * Helper: Login as admin
 */
async function loginAsAdmin(page) {
  await page.goto('/admin/login');
  await page.fill('input[name="password"]', ADMIN_PASSWORD);
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL('/admin/dashboard');
}

/**
 * Helper: Navigate to settings page
 */
async function navigateToSettings(page) {
  await page.goto('/admin/settings');
  await expect(page).toHaveURL('/admin/settings');
}

// =============================================================================
// TIER 1 SECURITY TEST
// =============================================================================

test('[TIER 1] T3.2-E2E-003: Authentication enforcement on all endpoints', async ({ page, context }) => {
  // Test 1: Cannot access settings page without authentication
  await page.goto('/admin/settings');
  // Should redirect to login or show error
  await expect(page).not.toHaveURL('/admin/settings');
  // Should be at login page
  await expect(page).toHaveURL('/admin/login');

  // Test 2: API endpoints return 401 without authentication
  // GET /api/admin/settings
  const getResponse = await page.request.get('/api/admin/settings');
  expect(getResponse.status()).toBe(401);

  // PUT /api/admin/settings
  const putResponse = await page.request.put('/api/admin/settings', {
    data: { daily_limit_minutes: 45 }
  });
  expect(putResponse.status()).toBe(401);

  // POST /api/admin/settings/reset
  const postResponse = await page.request.post('/api/admin/settings/reset');
  expect(postResponse.status()).toBe(401);

  // Test 3: Login and verify access works
  await loginAsAdmin(page);
  await navigateToSettings(page);

  // Should successfully load settings
  await expect(page.locator('form')).toBeVisible();
  await expect(page.locator('input[name="daily_limit_minutes"]')).toBeVisible();

  // Test 4: Logout and verify access is denied again
  await page.goto('/admin/logout');
  await page.goto('/admin/settings');
  await expect(page).not.toHaveURL('/admin/settings');
  await expect(page).toHaveURL('/admin/login');
});

// =============================================================================
// USER JOURNEY TESTS
// =============================================================================

test('T3.2-E2E-001: Complete settings update journey', async ({ page }) => {
  // Arrange: Login as admin
  await loginAsAdmin(page);
  await navigateToSettings(page);

  // Assert: Form displays with current values (defaults)
  await expect(page.locator('input[name="daily_limit_minutes"]')).toHaveValue('30');
  await expect(page.locator('input[name="grid_size"]')).toHaveValue('9');
  await expect(page.locator('input[name="audio_enabled"]')).toBeChecked();

  // Act: Change daily limit to 60
  await page.fill('input[name="daily_limit_minutes"]', '60');

  // Assert: Save button should be enabled (form is dirty)
  const saveButton = page.locator('button:has-text("Lagre")');
  await expect(saveButton).toBeEnabled();

  // Act: Change grid size to 12
  await page.fill('input[name="grid_size"]', '12');

  // Act: Toggle audio to disabled
  await page.uncheck('input[name="audio_enabled"]');

  // Act: Click save
  await saveButton.click();

  // Assert: Success message displayed (Norwegian)
  await expect(page.locator('text=Innstillinger lagret')).toBeVisible({ timeout: 5000 });

  // Act: Reload page (F5)
  await page.reload();

  // Assert: Form shows new values (60, 12, false)
  await expect(page.locator('input[name="daily_limit_minutes"]')).toHaveValue('60');
  await expect(page.locator('input[name="grid_size"]')).toHaveValue('12');
  await expect(page.locator('input[name="audio_enabled"]')).not.toBeChecked();

  // Optional: Verify grid size applied (navigate to child interface)
  // This would require content to exist and child interface to be implemented
  // await page.goto('/');
  // await expect(page.locator('.video-card')).toHaveCount(12);
});

test('T3.2-E2E-002: Reset to defaults workflow', async ({ page }) => {
  // Arrange: Login as admin and navigate to settings
  await loginAsAdmin(page);
  await navigateToSettings(page);

  // Arrange: Set custom values
  await page.fill('input[name="daily_limit_minutes"]', '120');
  await page.fill('input[name="grid_size"]', '15');
  await page.uncheck('input[name="audio_enabled"]');
  await page.click('button:has-text("Lagre")');
  await expect(page.locator('text=Innstillinger lagret')).toBeVisible({ timeout: 5000 });

  // Assert: Custom values saved
  await page.reload();
  await expect(page.locator('input[name="daily_limit_minutes"]')).toHaveValue('120');
  await expect(page.locator('input[name="grid_size"]')).toHaveValue('15');
  await expect(page.locator('input[name="audio_enabled"]')).not.toBeChecked();

  // Act: Click "Tilbakestill til standard" button
  const resetButton = page.locator('button:has-text("Tilbakestill")');
  await resetButton.click();

  // Assert: Confirmation dialog appears with Norwegian text
  // Handle the browser's native confirm dialog
  page.once('dialog', async dialog => {
    expect(dialog.type()).toBe('confirm');
    expect(dialog.message()).toContain('sikker'); // Norwegian confirmation text
    await dialog.dismiss(); // First test: Cancel
  });

  // Wait a bit for dialog to appear and be dismissed
  await page.waitForTimeout(500);

  // Assert: Settings unchanged (still custom after cancel)
  await expect(page.locator('input[name="daily_limit_minutes"]')).toHaveValue('120');
  await expect(page.locator('input[name="grid_size"]')).toHaveValue('15');

  // Act: Click reset button again
  await resetButton.click();

  // Act: This time confirm
  page.once('dialog', async dialog => {
    expect(dialog.type()).toBe('confirm');
    await dialog.accept(); // Confirm reset
  });

  // Wait for reset to complete
  await page.waitForTimeout(500);

  // Assert: Success message
  await expect(page.locator('text=Innstillinger tilbakestilt')).toBeVisible({ timeout: 5000 });

  // Assert: Form displays defaults (30, 9, true)
  await expect(page.locator('input[name="daily_limit_minutes"]')).toHaveValue('30');
  await expect(page.locator('input[name="grid_size"]')).toHaveValue('9');
  await expect(page.locator('input[name="audio_enabled"]')).toBeChecked();

  // Act: Reload page
  await page.reload();

  // Assert: Defaults persist
  await expect(page.locator('input[name="daily_limit_minutes"]')).toHaveValue('30');
  await expect(page.locator('input[name="grid_size"]')).toHaveValue('9');
  await expect(page.locator('input[name="audio_enabled"]')).toBeChecked();
});

test('T3.2-E2E-004: Settings persist and apply immediately', async ({ page, context }) => {
  // Arrange: Login and navigate to settings
  await loginAsAdmin(page);
  await navigateToSettings(page);

  // Act: Change daily_limit_minutes to 45
  await page.fill('input[name="daily_limit_minutes"]', '45');
  await page.click('button:has-text("Lagre")');
  await expect(page.locator('text=Innstillinger lagret')).toBeVisible({ timeout: 5000 });

  // Assert: Settings persisted (verify via API immediately)
  const getResponse = await page.request.get('/api/admin/settings');
  expect(getResponse.ok()).toBeTruthy();
  const data = await getResponse.json();
  expect(data.settings.daily_limit_minutes).toBe(45);

  // Assert: Navigate back to settings, value persists
  await page.goto('/admin/dashboard');
  await page.goto('/admin/settings');
  await expect(page.locator('input[name="daily_limit_minutes"]')).toHaveValue('45');

  // Assert: Open new tab, value persists (tests shared session)
  const newPage = await context.newPage();
  await newPage.goto('/admin/settings');
  await expect(newPage.locator('input[name="daily_limit_minutes"]')).toHaveValue('45');
  await newPage.close();

  // Assert: Settings applied immediately (no server restart)
  // Verify by making another API call
  const getResponse2 = await page.request.get('/api/admin/settings');
  const data2 = await getResponse2.json();
  expect(data2.settings.daily_limit_minutes).toBe(45);

  // Note: Full verification of daily limit enforcement would require:
  // 1. Content to exist in database
  // 2. Child interface to be implemented
  // 3. Watching videos and verifying limit calculation uses 45 minutes
  // This is acceptable for AC6 verification (immediate application without restart)
});
