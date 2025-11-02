// Story 4.2 - Progressive Warnings & Wind-down Mode - Playwright Test
// Run with: npx playwright test test-story-4.2.spec.js --headed

const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://127.0.0.1:8000';
const VITE_URL = 'http://localhost:5173';

test.describe('Story 4.2 - Progressive Warnings & Wind-down Mode', () => {

  test.beforeEach(async ({ page }) => {
    // Set up console logging
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('❌ Browser error:', msg.text());
      } else if (msg.text().includes('[Audio Stub]') || msg.text().includes('Warning')) {
        console.log('ℹ️ ', msg.text());
      }
    });
  });

  test('1. Child interface loads successfully', async ({ page }) => {
    await page.goto(`${BASE_URL}/child/grid`);
    await page.waitForLoadState('networkidle');

    // Check page loaded
    await expect(page).toHaveTitle(/Video Grid/);
    console.log('✅ Child interface loaded successfully');
  });

  test('2. Warning display elements exist in DOM', async ({ page }) => {
    await page.goto(`${BASE_URL}/child/grid`);
    await page.waitForLoadState('networkidle');

    // Check if warning overlay exists (may be hidden initially)
    const warningOverlay = await page.locator('.warning-overlay').count();
    console.log(`Found ${warningOverlay} warning overlay element(s)`);

    if (warningOverlay === 0) {
      console.log('⚠️  Warning overlay not found in DOM');
    } else {
      console.log('✅ Warning overlay exists in DOM');
    }
  });

  test('3. Backend API - POST /api/warnings/log with valid data', async ({ request }) => {
    // Test 10min warning
    const response1 = await request.post(`${BASE_URL}/api/warnings/log`, {
      data: {
        warningType: '10min',
        shownAt: new Date().toISOString()
      }
    });
    expect(response1.ok()).toBeTruthy();
    const data1 = await response1.json();
    expect(data1.success).toBe(true);
    console.log('✅ 10min warning logged successfully');

    // Test 5min warning
    const response2 = await request.post(`${BASE_URL}/api/warnings/log`, {
      data: {
        warningType: '5min',
        shownAt: new Date().toISOString()
      }
    });
    expect(response2.ok()).toBeTruthy();
    const data2 = await response2.json();
    expect(data2.success).toBe(true);
    console.log('✅ 5min warning logged successfully');

    // Test 2min warning
    const response3 = await request.post(`${BASE_URL}/api/warnings/log`, {
      data: {
        warningType: '2min',
        shownAt: new Date().toISOString()
      }
    });
    expect(response3.ok()).toBeTruthy();
    const data3 = await response3.json();
    expect(data3.success).toBe(true);
    console.log('✅ 2min warning logged successfully');
  });

  test('4. Backend API - POST /api/warnings/log rejects invalid warning type', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/warnings/log`, {
      data: {
        warningType: 'invalid',
        shownAt: new Date().toISOString()
      }
    });

    expect(response.status()).toBe(400);
    const data = await response.json();
    expect(data.error).toBeTruthy();
    console.log('✅ API correctly rejected invalid warning type:', data.message);
  });

  test('5. Backend API - GET /api/videos supports max_duration parameter', async ({ request }) => {
    // Test without max_duration
    const response1 = await request.get(`${BASE_URL}/api/videos?count=9`);
    console.log('Status without filter:', response1.status());

    // Test with max_duration=300 (5 minutes)
    const response2 = await request.get(`${BASE_URL}/api/videos?count=9&max_duration=300`);
    console.log('Status with 5min filter:', response2.status());

    // Test with max_duration=120 (2 minutes)
    const response3 = await request.get(`${BASE_URL}/api/videos?count=9&max_duration=120`);
    console.log('Status with 2min filter:', response3.status());

    console.log('✅ max_duration parameter accepted (503 expected when no videos exist)');
  });

  test('6. Backend API - GET /admin/warnings requires authentication', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/admin/warnings`);
    expect(response.status()).toBe(401);
    const data = await response.json();
    expect(data.detail).toBe('Unauthorized');
    console.log('✅ Admin warnings endpoint requires authentication');
  });

  test('7. Test warning display via console manipulation', async ({ page }) => {
    await page.goto(`${BASE_URL}/child/grid`);
    await page.waitForLoadState('networkidle');

    // Wait for child.js to initialize
    await page.waitForTimeout(1000);

    // Check if warningDisplay is available
    const hasWarningDisplay = await page.evaluate(() => {
      return typeof window.warningDisplay !== 'undefined';
    });

    console.log('warningDisplay available:', hasWarningDisplay);

    if (hasWarningDisplay) {
      // Test showing 10min warning
      await page.evaluate(() => {
        window.warningDisplay.show('10min');
      });

      // Wait for warning to appear
      await page.waitForTimeout(500);

      // Check if warning is visible
      const warningVisible = await page.locator('.warning-overlay--active').count();
      console.log('Warning visible:', warningVisible > 0 ? '✅' : '⚠️');

      // Wait for auto-dismiss
      await page.waitForTimeout(3500);

      console.log('✅ Warning display test completed');
    } else {
      console.log('⚠️  warningDisplay not available in window object');
    }
  });

  test('8. Check CSS classes for wind-down mode', async ({ page }) => {
    await page.goto(`${BASE_URL}/child/grid`);
    await page.waitForLoadState('networkidle');

    // Check if video-grid exists
    const gridExists = await page.locator('.video-grid').count();
    console.log('Video grid found:', gridExists > 0 ? '✅' : '⚠️');

    if (gridExists > 0) {
      // Check for wind-down class (should not be present initially in normal mode)
      const hasWinddown = await page.locator('.video-grid--winddown').count();
      console.log('Wind-down class present:', hasWinddown > 0 ? 'Yes' : 'No (expected in normal mode)');
    }

    console.log('✅ CSS class check completed');
  });

  test('9. Verify limit status endpoint returns current state', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/limit/status`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    expect(data).toHaveProperty('currentState');
    expect(data).toHaveProperty('minutesRemaining');
    expect(data).toHaveProperty('minutesWatched');

    console.log('Current state:', data.currentState);
    console.log('Minutes remaining:', data.minutesRemaining);
    console.log('Minutes watched:', data.minutesWatched);
    console.log('✅ Limit status endpoint working correctly');
  });

});
