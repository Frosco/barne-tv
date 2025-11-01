/**
 * Child Limit Tracker Module (Story 4.1, Task 7)
 *
 * Handles:
 * - Polling /api/limit/status every 30 seconds
 * - In-memory state management (no localStorage per TIER 3 Rule 15)
 * - Event emission for state changes
 * - Page Visibility API (pause when tab hidden)
 * - Error handling with backoff
 */

// In-memory state (no localStorage per TIER 3 Rule 15)
let currentState = null;
let pollInterval = null;
let pollIntervalDuration = 30000; // 30 seconds default
let consecutiveErrors = 0;
let isVisible = true;

/**
 * Initialize limit tracker with polling.
 */
export function initLimitTracker() {
  // Initial fetch
  fetchLimitStatus();

  // Start polling
  startPolling();

  // Set up Page Visibility API
  setupVisibilityListener();
}

/**
 * Start polling for limit status.
 */
function startPolling() {
  // Clear any existing interval
  if (pollInterval) {
    clearInterval(pollInterval);
  }

  // Only poll if page is visible
  if (!isVisible) {
    return;
  }

  pollInterval = setInterval(() => {
    // Only fetch if page is visible
    if (isVisible) {
      fetchLimitStatus();
    }
  }, pollIntervalDuration);
}

/**
 * Stop polling.
 */
function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
}

/**
 * Fetch limit status from API.
 */
async function fetchLimitStatus() {
  try {
    const response = await fetch('/api/limit/status');

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const limitData = await response.json();

    // Reset error count on success
    consecutiveErrors = 0;

    // Reset poll interval to normal if it was increased
    if (pollIntervalDuration !== 30000) {
      pollIntervalDuration = 30000;
      startPolling(); // Restart with normal interval
    }

    // Check for state changes and emit events
    handleLimitData(limitData);
  } catch (error) {
    console.error('Error fetching limit status:', error);
    handleFetchError();
  }
}

/**
 * Handle limit data and emit events for state changes.
 *
 * @param {Object} limitData - Limit status data from API
 */
function handleLimitData(limitData) {
  const previousState = currentState;
  const newState = limitData.currentState;

  // Update in-memory state
  currentState = limitData;

  // Emit event if state changed
  if (previousState && previousState.currentState !== newState) {
    emitEvent('limitStateChanged', {
      previousState: previousState.currentState,
      newState: newState,
      limitData: limitData,
    });

    // Special event for grace limit reached
    if (newState === 'grace') {
      emitEvent('graceLimitReached', { limitData });
    }
  }
}

/**
 * Handle fetch errors with backoff strategy.
 */
function handleFetchError() {
  consecutiveErrors++;

  // After 3 consecutive failures, increase polling interval to 60 seconds
  if (consecutiveErrors >= 3 && pollIntervalDuration === 30000) {
    console.warn(
      '3 consecutive limit status fetch failures, increasing poll interval to 60s'
    );
    pollIntervalDuration = 60000;
    startPolling(); // Restart with increased interval
  }
}

/**
 * Emit custom event.
 *
 * @param {string} eventName - Name of the event to emit
 * @param {Object} detail - Event detail data
 */
function emitEvent(eventName, detail) {
  const event = new CustomEvent(eventName, {
    detail,
    bubbles: true,
    cancelable: false,
  });

  window.dispatchEvent(event);
}

/**
 * Set up Page Visibility API listener.
 * Pauses polling when tab is hidden, resumes when visible.
 */
function setupVisibilityListener() {
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      // Tab is hidden - stop polling
      isVisible = false;
      stopPolling();
    } else {
      // Tab is visible - resume polling
      isVisible = true;
      // Fetch immediately when becoming visible
      fetchLimitStatus();
      // Restart polling
      startPolling();
    }
  });
}

/**
 * Get current limit state (in-memory).
 *
 * @returns {Object|null} Current limit state or null if not yet fetched
 */
export function getCurrentState() {
  return currentState;
}

/**
 * Clean up (stop polling).
 * Useful for testing or cleanup.
 */
export function cleanup() {
  stopPolling();
  currentState = null;
  consecutiveErrors = 0;
  pollIntervalDuration = 30000;
}
