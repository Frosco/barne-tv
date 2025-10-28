/**
 * YouTube Player Component (Story 2.2)
 *
 * Handles video playback using YouTube IFrame Player API.
 * Tracks watch duration, handles errors, and manages state-based navigation.
 *
 * TIER 1 Safety Rules:
 * - ESC key MUST NOT log watch history (cancelled playback)
 * - Back button DOES log partial watch with actual duration
 * - Error codes 100/150 mark video globally unavailable
 *
 * TIER 2 Rules:
 * - All API calls wrapped in try/catch with Norwegian error messages
 * - Consistent response handling
 *
 * TIER 3 Rules:
 * - Norwegian user messages
 * - No localStorage/sessionStorage
 */

// Player state
let playerInstance = null;
let startTime = null;
let bufferingTimer = null;
let videoId = null;
let playerContainer = null;

/**
 * Load YouTube IFrame API script if not already loaded.
 * Returns a Promise that resolves when API is ready.
 * Exported for testing purposes.
 */
export function loadYouTubeAPI() {
  return new Promise((resolve, reject) => {
    // Check if API already loaded
    if (window.YT && window.YT.Player) {
      resolve();
      return;
    }

    // Check if script tag already exists
    if (document.querySelector('script[src*="youtube.com/iframe_api"]')) {
      // Script loading, wait for callback
      window.onYouTubeIframeAPIReady = resolve;
      return;
    }

    // Load API script
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    tag.onerror = () => reject(new Error('Failed to load YouTube IFrame API'));

    // Insert script tag
    const firstScriptTag = document.getElementsByTagName('script')[0];
    if (firstScriptTag && firstScriptTag.parentNode) {
      firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
    } else {
      // Fallback: append to head or body
      (document.head || document.body).appendChild(tag);
    }

    // Set global callback
    window.onYouTubeIframeAPIReady = resolve;
  });
}

/**
 * Create YouTube player with autoplay and minimal chrome.
 *
 * @param {string} vid - YouTube video ID (11 characters)
 * @param {HTMLElement} container - Container element for player
 * @returns {Promise<Object>} Player instance
 */
export async function createPlayer(vid, container) {
  try {
    // Load YouTube API
    await loadYouTubeAPI();

    // Store references
    videoId = vid;
    playerContainer = container;
    startTime = Date.now();

    // Create player element
    const playerDiv = document.createElement('div');
    playerDiv.id = 'youtube-player';
    container.appendChild(playerDiv);

    // Create Back to Videos button
    const backButton = document.createElement('button');
    backButton.className = 'player__back-button';
    backButton.textContent = 'Tilbake til videoer';
    backButton.setAttribute('data-back-button', '');
    backButton.addEventListener('click', handleBackButtonClick);
    container.appendChild(backButton);

    // Create error overlay (hidden by default)
    const errorOverlay = document.createElement('div');
    errorOverlay.className = 'player__error-overlay';
    errorOverlay.style.display = 'none';
    errorOverlay.setAttribute('data-error-overlay', '');
    container.appendChild(errorOverlay);

    // Handle ESC key globally - MUST be added before player creation
    // so it works even if player constructor fails
    document.addEventListener('keydown', handleEscKey);

    // Create player with YouTube IFrame API
    playerInstance = new window.YT.Player('youtube-player', {
      videoId: vid,
      playerVars: {
        autoplay: 1, // Start playing immediately
        rel: 0, // Don't show related videos
        modestbranding: 1, // Minimal YouTube branding
        controls: 1, // Show player controls
        fs: 1, // Allow fullscreen
        iv_load_policy: 3, // Don't show video annotations
      },
      events: {
        onReady: onPlayerReady,
        onStateChange: onPlayerStateChange,
        onError: onPlayerError,
      },
    });

    return playerInstance;
  } catch (error) {
    console.error('Error creating player:', error);
    showErrorOverlay('Noe gikk galt med videospilleren', false);
    throw error;
  }
}

/**
 * Player ready event handler.
 * Request fullscreen or fallback to viewport maximization.
 */
function onPlayerReady() {
  // Try to request fullscreen
  const iframe = document.querySelector('#youtube-player');
  if (iframe) {
    // Try native fullscreen API
    if (iframe.requestFullscreen) {
      iframe.requestFullscreen().catch(() => {
        // Fallback to viewport maximization
        applyFullscreenFallback(iframe);
      });
    } else {
      // No fullscreen API, use fallback
      applyFullscreenFallback(iframe);
    }
  }
}

/**
 * Apply fullscreen fallback styling (100vw x 100vh).
 */
function applyFullscreenFallback(element) {
  element.style.width = '100vw';
  element.style.height = '100vh';
  element.style.position = 'fixed';
  element.style.top = '0';
  element.style.left = '0';
  element.style.zIndex = '9999';
}

/**
 * Player state change event handler.
 * Handles video end, buffering timeout detection.
 */
function onPlayerStateChange(event) {
  const state = event.data;

  // Video ended - log complete watch and navigate
  if (state === window.YT.PlayerState.ENDED) {
    handleVideoComplete();
  }

  // Buffering state - start 30-second timeout timer
  if (state === window.YT.PlayerState.BUFFERING) {
    if (!bufferingTimer) {
      bufferingTimer = setTimeout(() => {
        // Still buffering after 30 seconds - show network error
        showErrorOverlay('Videoene trenger internett', false);
      }, 30000); // 30 seconds
    }
  } else {
    // Clear buffering timer if playback resumed
    if (bufferingTimer) {
      clearTimeout(bufferingTimer);
      bufferingTimer = null;
    }
  }
}

/**
 * Player error event handler.
 * Handles YouTube error codes: 2, 5, 100, 150, 153.
 */
function onPlayerError(event) {
  const errorCode = event.data;
  console.error('YouTube Player Error:', errorCode);

  // Error codes 100/150: Video not found or embedding restricted
  if (errorCode === 100 || errorCode === 150) {
    // Mark video unavailable
    markVideoUnavailable();
    // Show error with auto-return
    showErrorOverlay('Oops! Det videoen gjemmer seg!', true);
  }
  // Error code 2: Invalid parameter
  else if (errorCode === 2) {
    console.error('Invalid video parameter');
    showErrorOverlay('Noe gikk galt. Prøv igjen.', true);
  }
  // Error code 5: HTML5 player error
  else if (errorCode === 5) {
    showErrorOverlay('Videoene trenger internett', false);
  }
  // Error code 153: Missing HTTP Referer
  else if (errorCode === 153) {
    console.error('Missing API Client identification');
    showErrorOverlay('Noe gikk galt. Prøv igjen.', true);
  }
  // Unknown error
  else {
    showErrorOverlay('Noe gikk galt. Prøv igjen.', true);
  }
}

/**
 * Handle video completion (video played to end).
 * Log complete watch and navigate based on daily limit state.
 */
async function handleVideoComplete() {
  if (!startTime || !videoId) return;

  try {
    // Calculate duration watched
    const durationMs = Date.now() - startTime;
    const durationSeconds = Math.floor(durationMs / 1000);

    // Log watch history
    const response = await fetch('/api/videos/watch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        videoId: videoId,
        completed: true,
        durationWatchedSeconds: durationSeconds,
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to log watch');
    }

    const data = await response.json();
    const dailyLimit = data.dailyLimit;

    // Destroy player
    destroyPlayer();

    // Navigate based on daily limit state
    if (dailyLimit.currentState === 'grace') {
      window.location.href = '/grace';
    } else if (dailyLimit.currentState === 'locked') {
      window.location.href = '/goodbye';
    } else {
      // Normal or winddown: Return to grid with new videos
      await returnToGrid(true);
    }
  } catch (error) {
    console.error('Error handling video completion:', error);
    showErrorOverlay('Noe gikk galt', false);
  }
}

/**
 * Handle Back button click.
 * Log partial watch and navigate based on daily limit state.
 */
async function handleBackButtonClick() {
  if (!startTime || !videoId) return;

  try {
    // Calculate duration watched
    const durationMs = Date.now() - startTime;
    const durationSeconds = Math.floor(durationMs / 1000);

    // Log watch history
    const response = await fetch('/api/videos/watch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        videoId: videoId,
        completed: false,
        durationWatchedSeconds: durationSeconds,
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to log watch');
    }

    const data = await response.json();
    const dailyLimit = data.dailyLimit;

    // Destroy player
    destroyPlayer();

    // Navigate based on daily limit state
    if (dailyLimit.currentState === 'grace') {
      window.location.href = '/grace';
    } else if (dailyLimit.currentState === 'locked') {
      window.location.href = '/goodbye';
    } else {
      // Normal or winddown: Return to grid with new videos
      await returnToGrid(true);
    }
  } catch (error) {
    console.error('Error handling back button:', error);
    showErrorOverlay('Noe gikk galt', false);
  }
}

/**
 * Handle ESC key press.
 * CRITICAL: MUST NOT log watch history (cancelled playback).
 * Returns to grid without fetching new videos.
 */
function handleEscKey(event) {
  if (event.key === 'Escape' || event.keyCode === 27) {
    // TIER 1 Safety Rule: ESC key MUST NOT log watch history
    console.log('ESC key pressed - cancelling playback without logging');
    destroyPlayer();
    returnToGrid(false); // Don't fetch new videos
  }
}

/**
 * Mark video as unavailable via API.
 * Called when YouTube returns error codes 100/150.
 */
async function markVideoUnavailable() {
  if (!videoId) return;

  try {
    const response = await fetch('/api/videos/unavailable', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ videoId: videoId }),
    });

    if (!response.ok) {
      console.error('Failed to mark video unavailable');
    } else {
      console.log(`Marked video ${videoId} as unavailable`);
    }
  } catch (error) {
    console.error('Error marking video unavailable:', error);
  }
}

/**
 * Show error overlay with mascot and message.
 *
 * @param {string} message - Norwegian error message
 * @param {boolean} autoReturn - If true, auto-return to grid after 5 seconds
 */
function showErrorOverlay(message, autoReturn) {
  const overlay = playerContainer?.querySelector('[data-error-overlay]');
  if (!overlay) return;

  // Build overlay content
  overlay.innerHTML = `
    <div class="error-overlay__content">
      <img src="/images/mascot/owl_confused.png" alt="Owl mascot" class="error-overlay__mascot" />
      <p class="error-overlay__message">${message}</p>
      ${!autoReturn ? '<button class="error-overlay__button" data-error-return>Tilbake til videoer</button>' : ''}
    </div>
  `;

  overlay.style.display = 'flex';

  // Auto-return after 5 seconds
  if (autoReturn) {
    setTimeout(async () => {
      destroyPlayer();
      await returnToGrid(true);
    }, 5000);
  } else {
    // Manual return button
    const returnButton = overlay.querySelector('[data-error-return]');
    if (returnButton) {
      returnButton.addEventListener('click', async () => {
        destroyPlayer();
        await returnToGrid(true);
      });
    }
  }
}

/**
 * Return to grid view.
 *
 * @param {boolean} fetchNewVideos - If true, fetch new random videos. If false, show existing grid.
 */
function returnToGrid(fetchNewVideos) {
  // Clear error overlay if present
  const errorOverlay = playerContainer?.querySelector('[data-error-overlay]');
  if (errorOverlay) {
    errorOverlay.style.display = 'none';
    errorOverlay.innerHTML = '';
  }

  // Hide player container and disable pointer events
  if (playerContainer) {
    playerContainer.style.display = 'none';
    playerContainer.style.pointerEvents = 'none';
  }

  // Show grid
  const grid = document.querySelector('[data-video-grid]');
  if (grid) {
    grid.style.display = '';
  }

  // Fetch new videos if requested
  if (fetchNewVideos) {
    // This will be handled by grid.js integration
    // Trigger custom event to notify grid to fetch new videos
    const event = new CustomEvent('player:returnToGrid', {
      detail: { fetchNew: true },
    });
    document.dispatchEvent(event);
  }
}

/**
 * Destroy player and clean up resources.
 */
export function destroyPlayer() {
  // Clear timers
  if (bufferingTimer) {
    clearTimeout(bufferingTimer);
    bufferingTimer = null;
  }

  // Remove ESC key listener
  document.removeEventListener('keydown', handleEscKey);

  // Destroy YouTube player
  if (playerInstance) {
    try {
      playerInstance.destroy();
    } catch (error) {
      console.error('Error destroying player:', error);
    }
    playerInstance = null;
  }

  // Clear state
  startTime = null;
  videoId = null;
  playerContainer = null;
}
