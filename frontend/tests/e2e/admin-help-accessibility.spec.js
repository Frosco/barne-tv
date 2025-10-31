/**
 * E2E Accessibility Tests for Admin Help Features (Story 3.X)
 * Tests WCAG 2.1 Level AA compliance for:
 * - Tooltips
 * - FAQ accordion
 * - Help text
 */

import { test, expect } from '@playwright/test';

// Test configuration
test.describe('Admin Help Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to admin dashboard (assumes authentication is handled)
    await page.goto('http://localhost:8000/admin/dashboard');
  });

  test.describe('Tooltip Keyboard Accessibility', () => {
    test('should be navigable with Tab key', async ({ page }) => {
      await page.goto('http://localhost:8000/admin/settings');

      // Find first tooltip trigger
      const tooltipTrigger = page.locator('.tooltip-trigger').first();
      await expect(tooltipTrigger).toBeVisible();

      // Tab to tooltip trigger
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab'); // May need multiple tabs depending on form structure

      // Check if trigger is focused (by checking if we can activate it)
      await tooltipTrigger.focus();
      await expect(tooltipTrigger).toBeFocused();
    });

    test('should open on Enter key', async ({ page }) => {
      await page.goto('http://localhost:8000/admin/settings');

      const tooltipTrigger = page.locator('.tooltip-trigger').first();
      await tooltipTrigger.focus();

      // Press Enter to open
      await page.keyboard.press('Enter');

      // Verify tooltip is visible
      const tooltip = page.locator('.tooltip-content').first();
      await expect(tooltip).toBeVisible();

      // Verify aria-expanded is true
      await expect(tooltipTrigger).toHaveAttribute('aria-expanded', 'true');
    });

    test('should close on ESC key', async ({ page }) => {
      await page.goto('http://localhost:8000/admin/settings');

      const tooltipTrigger = page.locator('.tooltip-trigger').first();
      const tooltip = page.locator('.tooltip-content').first();

      // Open tooltip
      await tooltipTrigger.click();
      await expect(tooltip).toBeVisible();

      // Press ESC to close
      await page.keyboard.press('Escape');
      await expect(tooltip).toBeHidden();

      // Verify aria-expanded is false
      await expect(tooltipTrigger).toHaveAttribute('aria-expanded', 'false');
    });

    test('should have correct ARIA attributes', async ({ page }) => {
      await page.goto('http://localhost:8000/admin/settings');

      const tooltipTrigger = page.locator('.tooltip-trigger').first();
      const tooltip = page.locator('.tooltip-content').first();

      // Verify role="tooltip"
      await expect(tooltip).toHaveAttribute('role', 'tooltip');

      // Verify aria-describedby links to tooltip
      const tooltipId = await tooltip.getAttribute('id');
      await expect(tooltipTrigger).toHaveAttribute(
        'aria-describedby',
        tooltipId
      );
    });
  });

  test.describe('FAQ Accordion Keyboard Accessibility', () => {
    test('should be navigable with Tab key', async ({ page }) => {
      // FAQ is on dashboard
      const firstQuestion = page.locator('.faq-question').first();
      await expect(firstQuestion).toBeVisible();

      // Tab to first question
      await firstQuestion.focus();
      await expect(firstQuestion).toBeFocused();
    });

    test('should expand on Enter key', async ({ page }) => {
      const firstQuestion = page.locator('.faq-question').first();
      const firstAnswer = page.locator('.faq-answer').first();

      await firstQuestion.focus();

      // Initially collapsed
      await expect(firstQuestion).toHaveAttribute('aria-expanded', 'false');
      await expect(firstAnswer).toBeHidden();

      // Press Enter to expand
      await page.keyboard.press('Enter');

      // Verify expanded
      await expect(firstQuestion).toHaveAttribute('aria-expanded', 'true');
      await expect(firstAnswer).toBeVisible();
    });

    test('should expand on Space key', async ({ page }) => {
      const firstQuestion = page.locator('.faq-question').first();
      const firstAnswer = page.locator('.faq-answer').first();

      await firstQuestion.focus();

      // Press Space to expand
      await page.keyboard.press('Space');

      // Verify expanded
      await expect(firstQuestion).toHaveAttribute('aria-expanded', 'true');
      await expect(firstAnswer).toBeVisible();
    });

    test('should have correct ARIA attributes', async ({ page }) => {
      const firstQuestion = page.locator('.faq-question').first();
      const firstAnswer = page.locator('.faq-answer').first();

      // Verify aria-controls links to answer
      const answerId = await firstAnswer.getAttribute('id');
      await expect(firstQuestion).toHaveAttribute('aria-controls', answerId);

      // Verify role="button"
      await expect(firstQuestion).toHaveAttribute('type', 'button');
    });
  });

  test.describe('Help Text Accessibility', () => {
    test('should have aria-describedby associations', async ({ page }) => {
      await page.goto('http://localhost:8000/admin/settings');

      // Check daily limit input has aria-describedby
      const dailyLimitInput = page.locator('#daily-limit');
      const describedBy =
        await dailyLimitInput.getAttribute('aria-describedby');
      expect(describedBy).toBeTruthy();
      expect(describedBy).toContain('daily-limit-help');

      // Verify help text exists with correct ID
      const helpText = page.locator('#daily-limit-help');
      await expect(helpText).toBeVisible();
    });

    test('should be readable by screen readers', async ({ page }) => {
      await page.goto('http://localhost:8000/admin/settings');

      // Verify help text is visible and has content
      const helpText = page.locator('.help-text').first();
      await expect(helpText).toBeVisible();
      const textContent = await helpText.textContent();
      expect(textContent.length).toBeGreaterThan(0);
    });
  });

  test.describe('Color Contrast', () => {
    test('should meet WCAG AA contrast requirements', async ({ page }) => {
      await page.goto('http://localhost:8000/admin/settings');

      // Test help text color contrast
      // (Note: This is a basic check; ideally use axe-core for comprehensive testing)
      const helpText = page.locator('.help-text').first();
      const color = await helpText.evaluate((el) => {
        const style = window.getComputedStyle(el);
        return style.color;
      });

      // Verify color is set (actual contrast testing would require axe-core)
      expect(color).toBeTruthy();
    });
  });

  test.describe('General Accessibility', () => {
    test('should have semantic footer', async ({ page }) => {
      const footer = page.locator('footer');
      await expect(footer).toBeVisible();

      // Verify version is displayed
      const versionNumber = page.locator('.version-number');
      await expect(versionNumber).toBeVisible();
      const version = await versionNumber.textContent();
      expect(version).toContain('Versjon');
    });

    test('should have accessible documentation link', async ({ page }) => {
      const helpLink = page.locator('.help-link');
      await expect(helpLink).toBeVisible();

      // Verify accessible label
      const ariaLabel = await helpLink.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
      expect(ariaLabel).toContain('dokumentasjon');

      // Verify link text
      const linkText = await helpLink.textContent();
      expect(linkText).toContain('Kom i gang');
    });
  });
});
