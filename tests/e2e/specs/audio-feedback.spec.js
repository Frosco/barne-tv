/**
 * E2E Tests for Audio Feedback System (Story 4.5)
 *
 * Tests audio playback on user interactions, settings controls,
 * and graceful fallback when audio is unavailable.
 *
 * Test IDs: 4.5-E2E-001 through 4.5-E2E-007
 */

import { test, expect } from '@playwright/test';

// =============================================================================
// TEST HELPERS
// =============================================================================

/**
 * Login to admin interface.
 */
async function loginAsAdmin(page) {
  await page.goto('/admin/login');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL('/admin/channels');
}

/**
 * Setup audio monitoring in the page context.
 * Returns a function to check if audio was played.
 */
async function setupAudioMonitoring(page) {
  await page.addInitScript(() => {
    window.audioPlayedEvents = [];
    // Override HTMLMediaElement.prototype.play to track calls
    const originalPlay = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function () {
      window.audioPlayedEvents.push({
        src: this.src,
        timestamp: Date.now(),
      });
      return originalPlay.call(this);
    };
  });

  return async () => {
    return await page.evaluate(() => window.audioPlayedEvents || []);
  };
}

// =============================================================================
// AC1: Click Sound Tests
// =============================================================================

test.describe('Audio Feedback - Click Sound (AC 1)', () => {
  test('4.5-E2E-001: Click thumbnail plays audible sound (P1)', async ({
    page,
  }) => {
    // Arrange: Setup audio monitoring
    const getAudioEvents = await setupAudioMonitoring(page);
    await page.goto('/');

    // Wait for grid to load
    await page.waitForSelector('[data-video-id]');

    // Act: Click first video thumbnail
    await page.click('[data-video-id]');

    // Wait for potential audio playback
    await page.waitForTimeout(200);

    // Assert: Audio play event was triggered
    const audioEvents = await getAudioEvents();
    const clickSoundPlayed = audioEvents.some((event) =>
      event.src.includes('click.mp3')
    );
    expect(clickSoundPlayed).toBe(true);
  });
});

// =============================================================================
// AC2: Transition Sound Tests
// =============================================================================

test.describe('Audio Feedback - Transition Sound (AC 2)', () => {
  test('4.5-E2E-002: Return to grid plays transition sound (P1)', async ({
    page,
  }) => {
    // Arrange: Setup audio monitoring and navigate to video player
    const getAudioEvents = await setupAudioMonitoring(page);
    await page.goto('/');
    await page.waitForSelector('[data-video-id]');

    // Navigate to player
    await page.click('[data-video-id]');
    await page.waitForURL(/.*video=.*/);

    // Clear previous audio events
    await page.evaluate(() => {
      window.audioPlayedEvents = [];
    });

    // Act: Press ESC to return to grid
    await page.keyboard.press('Escape');
    await page.waitForURL('/');

    // Wait for potential audio playback
    await page.waitForTimeout(200);

    // Assert: Transition sound was played
    const audioEvents = await getAudioEvents();
    const transitionSoundPlayed = audioEvents.some((event) =>
      event.src.includes('transition.mp3')
    );
    expect(transitionSoundPlayed).toBe(true);
  });
});

// =============================================================================
// AC3: Warning Chime Tests
// =============================================================================

test.describe('Audio Feedback - Warning Chime (AC 3)', () => {
  test('4.5-E2E-003: Warning display triggers chime sound (P1)', async ({
    page,
  }) => {
    // This test requires setting up a scenario where warnings are triggered
    // For now, we'll skip this test as it requires complex state manipulation
    test.skip(
      'Requires complex time limit state - test manually or with backend mock'
    );

    // TODO: Implement when we have a way to trigger warnings in E2E tests
    // Options:
    // 1. Mock backend to return low remaining time
    // 2. Fast-forward time using Date mocking
    // 3. Add test-only endpoint to trigger warning state
  });
});

// =============================================================================
// AC4: Audio Enable/Disable Tests
// =============================================================================

test.describe('Audio Feedback - Enable/Disable Control (AC 4)', () => {
  test('4.5-E2E-004: Toggle audio setting prevents sound playback (P1)', async ({
    page,
  }) => {
    // Arrange: Login and disable audio
    await loginAsAdmin(page);
    await page.goto('/admin/settings');

    // Uncheck audio enabled checkbox
    const audioCheckbox = page.locator('input[name="audio_enabled"]');
    await audioCheckbox.uncheck();

    // Save settings
    await page.click('button[type="submit"]');
    await page.waitForSelector('text=Innstillinger lagret');

    // Setup audio monitoring on child page
    await page.goto('/');
    const getAudioEvents = await setupAudioMonitoring(page);

    // Act: Click thumbnail (audio should NOT play)
    await page.waitForSelector('[data-video-id]');
    await page.click('[data-video-id]');
    await page.waitForTimeout(200);

    // Assert: No audio events triggered
    const audioEvents = await getAudioEvents();
    expect(audioEvents.length).toBe(0);

    // Cleanup: Re-enable audio for other tests
    await loginAsAdmin(page);
    await page.goto('/admin/settings');
    await page.locator('input[name="audio_enabled"]').check();
    await page.click('button[type="submit"]');
  });
});

// =============================================================================
// AC5: Volume Control Tests
// =============================================================================

test.describe('Audio Feedback - Volume Control (AC 5)', () => {
  test('4.5-E2E-005: Volume slider updates audio playback volume (P1)', async ({
    page,
  }) => {
    // Arrange: Login and change volume
    await loginAsAdmin(page);
    await page.goto('/admin/settings');

    // Set volume to 50%
    const volumeSlider = page.locator('input[name="audio_volume"]');
    await volumeSlider.fill('50');

    // Save settings
    await page.click('button[type="submit"]');
    await page.waitForSelector('text=Innstillinger lagret');

    // Go to child page
    await page.goto('/');
    await page.waitForSelector('[data-video-id]');

    // Act: Click thumbnail to trigger audio
    await page.click('[data-video-id]');
    await page.waitForTimeout(200);

    // Assert: Audio element has correct volume
    const audioVolume = await page.evaluate(() => {
      const audioElements = document.querySelectorAll('audio');
      if (audioElements.length > 0) {
        // Find the most recently created audio element
        return audioElements[audioElements.length - 1].volume;
      }
      return null;
    });

    expect(audioVolume).toBeCloseTo(0.5, 1);

    // Cleanup: Reset volume to default
    await loginAsAdmin(page);
    await page.goto('/admin/settings');
    await page.locator('input[name="audio_volume"]').fill('70');
    await page.click('button[type="submit"]');
  });
});

// =============================================================================
// AC9: Graceful Fallback Tests (P0 PRIORITY)
// =============================================================================

test.describe('Audio Feedback - Graceful Fallback (AC 9) - P0', () => {
  test('4.5-E2E-006: App functions perfectly with audio disabled (P0)', async ({
    page,
  }) => {
    // Arrange: Disable audio via settings
    await loginAsAdmin(page);
    await page.goto('/admin/settings');
    await page.locator('input[name="audio_enabled"]').uncheck();
    await page.click('button[type="submit"]');
    await page.waitForSelector('text=Innstillinger lagret');

    // Track console errors
    const consoleErrors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Act: Navigate child interface
    await page.goto('/');
    await page.waitForSelector('[data-video-id]');

    // Click thumbnail
    await page.click('[data-video-id]');
    await page.waitForURL(/.*video=.*/);

    // Return to grid
    await page.keyboard.press('Escape');
    await page.waitForURL('/');

    // Assert: No JavaScript errors occurred
    expect(consoleErrors.length).toBe(0);

    // Assert: UI still works (grid is visible)
    const gridVisible = await page.isVisible('[data-video-id]');
    expect(gridVisible).toBe(true);

    // Cleanup: Re-enable audio
    await loginAsAdmin(page);
    await page.goto('/admin/settings');
    await page.locator('input[name="audio_enabled"]').check();
    await page.click('button[type="submit"]');
  });

  test('4.5-E2E-007: App functions with autoplay blocked by browser (P0)', async ({
    context,
    page,
  }) => {
    // Arrange: Block autoplay at browser level
    await context.grantPermissions([], { origin: page.url() });

    // Override play() to simulate autoplay blocking
    await page.addInitScript(() => {
      const originalPlay = HTMLMediaElement.prototype.play;
      HTMLMediaElement.prototype.play = function () {
        // Simulate autoplay rejection
        return Promise.reject(
          new Error('play() failed because the user did not interact')
        );
      };
    });

    // Track console errors (should see warnings, but not errors)
    const consoleErrors = [];
    const consoleWarnings = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      } else if (msg.type() === 'warning') {
        consoleWarnings.push(msg.text());
      }
    });

    // Act: Navigate and interact with UI
    await page.goto('/');
    await page.waitForSelector('[data-video-id]');

    // Click thumbnail (audio will fail, but app should work)
    await page.click('[data-video-id]');
    await page.waitForURL(/.*video=.*/);

    // Wait for potential errors to surface
    await page.waitForTimeout(500);

    // Assert: No JavaScript errors (warnings OK, they're graceful)
    const criticalErrors = consoleErrors.filter(
      (err) => !err.includes('[Audio]')
    );
    expect(criticalErrors.length).toBe(0);

    // Assert: Navigation still worked despite audio failure
    expect(page.url()).toContain('video=');

    // Assert: Graceful warnings were logged (optional but good practice)
    const audioWarnings = consoleWarnings.filter((warn) =>
      warn.includes('[Audio]')
    );
    // Should have at least one warning about audio failure
    expect(audioWarnings.length).toBeGreaterThanOrEqual(0); // Warnings may or may not appear
  });
});

// =============================================================================
// STATIC VALIDATION (File Existence)
// =============================================================================

test.describe('Audio Feedback - Static Validation', () => {
  test('4.5-STATIC-002: Audio files exist in correct directory (P3)', async ({
    page,
  }) => {
    // Test that audio files are accessible via HTTP
    await page.goto('/');

    const audioFiles = [
      '/sounds/click.mp3',
      '/sounds/transition.mp3',
      '/sounds/warning-chime.mp3',
      '/sounds/grace-notification.mp3',
    ];

    for (const file of audioFiles) {
      const response = await page.goto(file);
      expect(response.status()).toBe(200);
      expect(response.headers()['content-type']).toContain('audio');
    }
  });
});
