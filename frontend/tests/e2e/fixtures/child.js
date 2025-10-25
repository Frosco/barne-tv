/**
 * Child interface fixtures for E2E tests
 *
 * Provides reusable helpers for child grid testing.
 *
 * Story 2.1 - Child-Friendly Video Grid E2E Tests
 */

/**
 * Navigate to child grid page
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<void>}
 */
export async function navigateToGrid(page) {
  await page.goto('/child/grid');
}

/**
 * Wait for grid to finish loading and render video cards
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {number} timeout - Maximum time to wait in milliseconds (default 10000)
 * @returns {Promise<void>}
 */
export async function waitForGrid(page, timeout = 10000) {
  // Wait for loading indicator to disappear
  await page.waitForSelector('[data-loading]', { state: 'hidden', timeout });

  // Wait for at least one video card to appear
  await page.waitForSelector('.video-card', { state: 'visible', timeout });
}

/**
 * Get all video card elements
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<import('@playwright/test').Locator>} Locator for video cards
 */
export function getVideoCards(page) {
  return page.locator('.video-card');
}

/**
 * Get a specific video card by index
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {number} index - Zero-based index of the card
 * @returns {import('@playwright/test').Locator} Locator for the specific card
 */
export function getVideoCard(page, index) {
  return page.locator('.video-card').nth(index);
}

/**
 * Count number of video cards in the grid
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<number>} Number of video cards
 */
export async function countVideoCards(page) {
  return await page.locator('.video-card').count();
}

/**
 * Get the dimensions of a video card element
 *
 * @param {import('@playwright/test').Locator} card - Locator for a video card
 * @returns {Promise<{width: number, height: number}>} Dimensions in pixels
 */
export async function getCardDimensions(card) {
  const box = await card.boundingBox();
  return {
    width: box?.width || 0,
    height: box?.height || 0,
  };
}

/**
 * Get the dimensions of a thumbnail image
 *
 * @param {import('@playwright/test').Locator} card - Locator for a video card
 * @returns {Promise<{width: number, height: number}>} Dimensions in pixels
 */
export async function getThumbnailDimensions(card) {
  const thumbnail = card.locator('.video-card__thumbnail');
  const box = await thumbnail.boundingBox();
  return {
    width: box?.width || 0,
    height: box?.height || 0,
  };
}

/**
 * Get mascot element
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {import('@playwright/test').Locator} Locator for mascot image
 */
export function getMascotElement(page) {
  return page.locator('.mascot');
}

/**
 * Get mascot position
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<{top: number, right: number, bottom: number, left: number}>} Position in pixels
 */
export async function getMascotPosition(page) {
  const mascot = getMascotElement(page);
  const box = await mascot.boundingBox();
  const viewport = page.viewportSize();

  return {
    top: box?.y || 0,
    right: (viewport?.width || 0) - ((box?.x || 0) + (box?.width || 0)),
    bottom: (viewport?.height || 0) - ((box?.y || 0) + (box?.height || 0)),
    left: box?.x || 0,
  };
}

/**
 * Get computed CSS property value
 *
 * @param {import('@playwright/test').Locator} element - Element locator
 * @param {string} property - CSS property name
 * @returns {Promise<string>} Computed property value
 */
export async function getComputedStyle(element, property) {
  return await element.evaluate((el, prop) => {
    return window.getComputedStyle(el).getPropertyValue(prop);
  }, property);
}

/**
 * Get number of grid columns
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<number>} Number of columns
 */
export async function getGridColumnCount(page) {
  const grid = page.locator('[data-grid]');
  const columns = await grid.evaluate((el) => {
    return window.getComputedStyle(el).gridTemplateColumns.split(' ').length;
  });
  return columns;
}

/**
 * Check if element has specific CSS class
 *
 * @param {import('@playwright/test').Locator} element - Element locator
 * @param {string} className - Class name to check
 * @returns {Promise<boolean>} True if class exists
 */
export async function hasClass(element, className) {
  const classes = await element.getAttribute('class');
  return classes?.includes(className) || false;
}

/**
 * Click video card and wait for navigation/event
 *
 * @param {import('@playwright/test').Locator} card - Video card locator
 * @returns {Promise<void>}
 */
export async function clickVideoCard(card) {
  await card.click();
}

/**
 * Check if cards are in disabled/loading state
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<boolean>} True if cards are disabled
 */
export async function areCardsDisabled(page) {
  const firstCard = page.locator('.video-card').first();
  const isDisabled = await firstCard.evaluate((el) => {
    return (
      el.hasAttribute('disabled') ||
      el.classList.contains('disabled') ||
      el.style.pointerEvents === 'none'
    );
  });
  return isDisabled;
}

/**
 * Refresh the page and wait for grid to reload
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<void>}
 */
export async function refreshGrid(page) {
  await page.reload();
  await waitForGrid(page);
}

/**
 * Get all video titles from the grid
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<string[]>} Array of video titles
 */
export async function getVideoTitles(page) {
  const titles = await page.locator('.video-card__title').allTextContents();
  return titles;
}

/**
 * Check if error message is displayed
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<boolean>} True if error is visible
 */
export async function isErrorDisplayed(page) {
  const errorContainer = page.locator('[data-error]');
  return await errorContainer.isVisible();
}
