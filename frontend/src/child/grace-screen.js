/**
 * Grace screen handling for Story 4.3, audio added in Story 4.5.
 *
 * Manages the grace video selection screen shown when daily limit is reached.
 * Child can choose one final grace video (≤5 minutes) or finish for the day.
 *
 * TIER 2 Rule 9: Always handle API errors gracefully
 * TIER 3 Rule 14: Norwegian UI messages
 */

// Story 4.5: Audio feedback
import { playGraceNotification } from './audio-manager.js';

/**
 * Calculate time remaining until midnight UTC.
 *
 * TIER 1 Rule 3: Always use UTC for time calculations.
 *
 * @returns {string} Formatted Norwegian string: "X timer og Y minutter"
 */
export function calculateTimeUntilReset() {
  const now = new Date();

  // Calculate midnight UTC tomorrow
  const midnightUTC = new Date(now);
  midnightUTC.setUTCHours(24, 0, 0, 0);

  // Calculate difference
  const diff = midnightUTC - now;
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

  // Format in Norwegian
  if (hours > 0) {
    return `${hours} timer og ${minutes} minutter`;
  } else {
    return `${minutes} minutter`;
  }
}

/**
 * Show inline error message with mascot image.
 *
 * TIER 1 Rule 5: Use createElement and textContent to prevent XSS
 * TIER 3 Rule 14: Norwegian UI messages
 *
 * @param {string} message - Norwegian error message to display
 */
function showInlineError(message) {
  // Find grace content container
  const graceContent = document.querySelector('.grace-content');
  if (!graceContent) {
    console.error('Grace content container not found');
    return;
  }

  // Remove any existing error
  const existingError = graceContent.querySelector('.grace-error');
  if (existingError) {
    existingError.remove();
  }

  // Create error container
  const errorContainer = document.createElement('div');
  errorContainer.className = 'grace-error';
  errorContainer.setAttribute('role', 'alert');
  errorContainer.setAttribute('aria-live', 'assertive');

  // Create mascot image (shrug for errors)
  const mascotImg = document.createElement('img');
  mascotImg.src = '/images/mascot/mascot-shrug.png';
  mascotImg.alt = '';
  mascotImg.className = 'grace-error__mascot';

  // Create message text
  const messageEl = document.createElement('p');
  messageEl.className = 'grace-error__message';
  messageEl.textContent = message;

  // Assemble error
  errorContainer.appendChild(mascotImg);
  errorContainer.appendChild(messageEl);

  // Add to DOM
  graceContent.appendChild(errorContainer);

  // Auto-dismiss after 5 seconds
  setTimeout(() => {
    if (errorContainer.parentNode) {
      errorContainer.remove();
    }
  }, 5000);
}

/**
 * Fetch grace videos from API.
 *
 * Grace videos are filtered to max 5 minutes duration, limited to 6 videos.
 *
 * TIER 2 Rule 9: Handle API errors gracefully
 *
 * @returns {Promise<Array>} Array of video objects, or empty array on error
 */
async function fetchGraceVideos() {
  try {
    const response = await fetch('/api/videos?count=6');

    if (!response.ok) {
      console.error('Failed to fetch grace videos:', response.status);
      return [];
    }

    const data = await response.json();
    return data.videos || [];
  } catch (error) {
    console.error('Grace video fetch network error:', error);
    return [];
  }
}

/**
 * Render grace video grid (4-6 videos).
 *
 * Creates video cards for grace video selection.
 * Uses same card structure as main grid but fewer videos.
 *
 * @param {Array} videos - Array of video objects
 */
function renderGraceGrid(videos) {
  const gridContainer = document.getElementById('grace-video-grid');

  if (!gridContainer) {
    console.error('Grace video grid container not found');
    return;
  }

  // Clear existing content
  gridContainer.innerHTML = '';

  if (videos.length === 0) {
    // No videos available - show message
    const message = document.createElement('p');
    message.className = 'grace-screen__no-videos';
    message.textContent =
      'Ingen videoer tilgjengelig akkurat nå. Prøv "Nei, ha det!" knappen.';
    gridContainer.appendChild(message);
    gridContainer.style.display = 'block';
    return;
  }

  // Create video cards
  videos.forEach((video) => {
    const card = createGraceVideoCard(video);
    gridContainer.appendChild(card);
  });

  // Show grid
  gridContainer.style.display = 'grid';
}

/**
 * Create a single grace video card.
 *
 * TIER 1 Rule 5: Use createElement and textContent to prevent XSS
 *
 * @param {Object} video - Video object with videoId, title, thumbnailUrl, durationSeconds
 * @returns {HTMLElement} Video card element
 */
function createGraceVideoCard(video) {
  const card = document.createElement('div');
  card.className = 'video-card video-card--grace';
  card.dataset.videoId = video.videoId;
  card.dataset.duration = video.durationSeconds;

  // Thumbnail
  const thumbnail = document.createElement('img');
  thumbnail.src = video.thumbnailUrl;
  thumbnail.alt = '';
  thumbnail.className = 'video-card__thumbnail';

  // Title
  const title = document.createElement('h3');
  title.className = 'video-card__title';
  title.textContent = video.title;

  // Duration
  const duration = document.createElement('span');
  duration.className = 'video-card__duration';
  const minutes = Math.ceil(video.durationSeconds / 60);
  duration.textContent = `${minutes} min`;

  card.appendChild(thumbnail);
  card.appendChild(title);
  card.appendChild(duration);

  // Add click handler for grace video selection
  card.addEventListener('click', () => handleGraceVideoSelection(video));

  return card;
}

/**
 * Handle grace video selection.
 *
 * Navigates to video player with gracePlay flag.
 *
 * @param {Object} video - Selected video object
 */
function handleGraceVideoSelection(video) {
  // Navigate to player with grace flag
  window.location.href = `/video/${video.videoId}?gracePlay=true`;
}

/**
 * Handle "Ja, én til!" button click.
 *
 * Fetches and displays grace videos.
 */
async function handleGraceAccept() {
  const yesButton = document.getElementById('grace-yes-btn');
  const noButton = document.getElementById('grace-no-btn');
  const mascotContainer = document.querySelector('.grace-screen__mascot');
  const message = document.querySelector('.grace-screen__message');

  // Disable buttons to prevent double-click
  yesButton.disabled = true;
  noButton.disabled = true;
  yesButton.textContent = 'Laster...';

  // Fetch grace videos
  const videos = await fetchGraceVideos();

  if (videos.length === 0) {
    // No videos available - show inline error with mascot
    yesButton.textContent = 'Ja, én til! 🎉';
    yesButton.disabled = false;
    noButton.disabled = false;

    showInlineError(
      'Ingen videoer tilgjengelig akkurat nå. Prøv igjen eller velg "Nei, ha det!"'
    );
    return;
  }

  // Hide mascot and message, show grace grid
  if (mascotContainer) mascotContainer.style.display = 'none';
  if (message) message.style.display = 'none';
  yesButton.style.display = 'none';
  noButton.style.display = 'none';

  // Render grace video grid
  renderGraceGrid(videos);
}

/**
 * Handle "Nei, ha det!" button click.
 *
 * Navigates to goodbye screen.
 */
function handleGraceDecline() {
  window.location.href = '/goodbye';
}

/**
 * Initialize grace screen.
 *
 * Sets up button handlers and countdown display.
 */
export function initGraceScreen() {
  // Story 4.5: Play grace notification sound when grace screen is displayed
  playGraceNotification();

  const yesButton = document.getElementById('grace-yes-btn');
  const noButton = document.getElementById('grace-no-btn');
  const countdownElement = document.getElementById('time-until-reset');

  // Attach button handlers
  if (yesButton) {
    yesButton.addEventListener('click', handleGraceAccept);
  }

  if (noButton) {
    noButton.addEventListener('click', handleGraceDecline);
  }

  // Update countdown display
  function updateCountdown() {
    if (countdownElement) {
      countdownElement.textContent = calculateTimeUntilReset();
    }
  }

  // Initial update
  updateCountdown();

  // Update every minute
  setInterval(updateCountdown, 60000);
}
