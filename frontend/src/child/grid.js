/**
 * Video grid rendering and interaction logic for child interface.
 *
 * TIER 1 Rule 5: XSS Prevention
 * - Always use textContent not innerHTML for user data
 * - Create elements with createElement() not string concatenation
 *
 * TIER 2 Rule 9: Always handle fetch errors
 * - Wrap all API calls in try/catch
 * - Show user-friendly error messages
 *
 * TIER 3 Rule 14: Norwegian user messages
 */

// Module state
let currentVideos = [];
let dailyLimit = null;
let isLoading = false;

/**
 * Initialize the video grid when page loads.
 * Called by child.js entry point.
 */
export function initGrid() {
  console.log('Initializing video grid...');

  // Load videos on init
  loadVideos();

  // Attach retry button listener
  const retryBtn = document.querySelector('[data-retry]');
  if (retryBtn) {
    retryBtn.addEventListener('click', () => {
      hideError();
      loadVideos();
    });
  }
}

/**
 * Fetch videos from API and render the grid.
 *
 * TIER 2 Rule 9: Always handle fetch errors
 * TIER 3 Rule 14: Norwegian error messages
 */
export async function loadVideos() {
  if (isLoading) return;

  isLoading = true;
  showLoading();

  try {
    // Fetch videos from backend API
    const response = await fetch('/api/videos?count=9');

    // TIER 2 Rule 9: Check response status
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Noe gikk galt');
    }

    const data = await response.json();

    // Store data in module state
    currentVideos = data.videos || [];
    dailyLimit = data.dailyLimit || null;

    // Render the grid
    hideLoading();
    renderGrid(currentVideos);
  } catch (error) {
    // TIER 2 Rule 9: Handle all errors gracefully
    console.error('Failed to load videos:', error);
    hideLoading();
    // TIER 3 Rule 14: Norwegian error message
    showError(error.message || 'Noe gikk galt');
  } finally {
    isLoading = false;
  }
}

/**
 * Render video cards in the grid.
 *
 * TIER 1 Rule 5: XSS Prevention
 * - Use createElement() not innerHTML
 * - Use textContent not innerHTML for titles
 * - Set attributes via properties not string concatenation
 *
 * @param {Array} videos - Array of video objects from API
 */
export function renderGrid(videos) {
  const gridContainer = document.querySelector('[data-grid]');
  if (!gridContainer) {
    console.error('Grid container not found');
    return;
  }

  // Clear existing content
  gridContainer.innerHTML = '';

  // Show message if no videos
  if (!videos || videos.length === 0) {
    const emptyMessage = document.createElement('div');
    emptyMessage.className = 'grid-empty';
    // TIER 1 Rule 5: Use textContent for XSS prevention
    emptyMessage.textContent =
      'Ingen videoer tilgjengelig. Be foreldrene legge til kanaler.';
    gridContainer.appendChild(emptyMessage);
    return;
  }

  // Create video cards
  videos.forEach((video) => {
    const card = createVideoCard(video);
    gridContainer.appendChild(card);
  });

  // Attach click listeners to all cards
  attachCardListeners();
}

/**
 * Create a single video card element.
 *
 * TIER 1 Rule 5: XSS Prevention - all elements created with createElement()
 *
 * @param {Object} video - Video object with videoId, title, thumbnailUrl, etc.
 * @returns {HTMLElement} Video card element
 */
function createVideoCard(video) {
  // Create card container
  const card = document.createElement('div');
  card.className = 'video-card';
  card.setAttribute('role', 'listitem');
  card.setAttribute('tabindex', '0');

  // TIER 1 Rule 5: Set data attributes via setAttribute (safe)
  card.dataset.videoId = video.videoId;
  card.dataset.durationSeconds = video.durationSeconds;

  // Create thumbnail image
  const thumbnail = document.createElement('div');
  thumbnail.className = 'video-card__thumbnail';

  const img = document.createElement('img');
  img.src = video.thumbnailUrl;
  img.alt = ''; // Decorative image, title is in text below
  img.loading = 'lazy';

  thumbnail.appendChild(img);

  // Create title
  const titleEl = document.createElement('h3');
  titleEl.className = 'video-card__title';
  // TIER 1 Rule 5: Use textContent not innerHTML for XSS prevention
  titleEl.textContent = video.title;

  // Create channel name
  const channelEl = document.createElement('p');
  channelEl.className = 'video-card__channel';
  // TIER 1 Rule 5: Use textContent not innerHTML
  channelEl.textContent = video.youtubeChannelName;

  // Assemble card
  card.appendChild(thumbnail);
  card.appendChild(titleEl);
  card.appendChild(channelEl);

  return card;
}

/**
 * Attach click and keyboard event listeners to video cards.
 */
function attachCardListeners() {
  const cards = document.querySelectorAll('.video-card');

  cards.forEach((card) => {
    // Click event
    card.addEventListener('click', handleCardClick);

    // Keyboard event (Enter or Space)
    card.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        handleCardClick(event);
      }
    });
  });
}

/**
 * Handle video card click/activation.
 *
 * Disables all cards during loading to prevent double-clicks.
 * Emits custom event that player module will listen for (Story 2.2).
 *
 * @param {Event} event - Click or keyboard event
 */
function handleCardClick(event) {
  if (isLoading) return;

  const card = event.currentTarget;
  const videoId = card.dataset.videoId;
  const durationSeconds = card.dataset.durationSeconds;

  console.log(`Video card clicked: ${videoId}`);

  // Disable all cards during loading
  disableCards();

  // Emit custom event for player module (Story 2.2)
  const playEvent = new CustomEvent('video:play', {
    detail: {
      videoId,
      durationSeconds: parseInt(durationSeconds, 10),
    },
  });
  document.dispatchEvent(playEvent);

  // For now, just log (Story 2.2 will implement player)
  console.log('Play event dispatched:', playEvent.detail);

  // Re-enable cards after a short delay (Story 2.2 will handle this properly)
  setTimeout(() => {
    enableCards();
  }, 500);
}

/**
 * Disable all video cards (prevent interaction during loading).
 */
function disableCards() {
  const cards = document.querySelectorAll('.video-card');
  cards.forEach((card) => {
    card.style.pointerEvents = 'none';
    card.style.opacity = '0.6';
    card.setAttribute('aria-disabled', 'true');
  });
}

/**
 * Re-enable all video cards.
 */
function enableCards() {
  const cards = document.querySelectorAll('.video-card');
  cards.forEach((card) => {
    card.style.pointerEvents = '';
    card.style.opacity = '';
    card.removeAttribute('aria-disabled');
  });
}

/**
 * Show loading state in grid.
 */
function showLoading() {
  const loading = document.querySelector('[data-loading]');
  if (loading) {
    loading.hidden = false;
  }
}

/**
 * Hide loading state.
 */
function hideLoading() {
  const loading = document.querySelector('[data-loading]');
  if (loading) {
    loading.hidden = true;
  }
}

/**
 * Show error message in grid.
 *
 * TIER 3 Rule 14: Norwegian error message
 *
 * @param {string} message - Norwegian error message
 */
function showError(message) {
  const errorContainer = document.querySelector('[data-error]');
  const errorMessage = document.querySelector('[data-error-message]');

  if (errorContainer && errorMessage) {
    // TIER 1 Rule 5: Use textContent for XSS prevention
    errorMessage.textContent = message;
    errorContainer.hidden = false;
  }

  // Update mascot to confused state
  const mascot = document.querySelector('[data-mascot-state]');
  if (mascot) {
    mascot.src = '/images/mascot/owl_confused.png';
    mascot.dataset.mascotState = 'confused';
  }
}

/**
 * Hide error message.
 */
function hideError() {
  const errorContainer = document.querySelector('[data-error]');
  if (errorContainer) {
    errorContainer.hidden = true;
  }

  // Reset mascot to neutral state
  const mascot = document.querySelector('[data-mascot-state]');
  if (mascot) {
    mascot.src = '/images/mascot/owl_neutral.png';
    mascot.dataset.mascotState = 'neutral';
  }
}

/**
 * Get current daily limit state (for other modules).
 *
 * @returns {Object|null} Daily limit object or null
 */
export function getDailyLimit() {
  return dailyLimit;
}
