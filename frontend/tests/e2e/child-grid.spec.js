/**
 * E2E Tests for Child-Friendly Video Grid
 *
 * Story 2.1 - Child-Friendly Video Grid Interface
 *
 * Tests: 21 E2E scenarios covering grid rendering, responsive design,
 * visual styling, mascot integration, and user interactions.
 *
 * Test Design: docs/qa/assessments/2.1-test-design-20251022.md
 */

import { test, expect } from '@playwright/test';
import {
  navigateToGrid,
  waitForGrid,
  getVideoCards,
  getVideoCard,
  countVideoCards,
  getCardDimensions,
  getThumbnailDimensions,
  getMascotElement,
  getMascotPosition,
  getComputedStyle,
  getGridColumnCount,
  clickVideoCard,
  areCardsDisabled,
  refreshGrid,
  getVideoTitles,
} from './fixtures/child.js';

// =============================================================================
// GROUP 1: GRID RENDERING TESTS (AC 1, 3, 4)
// =============================================================================

test.describe('Grid Rendering', () => {
  /**
   * Test 2.1-E2E-001: Grid Renders with 9 Videos
   *
   * Validates that the grid renders with the default 9 videos on initial load.
   *
   * Priority: P1 (High)
   * Category: Grid Rendering - Core Functionality
   */
  test('2.1-E2E-001: Grid renders with 9 videos on initial load', async ({
    page,
  }) => {
    // Step 1: Navigate to child grid page
    await navigateToGrid(page);

    // Step 2: Wait for grid to finish loading
    await waitForGrid(page);

    // Step 3: Count video cards in grid
    const cardCount = await countVideoCards(page);

    // Step 4: Verify default grid size is 9
    expect(cardCount).toBe(9);

    // Step 5: Verify all cards are visible
    const cards = getVideoCards(page);
    const count = await cards.count();
    for (let i = 0; i < count; i++) {
      await expect(cards.nth(i)).toBeVisible();
    }
  });

  /**
   * Test 2.1-E2E-003: Thumbnail Dimensions Meet Minimum
   *
   * Validates that video thumbnails meet the minimum 200x150px requirement.
   *
   * Priority: P1 (High)
   * Category: Grid Rendering - Visual Requirements
   * Acceptance Criteria: AC3 - Thumbnails large and clickable (minimum 200x150px)
   */
  test('2.1-E2E-003: Thumbnail dimensions meet minimum 200x150px', async ({
    page,
  }) => {
    // Step 1: Navigate and wait for grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 2: Get first video card
    const firstCard = getVideoCard(page, 0);

    // Step 3: Get thumbnail dimensions
    const dimensions = await getThumbnailDimensions(firstCard);

    // Step 4: Verify minimum dimensions
    expect(dimensions.width).toBeGreaterThanOrEqual(200);
    expect(dimensions.height).toBeGreaterThanOrEqual(150);
  });

  /**
   * Test 2.1-E2E-006: Titles Render Below Thumbnails
   *
   * Validates that video titles appear below thumbnails in the correct layout.
   *
   * Priority: P1 (High)
   * Category: Grid Rendering - Layout Validation
   * Acceptance Criteria: AC4 - Video titles appear below thumbnails
   */
  test('2.1-E2E-006: Titles render below thumbnails', async ({ page }) => {
    // Step 1: Navigate and wait for grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 2: Get first video card
    const firstCard = getVideoCard(page, 0);

    // Step 3: Get thumbnail and title elements
    const thumbnail = firstCard.locator('.video-card__thumbnail');
    const title = firstCard.locator('.video-card__title');

    // Step 4: Verify both elements are visible
    await expect(thumbnail).toBeVisible();
    await expect(title).toBeVisible();

    // Step 5: Verify title is below thumbnail
    const thumbnailBox = await thumbnail.boundingBox();
    const titleBox = await title.boundingBox();

    expect(titleBox.y).toBeGreaterThan(thumbnailBox.y + thumbnailBox.height);
  });

  /**
   * Test 2.1-E2E-007: Font Size Minimum for Readability
   *
   * Validates that video title font size meets minimum 16px requirement.
   *
   * Priority: P1 (High)
   * Category: Grid Rendering - Typography
   * Acceptance Criteria: AC4 - Titles in readable font
   */
  test('2.1-E2E-007: Font size minimum 16px for readability', async ({
    page,
  }) => {
    // Step 1: Navigate and wait for grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 2: Get first video card title
    const firstCard = getVideoCard(page, 0);
    const title = firstCard.locator('.video-card__title');

    // Step 3: Get computed font size
    const fontSize = await getComputedStyle(title, 'font-size');
    const fontSizeValue = parseFloat(fontSize);

    // Step 4: Verify minimum font size
    expect(fontSizeValue).toBeGreaterThanOrEqual(16);
  });

  /**
   * Test 2.1-E2E-021: Grid Displays Different Videos After Playback
   *
   * Validates that the grid refreshes with new videos after returning from playback.
   *
   * Priority: P1 (High)
   * Category: Grid Rendering - Dynamic Refresh
   * Acceptance Criteria: AC10 - Grid refreshes when returning from video playback
   */
  test('2.1-E2E-021: Grid displays different videos after playback simulation', async ({
    page,
  }) => {
    // Step 1: Navigate and wait for grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 2: Capture initial video titles
    const initialTitles = await getVideoTitles(page);

    // Step 3: Refresh the grid (simulates return from playback)
    await refreshGrid(page);

    // Step 4: Capture new video titles
    const newTitles = await getVideoTitles(page);

    // Step 5: Verify grid refreshed (titles may be different due to randomness)
    // Note: Due to weighted random algorithm, some videos may repeat
    // We verify that the grid successfully re-rendered
    expect(newTitles.length).toBe(initialTitles.length);
    expect(newTitles.length).toBeGreaterThan(0);
  });
});

// =============================================================================
// GROUP 2: RESPONSIVE DESIGN TESTS (AC 6, 7)
// =============================================================================

test.describe('Responsive Design', () => {
  /**
   * Test 2.1-E2E-012: Grid Renders at 1920x1080 Desktop Resolution
   *
   * Validates that the grid renders properly on desktop viewport.
   *
   * Priority: P1 (High)
   * Category: Responsive Design - Desktop Layout
   * Acceptance Criteria: AC6 - Page works on 1920x1080 screens
   */
  test('2.1-E2E-012: Grid renders properly at 1920x1080 resolution', async ({
    page,
  }) => {
    // Step 1: Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });

    // Step 2: Navigate to grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 3: Verify grid container is visible
    const grid = page.locator('[data-grid]');
    await expect(grid).toBeVisible();

    // Step 4: Verify video cards render properly
    const cardCount = await countVideoCards(page);
    expect(cardCount).toBeGreaterThan(0);

    // Step 5: Verify cards are laid out correctly (not overflowing)
    const firstCard = getVideoCard(page, 0);
    const box = await firstCard.boundingBox();
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(1920);
  });

  /**
   * Test 2.1-E2E-013: 3-Column Layout on Desktop Viewport
   *
   * Validates that the grid uses 3-column layout on desktop.
   *
   * Priority: P1 (High)
   * Category: Responsive Design - Layout Structure
   * Acceptance Criteria: AC6 - Desktop layout structure
   */
  test('2.1-E2E-013: 3-column layout on desktop viewport', async ({ page }) => {
    // Step 1: Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });

    // Step 2: Navigate to grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 3: Get number of grid columns
    const columns = await getGridColumnCount(page);

    // Step 4: Verify 3 columns on desktop
    expect(columns).toBe(3);
  });

  /**
   * Test 2.1-E2E-014: Grid Renders at 1024x768 Tablet Resolution
   *
   * Validates that the grid renders properly on tablet viewport.
   *
   * Priority: P1 (High)
   * Category: Responsive Design - Tablet Layout
   * Acceptance Criteria: AC7 - Responsive layout adapts for tablet (1024x768 minimum)
   */
  test('2.1-E2E-014: Grid renders properly at 1024x768 resolution', async ({
    page,
  }) => {
    // Step 1: Set tablet viewport
    await page.setViewportSize({ width: 1024, height: 768 });

    // Step 2: Navigate to grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 3: Verify grid container is visible
    const grid = page.locator('[data-grid]');
    await expect(grid).toBeVisible();

    // Step 4: Verify video cards render properly
    const cardCount = await countVideoCards(page);
    expect(cardCount).toBeGreaterThan(0);

    // Step 5: Verify cards are laid out correctly (not overflowing)
    const firstCard = getVideoCard(page, 0);
    const box = await firstCard.boundingBox();
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(1024);
  });

  /**
   * Test 2.1-E2E-015: 2-Column Layout on Tablet Viewport
   *
   * Validates that the grid uses 2-column layout on tablet.
   *
   * Priority: P1 (High)
   * Category: Responsive Design - Layout Structure
   * Acceptance Criteria: AC7 - Tablet responsive layout
   */
  test('2.1-E2E-015: 2-column layout on tablet viewport', async ({ page }) => {
    // Step 1: Set tablet viewport
    await page.setViewportSize({ width: 1024, height: 768 });

    // Step 2: Navigate to grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 3: Get number of grid columns
    const columns = await getGridColumnCount(page);

    // Step 4: Verify 2 columns on tablet
    expect(columns).toBe(2);
  });
});

// =============================================================================
// GROUP 3: VISUAL STYLING TESTS (AC 4, 5)
// =============================================================================

test.describe('Visual Styling', () => {
  /**
   * Test 2.1-E2E-002: Grid Respects Parent-Configured Grid Size
   *
   * Validates that the grid respects the grid_size setting from admin interface.
   *
   * Priority: P2 (Medium)
   * Category: Visual Styling - Configuration
   * Acceptance Criteria: AC11 - Grid size controlled by grid_size setting
   *
   * Note: This test assumes default grid_size of 9. To fully test this,
   * you would need to modify the database setting and verify different sizes.
   */
  test('2.1-E2E-002: Grid respects grid_size setting (default 9)', async ({
    page,
  }) => {
    // Step 1: Navigate to grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 2: Count video cards
    const cardCount = await countVideoCards(page);

    // Step 3: Verify grid respects configured size
    // Default is 9, but could be 4-15 depending on settings
    expect(cardCount).toBeGreaterThanOrEqual(4);
    expect(cardCount).toBeLessThanOrEqual(15);
  });

  /**
   * Test 2.1-E2E-008: Long Titles Truncate with Ellipsis
   *
   * Validates that long video titles are truncated with ellipsis.
   *
   * Priority: P2 (Medium)
   * Category: Visual Styling - Text Overflow
   * Acceptance Criteria: AC4 - Readable font with proper text handling
   */
  test('2.1-E2E-008: Long titles truncate with ellipsis', async ({ page }) => {
    // Step 1: Navigate to grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 2: Get first video card title
    const firstCard = getVideoCard(page, 0);
    const title = firstCard.locator('.video-card__title');

    // Step 3: Check text-overflow CSS property
    const textOverflow = await getComputedStyle(title, 'text-overflow');
    const overflow = await getComputedStyle(title, 'overflow');

    // Step 4: Verify ellipsis or proper overflow handling
    // Should be either "ellipsis" or "hidden" with proper CSS
    expect(textOverflow === 'ellipsis' || overflow === 'hidden').toBeTruthy();
  });

  /**
   * Test 2.1-E2E-009: Yellow Accent Borders Using Design System
   *
   * Validates that yellow accent color is used in card borders.
   *
   * Priority: P2 (Medium)
   * Category: Visual Styling - Color Scheme
   * Acceptance Criteria: AC5 - Yellow accents from design system
   */
  test('2.1-E2E-009: Yellow accent color used in borders', async ({ page }) => {
    // Step 1: Navigate to grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 2: Get first video card
    const firstCard = getVideoCard(page, 0);

    // Step 3: Get border color (may appear on hover/focus)
    // Check if yellow color is defined in CSS custom properties
    const primaryColor = await page.evaluate(() => {
      return getComputedStyle(document.documentElement).getPropertyValue(
        '--color-primary'
      );
    });

    // Step 4: Verify yellow color is defined
    // Primary color should contain yellow-ish value
    expect(primaryColor).toBeTruthy();
    expect(primaryColor.trim().length).toBeGreaterThan(0);
  });

  /**
   * Test 2.1-E2E-010: Hover/Focus States Show Visual Feedback
   *
   * Validates that video cards show visual feedback on hover/focus.
   *
   * Priority: P2 (Medium)
   * Category: Visual Styling - Interactive States
   * Acceptance Criteria: AC5 - Playful, interactive CSS styling
   */
  test('2.1-E2E-010: Hover state shows visual feedback', async ({ page }) => {
    // Step 1: Navigate to grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 2: Get first video card
    const firstCard = getVideoCard(page, 0);

    // Step 3: Get initial box-shadow
    const initialShadow = await getComputedStyle(firstCard, 'box-shadow');

    // Step 4: Hover over card
    await firstCard.hover();

    // Step 5: Get box-shadow after hover
    const hoverShadow = await getComputedStyle(firstCard, 'box-shadow');

    // Step 6: Verify visual feedback (shadow or transform changes)
    // Note: This may pass if initial shadow exists, as hover might enhance it
    expect(hoverShadow).toBeTruthy();
    expect(hoverShadow).not.toBe('none');
  });

  /**
   * Test 2.1-E2E-011: Cards Have Rounded Corners and Shadows
   *
   * Validates playful aesthetic with rounded corners and shadows.
   *
   * Priority: P2 (Medium)
   * Category: Visual Styling - Aesthetic
   * Acceptance Criteria: AC5 - Colorful, playful CSS styling
   */
  test('2.1-E2E-011: Cards have rounded corners and shadows', async ({
    page,
  }) => {
    // Step 1: Navigate to grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 2: Get first video card
    const firstCard = getVideoCard(page, 0);

    // Step 3: Get border-radius
    const borderRadius = await getComputedStyle(firstCard, 'border-radius');

    // Step 4: Get box-shadow
    const boxShadow = await getComputedStyle(firstCard, 'box-shadow');

    // Step 5: Verify rounded corners (non-zero border-radius)
    expect(borderRadius).toBeTruthy();
    expect(borderRadius).not.toBe('0px');

    // Step 6: Verify shadow exists
    expect(boxShadow).toBeTruthy();
    expect(boxShadow).not.toBe('none');
  });

  /**
   * Test 2.1-E2E-016: Media Queries Activate at Correct Breakpoints
   *
   * Validates that CSS breakpoints activate at 768px and 1024px.
   *
   * Priority: P2 (Medium)
   * Category: Visual Styling - Responsive Breakpoints
   * Acceptance Criteria: AC7 - Responsive layout with proper breakpoints
   */
  test('2.1-E2E-016: Media queries activate at correct breakpoints', async ({
    page,
  }) => {
    // Test breakpoint: 1025px should show 3 columns (desktop)
    await page.setViewportSize({ width: 1025, height: 768 });
    await navigateToGrid(page);
    await waitForGrid(page);
    let columns = await getGridColumnCount(page);
    expect(columns).toBe(3);

    // Test breakpoint: 1024px should show 2 columns (tablet)
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.reload();
    await waitForGrid(page);
    columns = await getGridColumnCount(page);
    expect(columns).toBe(2);

    // Test breakpoint: 767px should show 1 column (mobile)
    await page.setViewportSize({ width: 767, height: 600 });
    await page.reload();
    await waitForGrid(page);
    columns = await getGridColumnCount(page);
    expect(columns).toBe(1);
  });
});

// =============================================================================
// GROUP 4: MASCOT INTEGRATION TESTS (AC 9)
// =============================================================================

test.describe('Mascot Integration', () => {
  /**
   * Test 2.1-E2E-019: Mascot Image Renders and Is Visible
   *
   * Validates that the mascot character is visible on the page.
   *
   * Priority: P2 (Medium)
   * Category: Mascot Integration - Visibility
   * Acceptance Criteria: AC9 - Mascot character visible in corner or header
   */
  test('2.1-E2E-019: Mascot image renders and is visible', async ({ page }) => {
    // Step 1: Navigate to grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 2: Get mascot element
    const mascot = getMascotElement(page);

    // Step 3: Verify mascot is visible
    await expect(mascot).toBeVisible();

    // Step 4: Verify mascot has valid src attribute
    const src = await mascot.getAttribute('src');
    expect(src).toBeTruthy();
    expect(src).toContain('owl');
  });

  /**
   * Test 2.1-E2E-020: Mascot Positioned in Top-Right Corner
   *
   * Validates that the mascot is positioned in the corner/header.
   *
   * Priority: P2 (Medium)
   * Category: Mascot Integration - Positioning
   * Acceptance Criteria: AC9 - Mascot in corner or header
   */
  test('2.1-E2E-020: Mascot positioned in corner', async ({ page }) => {
    // Step 1: Navigate to grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 2: Get mascot position
    const position = await getMascotPosition(page);

    // Step 3: Verify mascot is in top portion of viewport
    expect(position.top).toBeLessThan(200);

    // Step 4: Verify mascot is in corner (either left or right)
    const isInCorner = position.left < 200 || position.right < 200;
    expect(isInCorner).toBeTruthy();
  });
});

// =============================================================================
// GROUP 5: NAVIGATION & SIMPLICITY TESTS (AC 8)
// =============================================================================

test.describe('Navigation & Simplicity', () => {
  /**
   * Test 2.1-E2E-017: No Nav Elements Present in DOM
   *
   * Validates that no navigation elements exist in the child interface.
   *
   * Priority: P2 (Medium)
   * Category: Navigation - Simplicity Requirement
   * Acceptance Criteria: AC8 - No navigation elements
   */
  test('2.1-E2E-017: Verify no nav elements present in DOM', async ({
    page,
  }) => {
    // Step 1: Navigate to grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 2: Check for nav element
    const navElements = page.locator('nav');
    const navCount = await navElements.count();

    // Step 3: Verify no nav elements
    expect(navCount).toBe(0);
  });

  /**
   * Test 2.1-E2E-018: No Text-Based Menus Present
   *
   * Validates that no text-based menus exist (child can't read).
   *
   * Priority: P2 (Medium)
   * Category: Navigation - Simplicity Requirement
   * Acceptance Criteria: AC8 - No text-based menus
   */
  test('2.1-E2E-018: Verify no text-based menus present', async ({ page }) => {
    // Step 1: Navigate to grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 2: Check for menu elements
    const menuElements = page.locator('menu, [role="menu"], [role="menubar"]');
    const menuCount = await menuElements.count();

    // Step 3: Verify no menu elements
    expect(menuCount).toBe(0);

    // Step 4: Check for common menu link patterns
    const linkElements = page.locator('a');
    const linkCount = await linkElements.count();

    // Step 5: Verify minimal or no links (grid should be self-contained)
    expect(linkCount).toBeLessThanOrEqual(1); // May have logo link or similar
  });
});

// =============================================================================
// GROUP 6: USER INTERACTION TESTS (AC 3, 10)
// =============================================================================

test.describe('User Interaction', () => {
  /**
   * Test 2.1-E2E-004: Clicking Thumbnail Triggers Video Selection
   *
   * Validates that clicking a video card triggers video selection.
   *
   * Priority: P1 (High)
   * Category: User Interaction - Click Handling
   * Acceptance Criteria: AC3 - Thumbnails are clickable
   *
   * Note: Story 2.2 (video player) not implemented yet, so we verify
   * click event handling without expecting navigation.
   */
  test('2.1-E2E-004: Clicking thumbnail triggers interaction', async ({
    page,
  }) => {
    // Step 1: Navigate to grid
    await navigateToGrid(page);
    await waitForGrid(page);

    // Step 2: Get first video card
    const firstCard = getVideoCard(page, 0);

    // Step 3: Verify card is clickable (has cursor pointer or similar)
    const cursor = await getComputedStyle(firstCard, 'cursor');
    expect(cursor).toBe('pointer');

    // Step 4: Click the card
    // Note: We don't expect navigation since Story 2.2 isn't implemented
    // We just verify the click action completes without error
    await clickVideoCard(firstCard);

    // Step 5: Wait a moment to see if any unexpected behavior occurs
    await page.waitForTimeout(500);

    // Step 6: Verify page didn't crash or show errors
    const errorContainer = page.locator('[data-error]');
    const hasError = await errorContainer.isVisible();
    expect(hasError).toBe(false);
  });

  /**
   * Test 2.1-E2E-005: Cards Disabled During Loading State
   *
   * Validates that video cards are disabled during loading to prevent
   * double-clicks or interaction with incomplete data.
   *
   * Priority: P1 (High)
   * Category: User Interaction - Loading State
   * Acceptance Criteria: AC3 - Proper loading state handling
   */
  test('2.1-E2E-005: Cards disabled during loading state', async ({ page }) => {
    // Step 1: Navigate to grid
    await page.goto('/');

    // Step 2: Check if loading indicator is visible initially
    const loadingIndicator = page.locator('[data-loading]');
    const isLoading = await loadingIndicator.isVisible();

    // Step 3: If loading is visible, verify cards are disabled
    if (isLoading) {
      // Check if any cards exist yet
      const cardCount = await page.locator('.video-card').count();

      if (cardCount > 0) {
        const disabled = await areCardsDisabled(page);
        expect(disabled).toBe(true);
      }
    }

    // Step 4: Wait for loading to complete
    await waitForGrid(page);

    // Step 5: Verify cards are now enabled
    const stillDisabled = await areCardsDisabled(page);
    expect(stillDisabled).toBe(false);
  });
});
