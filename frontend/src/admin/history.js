/**
 * Admin History Module (Story 3.1)
 *
 * Handles:
 * - Loading and displaying watch history
 * - Filtering by date range, channel, search
 * - Pagination
 * - Manual video replay in modal
 *
 * TIER 2 Rules:
 * - All API calls wrapped in try/catch with Norwegian error messages
 * - Consistent error handling
 *
 * TIER 3 Rules:
 * - Norwegian user messages
 * - No localStorage/sessionStorage
 */

// State
let currentPage = 1;
const perPage = 50;
let filters = {
  dateFrom: null,
  dateTo: null,
  channel: null,
  search: null,
};

/**
 * Initialize history page.
 * Load initial data and attach event listeners.
 */
export function initHistory() {
  // Load initial history
  loadHistory();

  // Attach filter form handler
  const filterForm = document.getElementById('filter-form');
  if (filterForm) {
    filterForm.addEventListener('submit', handleFilterSubmit);
  }

  // Attach reset button handler
  const resetButton = document.getElementById('reset-filters');
  if (resetButton) {
    resetButton.addEventListener('click', handleResetFilters);
  }

  // Attach pagination handlers
  const prevButton = document.getElementById('prev-page');
  if (prevButton) {
    prevButton.addEventListener('click', () => goToPage(currentPage - 1));
  }

  const nextButton = document.getElementById('next-page');
  if (nextButton) {
    nextButton.addEventListener('click', () => goToPage(currentPage + 1));
  }

  // Load unique channels for filter dropdown
  loadChannelOptions();
}

/**
 * Load watch history from API with current filters and pagination.
 */
async function loadHistory() {
  try {
    // Show loading state
    showLoading();

    // Build query parameters
    const params = new URLSearchParams({
      limit: perPage,
      offset: (currentPage - 1) * perPage,
    });

    if (filters.dateFrom) params.append('date_from', filters.dateFrom);
    if (filters.dateTo) params.append('date_to', filters.dateTo);
    if (filters.channel) params.append('channel', filters.channel);
    if (filters.search) params.append('search', filters.search);

    // Fetch history
    const response = await fetch(`/admin/api/history?${params.toString()}`);

    if (!response.ok) {
      if (response.status === 401) {
        // Session expired - redirect to login
        window.location.href = '/admin/login';
        return;
      }
      throw new Error('Failed to load history');
    }

    const data = await response.json();

    // Render history table
    renderHistory(data.history);

    // Update pagination
    updatePagination(data.total);

    // Show/hide empty state
    if (data.history.length === 0) {
      showEmptyState();
    }
  } catch (error) {
    console.error('Error loading history:', error);
    showError('Kunne ikke laste historikk. Prøv igjen.');
  }
}

/**
 * Render history entries as table rows.
 *
 * @param {Array} history - Array of history entry objects
 */
function renderHistory(history) {
  const contentDiv = document.getElementById('history-content');
  if (!contentDiv) return;

  // Hide loading/empty states
  hideLoading();
  hideEmptyState();

  // Build table HTML
  const tableHTML = `
    <table class="history-table">
      <thead>
        <tr>
          <th>Thumbnail</th>
          <th>Tittel</th>
          <th>Kanal</th>
          <th>Dato og tid</th>
          <th>Varighet</th>
          <th>Type</th>
          <th>Handlinger</th>
        </tr>
      </thead>
      <tbody>
        ${history.map((entry) => renderHistoryRow(entry)).join('')}
      </tbody>
    </table>
  `;

  contentDiv.innerHTML = tableHTML;

  // Attach replay button handlers
  const replayButtons = contentDiv.querySelectorAll('[data-replay-video]');
  replayButtons.forEach((button) => {
    button.addEventListener('click', (e) => {
      const videoId = e.target.dataset.replayVideo;
      handleReplayClick(videoId);
    });
  });
}

/**
 * Render single history table row.
 *
 * @param {Object} entry - History entry object
 * @returns {string} HTML string for table row
 */
function renderHistoryRow(entry) {
  // Format date/time (UTC to local, DD.MM.YYYY HH:MM)
  const formattedDate = formatDateTime(entry.watchedAt);

  // Format duration (seconds to MM:SS)
  const formattedDuration = formatDuration(entry.durationWatchedSeconds);

  // Determine entry type badge
  let typeBadge = '';
  if (entry.manualPlay) {
    typeBadge = '<span class="history-badge">Manuell avspilling</span>';
  } else if (entry.gracePlay) {
    typeBadge = '<span class="history-badge">Bonus-video</span>';
  } else if (entry.completed) {
    typeBadge = '<span class="history-badge">Fullført</span>';
  } else {
    typeBadge = '<span class="history-badge">Delvis</span>';
  }

  return `
    <tr>
      <td>
        <img
          src="${entry.thumbnailUrl}"
          alt="${escapeHtml(entry.videoTitle)}"
          class="history-thumbnail"
          loading="lazy"
        />
      </td>
      <td>${escapeHtml(entry.videoTitle)}</td>
      <td>${escapeHtml(entry.channelName)}</td>
      <td>${formattedDate}</td>
      <td>${formattedDuration}</td>
      <td>${typeBadge}</td>
      <td>
        <button
          class="btn btn-primary btn-sm"
          data-replay-video="${entry.videoId}"
        >
          Spill av igjen
        </button>
      </td>
    </tr>
  `;
}

/**
 * Format UTC timestamp to local Norwegian date/time.
 *
 * @param {string} utcTimestamp - ISO 8601 UTC timestamp
 * @returns {string} Formatted as DD.MM.YYYY HH:MM
 */
export function formatDateTime(utcTimestamp) {
  const date = new Date(utcTimestamp);

  // Format date parts
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();

  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${day}.${month}.${year} ${hours}:${minutes}`;
}

/**
 * Format duration seconds to MM:SS.
 *
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted as MM:SS
 */
export function formatDuration(seconds) {
  const totalSeconds = Math.floor(seconds); // Truncate any decimal part
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${mins}:${String(secs).padStart(2, '0')}`;
}

/**
 * Handle filter form submission.
 *
 * @param {Event} event - Form submit event
 */
function handleFilterSubmit(event) {
  event.preventDefault();

  // Extract filter values
  const formData = new FormData(event.target);
  filters.dateFrom = formData.get('dateFrom') || null;
  filters.dateTo = formData.get('dateTo') || null;
  filters.channel = formData.get('channel') || null;
  filters.search = formData.get('search') || null;

  // Reset to page 1 when filtering
  currentPage = 1;

  // Reload history
  loadHistory();
}

/**
 * Handle reset filters button click.
 */
function handleResetFilters() {
  // Clear filter state
  filters = {
    dateFrom: null,
    dateTo: null,
    channel: null,
    search: null,
  };

  // Reset form inputs
  const form = document.getElementById('filter-form');
  if (form) {
    form.reset();
  }

  // Reset to page 1
  currentPage = 1;

  // Reload history
  loadHistory();
}

/**
 * Handle replay button click.
 * Fetch embed URL and open modal player.
 *
 * @param {string} videoId - YouTube video ID
 */
async function handleReplayClick(videoId) {
  try {
    // Call replay API
    const response = await fetch('/admin/history/replay', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ videoId }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to replay video');
    }

    const data = await response.json();

    // Open modal with player
    openReplayModal(data.embedUrl, videoId);
  } catch (error) {
    console.error('Error replaying video:', error);
    showError(error.message || 'Kunne ikke spille av video');
  }
}

/**
 * Open modal with YouTube player.
 *
 * @param {string} embedUrl - YouTube embed URL with parameters
 * @param {string} videoId - YouTube video ID
 */
function openReplayModal(embedUrl, videoId) {
  const modal = document.getElementById('replay-modal');
  const playerDiv = document.getElementById('replay-player');

  if (!modal || !playerDiv) return;

  // Create iframe
  const iframe = document.createElement('iframe');
  iframe.src = embedUrl;
  iframe.allow =
    'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
  iframe.allowFullscreen = true;

  // Clear and insert iframe
  playerDiv.innerHTML = '';
  playerDiv.appendChild(iframe);

  // Show modal
  modal.style.display = 'block';

  // Attach close handlers
  const closeButtons = modal.querySelectorAll('[data-modal-close]');
  closeButtons.forEach((button) => {
    button.addEventListener('click', () => closeReplayModal(videoId, iframe));
  });

  // ESC key handler
  const escHandler = (event) => {
    if (event.key === 'Escape' || event.keyCode === 27) {
      closeReplayModal(videoId, iframe);
      document.removeEventListener('keydown', escHandler);
    }
  };
  document.addEventListener('keydown', escHandler);
}

/**
 * Close replay modal.
 * Does NOT log watch history (admin preview).
 *
 * @param {string} videoId - YouTube video ID
 * @param {HTMLIFrameElement} iframe - Player iframe element
 */
function closeReplayModal(videoId, iframe) {
  const modal = document.getElementById('replay-modal');
  if (!modal) return;

  // Remove iframe
  iframe.remove();

  // Hide modal
  modal.style.display = 'none';

  console.log(`Closed replay modal for ${videoId} without logging`);
}

/**
 * Update pagination controls.
 *
 * @param {number} total - Total number of entries
 */
function updatePagination(total) {
  const paginationDiv = document.getElementById('pagination');
  const prevButton = document.getElementById('prev-page');
  const nextButton = document.getElementById('next-page');
  const pageInfo = document.getElementById('page-info');

  if (!paginationDiv || !prevButton || !nextButton || !pageInfo) return;

  // Calculate total pages
  const totalPages = Math.ceil(total / perPage);

  // Show pagination only if multiple pages
  if (totalPages > 1) {
    paginationDiv.style.display = 'flex';
  } else {
    paginationDiv.style.display = 'none';
    return;
  }

  // Update page info text
  pageInfo.textContent = `Side ${currentPage} av ${totalPages}`;

  // Enable/disable prev button
  prevButton.disabled = currentPage === 1;

  // Enable/disable next button
  nextButton.disabled = currentPage === totalPages;
}

/**
 * Navigate to specific page.
 *
 * @param {number} page - Page number (1-indexed)
 */
function goToPage(page) {
  currentPage = page;
  loadHistory();
}

/**
 * Load unique channel names for filter dropdown.
 */
async function loadChannelOptions() {
  try {
    // Fetch all history to extract unique channels
    // (Simplified - in production, might want a dedicated endpoint)
    const response = await fetch('/admin/api/history?limit=1000');
    if (!response.ok) return;

    const data = await response.json();

    // Extract unique channel names
    const channels = [...new Set(data.history.map((h) => h.channelName))];
    channels.sort();

    // Populate dropdown
    const dropdown = document.getElementById('channel-filter');
    if (!dropdown) return;

    channels.forEach((channel) => {
      const option = document.createElement('option');
      option.value = channel;
      option.textContent = channel;
      dropdown.appendChild(option);
    });
  } catch (error) {
    console.error('Error loading channel options:', error);
  }
}

/**
 * Show loading spinner.
 */
function showLoading() {
  const contentDiv = document.getElementById('history-content');
  if (!contentDiv) return;

  contentDiv.innerHTML =
    '<div class="loading-spinner" data-loading>Laster historikk...</div>';
}

/**
 * Hide loading spinner.
 */
function hideLoading() {
  const loading = document.querySelector('[data-loading]');
  if (loading) loading.remove();
}

/**
 * Show empty state message.
 */
function showEmptyState() {
  const emptyDiv = document.getElementById('empty-state');
  if (emptyDiv) {
    emptyDiv.style.display = 'block';
  }

  const contentDiv = document.getElementById('history-content');
  if (contentDiv) {
    contentDiv.style.display = 'none';
  }
}

/**
 * Hide empty state message.
 */
function hideEmptyState() {
  const emptyDiv = document.getElementById('empty-state');
  if (emptyDiv) {
    emptyDiv.style.display = 'none';
  }

  const contentDiv = document.getElementById('history-content');
  if (contentDiv) {
    contentDiv.style.display = 'block';
  }
}

/**
 * Show error message to user.
 *
 * @param {string} message - Norwegian error message
 */
function showError(message) {
  // Simple alert for MVP
  // Could be replaced with toast notification system
  alert(message);
}

/**
 * Escape HTML to prevent XSS.
 *
 * @param {string} text - Text to escape
 * @returns {string} HTML-safe text
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
