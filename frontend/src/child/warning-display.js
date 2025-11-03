/**
 * Warning Display Component (Story 4.2, Task 6 | Story 4.3, Task 10)
 *
 * Displays progressive time limit warnings to the child:
 * - 10 minutes remaining
 * - 5 minutes remaining
 * - 2 minutes remaining
 *
 * Features:
 * - Auto-dismisses after 3 seconds
 * - Logs warnings to backend for parent review
 * - Plays audio chime (stub)
 * - Shows mascot PNG images (Story 4.3)
 * - Norwegian messages
 */

import { playWarningChime, isAudioEnabled } from './audio-manager.js';

// Warning configuration
const WARNING_CONFIG = {
  '10min': {
    title: '10 minutter igjen!',
    message: 'Du har god tid igjen! 😊',
    mascotImage: '/images/mascot/mascot-happy.png', // Story 4.3: Actual mascot PNG
    className: 'warning--10min',
  },
  '5min': {
    title: '5 minutter igjen!',
    message: 'Snart er tiden ute, velg en kort video!',
    mascotImage: '/images/mascot/mascot-curious.png', // Story 4.3: Curious mascot for urgency
    className: 'warning--5min',
  },
  '2min': {
    title: '2 minutter igjen!',
    message: 'Bare 2 minutter igjen!',
    mascotImage: '/images/mascot/mascot-curious.png', // Story 4.3: Curious mascot for final warning
    className: 'warning--2min',
  },
};

// Auto-dismiss timeout (3 seconds)
const AUTO_DISMISS_MS = 3000;

// Active warning timeout ID
let dismissTimeout = null;

/**
 * Show warning overlay.
 *
 * @param {string} warningType - Type of warning ('10min', '5min', '2min')
 */
export function showWarning(warningType) {
  const config = WARNING_CONFIG[warningType];

  if (!config) {
    console.error(`Invalid warning type: ${warningType}`);
    return;
  }

  // Play audio chime if enabled
  if (isAudioEnabled()) {
    playWarningChime(warningType);
  }

  // Create warning overlay
  const overlay = createWarningOverlay(config);

  // Add to DOM
  document.body.appendChild(overlay);

  // Trigger animation (add active class after DOM insertion)
  requestAnimationFrame(() => {
    overlay.classList.add('warning-overlay--active');
  });

  // Log warning to backend (non-blocking)
  logWarningToBackend(warningType);

  // Auto-dismiss after 3 seconds
  dismissTimeout = setTimeout(() => {
    dismissWarning(overlay);
  }, AUTO_DISMISS_MS);
}

/**
 * Create warning overlay DOM element.
 *
 * TIER 1 Rule 5: Use createElement and textContent to prevent XSS (Story 4.3)
 *
 * @param {Object} config - Warning configuration
 * @returns {HTMLElement} Warning overlay element
 */
function createWarningOverlay(config) {
  const overlay = document.createElement('div');
  overlay.className = `warning-overlay ${config.className}`;
  overlay.setAttribute('role', 'alert');
  overlay.setAttribute('aria-live', 'assertive');

  // Create content container
  const content = document.createElement('div');
  content.className = 'warning-overlay__content';

  // Create mascot image container (Story 4.3)
  const mascotContainer = document.createElement('div');
  mascotContainer.className = 'warning-overlay__mascot';
  mascotContainer.setAttribute('aria-hidden', 'true');

  const mascotImg = document.createElement('img');
  mascotImg.src = config.mascotImage;
  mascotImg.alt = 'Maskot';
  mascotImg.className = 'warning-overlay__mascot-img';

  mascotContainer.appendChild(mascotImg);

  // Create text container
  const textContainer = document.createElement('div');
  textContainer.className = 'warning-overlay__text';

  const title = document.createElement('h2');
  title.className = 'warning-overlay__title';
  title.textContent = config.title;

  const message = document.createElement('p');
  message.className = 'warning-overlay__message';
  message.textContent = config.message;

  textContainer.appendChild(title);
  textContainer.appendChild(message);

  // Assemble structure
  content.appendChild(mascotContainer);
  content.appendChild(textContainer);
  overlay.appendChild(content);

  // Allow manual dismissal by clicking
  overlay.addEventListener('click', () => {
    dismissWarning(overlay);
  });

  return overlay;
}

/**
 * Dismiss warning overlay.
 *
 * @param {HTMLElement} overlay - Warning overlay element to dismiss
 */
function dismissWarning(overlay) {
  // Clear auto-dismiss timeout if it exists
  if (dismissTimeout) {
    clearTimeout(dismissTimeout);
    dismissTimeout = null;
  }

  // Fade out animation
  overlay.classList.remove('warning-overlay--active');
  overlay.classList.add('warning-overlay--dismissing');

  // Remove from DOM after animation completes
  setTimeout(() => {
    if (overlay.parentNode) {
      overlay.parentNode.removeChild(overlay);
    }
  }, 300); // Match CSS transition duration
}

/**
 * Log warning to backend for parent review.
 *
 * Non-blocking: Errors are logged to console but don't affect UX.
 *
 * @param {string} warningType - Type of warning ('10min', '5min', '2min')
 */
async function logWarningToBackend(warningType) {
  try {
    const shownAt = new Date().toISOString();

    const response = await fetch('/api/warnings/log', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        warningType,
        shownAt,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    console.log(`Logged ${warningType} warning to backend`);
  } catch (error) {
    // Non-blocking: Log error but don't disrupt UX
    console.error('Failed to log warning to backend:', error);
  }
}

/**
 * Initialize warning display system.
 *
 * Sets up event listeners for warningTriggered events from limit-tracker.
 */
export function initWarningDisplay() {
  // Listen for warningTriggered events from limit-tracker
  window.addEventListener('warningTriggered', (event) => {
    const { warningType } = event.detail;
    showWarning(warningType);
  });

  console.log('Warning display system initialized');
}

/**
 * Clean up (for testing).
 */
export function cleanup() {
  // Clear any active dismiss timeout
  if (dismissTimeout) {
    clearTimeout(dismissTimeout);
    dismissTimeout = null;
  }

  // Remove any active warning overlays
  const overlays = document.querySelectorAll('.warning-overlay');
  overlays.forEach((overlay) => {
    if (overlay.parentNode) {
      overlay.parentNode.removeChild(overlay);
    }
  });
}
