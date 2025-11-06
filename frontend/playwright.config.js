import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E Test Configuration
 *
 * Story 1.5 - Channel Management E2E Tests
 *
 * Runs end-to-end tests for the Safe YouTube Viewer admin interface.
 * Tests validate critical user journeys including channel management.
 */
export default defineConfig({
  testDir: '../tests/e2e',

  /* Maximum time one test can run for */
  timeout: 30 * 1000,

  /* Run tests in files in parallel */
  fullyParallel: false, // Keep false for admin operations to avoid conflicts

  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI */
  workers: process.env.CI ? 1 : 1, // Single worker to avoid database conflicts

  /* Reporter to use */
  reporter: process.env.CI ? 'github' : 'list',

  /* Shared settings for all the projects below */
  use: {
    /* Base URL to use in actions like `await page.goto('/')` */
    baseURL: 'http://localhost:8000',

    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',

    /* Screenshot only on failure to conserve resources */
    screenshot: 'only-on-failure',

    /* Video only on failure */
    video: 'retain-on-failure',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Run backend server before starting the tests */
  webServer: {
    command: 'uv run uvicorn backend.main:app --port 8000',
    url: 'http://localhost:8000/health',
    reuseExistingServer: !process.env.CI, // Allow reuse in local development
    timeout: 120 * 1000, // 2 minutes to start server
    stdout: 'pipe',
    stderr: 'pipe',
    cwd: '../', // Run from project root
  },
});
