/**
 * Channel management module for admin interface.
 *
 * Handles:
 * - Loading and rendering channel list
 * - Adding new channels/playlists
 * - Refreshing existing sources
 * - Removing sources with confirmation
 *
 * TIER 2 Rule 9: Always handle frontend fetch errors
 * TIER 3 Rule 14: Norwegian error messages for users
 * Security: Use textContent (not innerHTML) to prevent XSS
 */

// =============================================================================
// STATE MANAGEMENT
// =============================================================================

let currentChannels = [];
let confirmCallback = null;

// =============================================================================
// DOM ELEMENT REFERENCES
// =============================================================================

const elements = {
  // Form elements
  addForm: null,
  channelInput: null,
  addButton: null,

  // Table elements
  channelsTable: null,
  channelsTbody: null,
  loadingRow: null,
  emptyState: null,

  // Message elements
  messageContainer: null,
  messageText: null,

  // Dialog elements
  confirmDialog: null,
  confirmMessage: null,
  confirmDetails: null,
  confirmCancelBtn: null,
  confirmDeleteBtn: null,

  // Loading overlay
  loadingOverlay: null,
};

// =============================================================================
// INITIALIZATION
// =============================================================================

/**
 * Initialize channel management module.
 * Called from admin.js when DOM is ready.
 */
export function initChannelManagement() {
  // Get DOM element references using data-* attributes
  elements.addForm = document.querySelector('[data-add-channel-form]');
  elements.channelInput = document.querySelector('[data-channel-input]');
  elements.addButton = document.querySelector('[data-add-button]');
  elements.channelsTable = document.querySelector('[data-channels-table]');
  elements.channelsTbody = document.querySelector('[data-channels-tbody]');
  elements.loadingRow = document.querySelector('[data-loading-row]');
  elements.emptyState = document.querySelector('[data-empty-state]');
  elements.messageContainer = document.querySelector(
    '[data-message-container]'
  );
  elements.messageText = document.querySelector('[data-message-text]');
  elements.confirmDialog = document.querySelector('[data-confirm-dialog]');
  elements.confirmMessage = document.querySelector('[data-confirm-message]');
  elements.confirmDetails = document.querySelector('[data-confirm-details]');
  elements.confirmCancelBtn = document.querySelector('[data-confirm-cancel]');
  elements.confirmDeleteBtn = document.querySelector('[data-confirm-delete]');
  elements.loadingOverlay = document.querySelector('[data-loading-overlay]');

  // Attach event listeners
  if (elements.addForm) {
    elements.addForm.addEventListener('submit', handleAddChannel);
  }

  if (elements.confirmCancelBtn) {
    elements.confirmCancelBtn.addEventListener('click', hideConfirmDialog);
  }

  if (elements.confirmDeleteBtn) {
    elements.confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
  }

  // Load initial channel list
  loadChannels();
}

// =============================================================================
// CHANNEL LOADING
// =============================================================================

/**
 * Load channels from API and render table.
 *
 * TIER 2 Rule 9: Handles fetch errors with try/catch.
 */
async function loadChannels() {
  try {
    // Show loading state
    if (elements.loadingRow) {
      elements.loadingRow.style.display = '';
    }
    if (elements.emptyState) {
      elements.emptyState.style.display = 'none';
    }

    // TIER 2 Rule 9: Handle fetch errors
    const response = await fetch('/admin/sources');

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    currentChannels = data.sources || [];

    // Render channel table
    renderChannelTable(currentChannels);
  } catch (error) {
    console.error('Failed to load channels:', error);

    // TIER 3 Rule 14: Norwegian error message with retry option
    showMessage('Kunne ikke laste kanaler.', 'error');

    // Hide loading row
    if (elements.loadingRow) {
      elements.loadingRow.style.display = 'none';
    }

    // Show empty state with retry button
    showRetryState();
  }
}

/**
 * Show retry button when initial load fails.
 *
 * Provides better UX than asking user to refresh entire page.
 */
function showRetryState() {
  if (!elements.channelsTbody) return;

  // Clear existing rows
  const existingRows = elements.channelsTbody.querySelectorAll(
    'tr:not([data-loading-row]):not([data-empty-state])'
  );
  existingRows.forEach((row) => row.remove());

  // Hide empty state
  if (elements.emptyState) {
    elements.emptyState.style.display = 'none';
  }

  // Create retry row
  const retryRow = document.createElement('tr');
  retryRow.className = 'retry-row';

  const retryCell = document.createElement('td');
  retryCell.colSpan = 6;
  retryCell.style.textAlign = 'center';
  retryCell.style.padding = '2rem';

  const retryButton = document.createElement('button');
  retryButton.className = 'btn btn-primary';
  retryButton.textContent = 'Prøv igjen';
  retryButton.addEventListener('click', () => {
    retryRow.remove();
    loadChannels();
  });

  retryCell.appendChild(retryButton);
  retryRow.appendChild(retryCell);
  elements.channelsTbody.appendChild(retryRow);
}

/**
 * Render channel table with current channels.
 *
 * Security: Uses textContent (not innerHTML) to prevent XSS.
 *
 * @param {Array} sources - Array of source objects from API
 */
function renderChannelTable(sources) {
  // Hide loading row
  if (elements.loadingRow) {
    elements.loadingRow.style.display = 'none';
  }

  // Clear existing rows (except loading row and empty state)
  if (elements.channelsTbody) {
    const existingRows = elements.channelsTbody.querySelectorAll(
      'tr:not([data-loading-row]):not([data-empty-state])'
    );
    existingRows.forEach((row) => row.remove());
  }

  // Show empty state if no sources
  if (!sources || sources.length === 0) {
    if (elements.emptyState) {
      elements.emptyState.style.display = 'block';
    }
    return;
  }

  // Hide empty state
  if (elements.emptyState) {
    elements.emptyState.style.display = 'none';
  }

  // Render each source as table row
  sources.forEach((source) => {
    const row = createChannelRow(source);
    if (elements.channelsTbody) {
      elements.channelsTbody.appendChild(row);
    }
  });
}

/**
 * Create table row for a single channel.
 *
 * Security: Uses textContent and createElement to prevent XSS.
 *
 * @param {Object} source - Source object from API
 * @returns {HTMLElement} Table row element
 */
function createChannelRow(source) {
  const row = document.createElement('tr');
  row.className = 'channel-row';
  row.dataset.sourceId = source.id;

  // Thumbnail cell (placeholder for now - YouTube API provides thumbnails)
  const thumbnailCell = document.createElement('td');
  thumbnailCell.className = 'table-cell thumbnail-cell';
  const thumbnailPlaceholder = document.createElement('div');
  thumbnailPlaceholder.className = 'channel-thumbnail';
  thumbnailPlaceholder.textContent = source.name.charAt(0).toUpperCase();
  thumbnailCell.appendChild(thumbnailPlaceholder);
  row.appendChild(thumbnailCell);

  // Name cell
  const nameCell = document.createElement('td');
  nameCell.className = 'table-cell';
  nameCell.textContent = source.name; // Security: textContent prevents XSS
  row.appendChild(nameCell);

  // Type cell
  const typeCell = document.createElement('td');
  typeCell.className = 'table-cell';
  typeCell.textContent =
    source.sourceType === 'channel' ? 'Kanal' : 'Spilleliste';
  row.appendChild(typeCell);

  // Video count cell
  const countCell = document.createElement('td');
  countCell.className = 'table-cell';
  countCell.textContent = source.videoCount.toString();
  row.appendChild(countCell);

  // Last refresh cell
  const refreshCell = document.createElement('td');
  refreshCell.className = 'table-cell';
  refreshCell.textContent = formatDate(source.lastRefresh);
  row.appendChild(refreshCell);

  // Actions cell
  const actionsCell = document.createElement('td');
  actionsCell.className = 'table-cell actions-cell';

  // Refresh button
  const refreshBtn = document.createElement('button');
  refreshBtn.className = 'btn btn-small btn-secondary';
  refreshBtn.textContent = 'Oppdater';
  refreshBtn.dataset.refreshBtn = '';
  refreshBtn.addEventListener('click', () => handleRefresh(source.id));
  actionsCell.appendChild(refreshBtn);

  // Remove button
  const removeBtn = document.createElement('button');
  removeBtn.className = 'btn btn-small btn-danger';
  removeBtn.textContent = 'Fjern';
  removeBtn.dataset.removeBtn = '';
  removeBtn.addEventListener('click', () =>
    handleRemove(source.id, source.name, source.videoCount)
  );
  actionsCell.appendChild(removeBtn);

  row.appendChild(actionsCell);

  return row;
}

// =============================================================================
// ADD CHANNEL
// =============================================================================

/**
 * Handle add channel form submission.
 *
 * TIER 2 Rule 9: Handles fetch errors with try/catch.
 * TIER 3 Rule 14: Shows Norwegian messages to user.
 *
 * @param {Event} event - Form submit event
 */
async function handleAddChannel(event) {
  event.preventDefault();

  // Get input value and validate
  const input = elements.channelInput.value.trim();
  if (!input) {
    showMessage('Vennligst oppgi en YouTube-lenke eller ID', 'error');
    return;
  }

  try {
    // Show loading overlay
    showLoadingOverlay();

    // Disable form during request
    elements.addButton.disabled = true;
    elements.channelInput.disabled = true;

    // TIER 2 Rule 9: Handle fetch errors
    const response = await fetch('/admin/sources', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ input }),
    });

    const data = await response.json();

    if (!response.ok) {
      // Handle error response
      // TIER 3 Rule 14: Display Norwegian error message from API
      const errorMessage = data.message || 'Noe gikk galt';
      showMessage(errorMessage, 'error');
      return;
    }

    // Success!
    const successMessage = data.message || 'Kanal lagt til';
    showMessage(successMessage, 'success');

    // Check if partial fetch (network error)
    if (data.partial) {
      // Add pulse animation to refresh button for this source
      // This will be done after table is re-rendered
      setTimeout(() => {
        const row = document.querySelector(
          `[data-source-id="${data.source.id}"]`
        );
        if (row) {
          const refreshBtn = row.querySelector('.btn-secondary');
          if (refreshBtn) {
            refreshBtn.classList.add('pulse-button');
          }
        }
      }, 100);
    }

    // Clear input field
    elements.channelInput.value = '';

    // Reload channel list
    await loadChannels();
  } catch (error) {
    console.error('Error adding channel:', error);
    // TIER 3 Rule 14: Norwegian error message
    showMessage('Noe gikk galt ved tilkobling til serveren', 'error');
  } finally {
    // Re-enable form
    elements.addButton.disabled = false;
    elements.channelInput.disabled = false;

    // Hide loading overlay
    hideLoadingOverlay();
  }
}

// =============================================================================
// REFRESH CHANNEL
// =============================================================================

/**
 * Handle refresh button click.
 *
 * TIER 2 Rule 9: Handles fetch errors with try/catch.
 * TIER 3 Rule 14: Shows Norwegian messages to user.
 *
 * @param {number} sourceId - Source ID to refresh
 */
async function handleRefresh(sourceId) {
  try {
    // Show loading overlay
    showLoadingOverlay();

    // TIER 2 Rule 9: Handle fetch errors
    const response = await fetch(`/admin/sources/${sourceId}/refresh`, {
      method: 'POST',
    });

    const data = await response.json();

    if (!response.ok) {
      // Handle error response
      // TIER 3 Rule 14: Display Norwegian error message from API
      const errorMessage = data.message || 'Noe gikk galt';
      showMessage(errorMessage, 'error');
      return;
    }

    // Success!
    const successMessage = data.message || 'Oppdatert';
    showMessage(successMessage, 'success');

    // Remove pulse animation if present
    const row = document.querySelector(`[data-source-id="${sourceId}"]`);
    if (row) {
      const refreshBtn = row.querySelector('.btn-secondary');
      if (refreshBtn) {
        refreshBtn.classList.remove('pulse-button');
      }
    }

    // Reload channel list
    await loadChannels();
  } catch (error) {
    console.error('Error refreshing channel:', error);
    // TIER 3 Rule 14: Norwegian error message
    showMessage('Noe gikk galt ved tilkobling til serveren', 'error');
  } finally {
    // Hide loading overlay
    hideLoadingOverlay();
  }
}

// =============================================================================
// REMOVE CHANNEL
// =============================================================================

/**
 * Handle remove button click - show confirmation dialog.
 *
 * @param {number} sourceId - Source ID to remove
 * @param {string} sourceName - Source name for confirmation message
 * @param {number} videoCount - Video count for confirmation message
 */
function handleRemove(sourceId, sourceName, videoCount) {
  // Set confirmation message
  // Security: Uses textContent to prevent XSS
  if (elements.confirmMessage) {
    elements.confirmMessage.textContent =
      'Er du sikker på at du vil fjerne denne kanalen?';
  }

  if (elements.confirmDetails) {
    elements.confirmDetails.textContent = `${sourceName} (${videoCount} videoer vil bli slettet)`;
  }

  // Store callback for confirm button
  confirmCallback = () => performRemove(sourceId);

  // Show confirmation dialog
  showConfirmDialog();
}

/**
 * Perform actual remove operation after confirmation.
 *
 * TIER 2 Rule 9: Handles fetch errors with try/catch.
 * TIER 3 Rule 14: Shows Norwegian messages to user.
 *
 * @param {number} sourceId - Source ID to remove
 */
async function performRemove(sourceId) {
  // Hide confirmation dialog
  hideConfirmDialog();

  try {
    // Show loading overlay
    showLoadingOverlay();

    // TIER 2 Rule 9: Handle fetch errors
    const response = await fetch(`/admin/sources/${sourceId}`, {
      method: 'DELETE',
    });

    const data = await response.json();

    if (!response.ok) {
      // Handle error response
      // TIER 3 Rule 14: Display Norwegian error message from API
      const errorMessage = data.message || 'Noe gikk galt';
      showMessage(errorMessage, 'error');
      return;
    }

    // Success!
    const successMessage = data.message || 'Kilde fjernet';
    showMessage(successMessage, 'success');

    // Reload channel list
    await loadChannels();
  } catch (error) {
    console.error('Error removing channel:', error);
    // TIER 3 Rule 14: Norwegian error message
    showMessage('Noe gikk galt ved tilkobling til serveren', 'error');
  } finally {
    // Hide loading overlay
    hideLoadingOverlay();
  }
}

/**
 * Handle confirm delete button click.
 */
function handleConfirmDelete() {
  if (confirmCallback) {
    confirmCallback();
    confirmCallback = null;
  }
}

// =============================================================================
// UI HELPERS
// =============================================================================

/**
 * Show message to user (success or error).
 *
 * Security: Uses textContent to prevent XSS.
 *
 * @param {string} message - Message text
 * @param {string} type - Message type ('success' or 'error')
 */
function showMessage(message, type) {
  if (!elements.messageContainer || !elements.messageText) return;

  // Set message text (Security: textContent prevents XSS)
  elements.messageText.textContent = message;

  // Set message type class
  elements.messageContainer.className = `message-container message-${type}`;

  // Show message
  elements.messageContainer.style.display = 'block';

  // Auto-hide after 5 seconds
  setTimeout(() => {
    if (elements.messageContainer) {
      elements.messageContainer.style.display = 'none';
    }
  }, 5000);
}

/**
 * Show confirmation dialog.
 */
function showConfirmDialog() {
  if (elements.confirmDialog) {
    elements.confirmDialog.style.display = 'flex';
  }
}

/**
 * Hide confirmation dialog.
 */
function hideConfirmDialog() {
  if (elements.confirmDialog) {
    elements.confirmDialog.style.display = 'none';
  }
  confirmCallback = null;
}

/**
 * Show loading overlay.
 */
function showLoadingOverlay() {
  if (elements.loadingOverlay) {
    elements.loadingOverlay.style.display = 'flex';
  }
}

/**
 * Hide loading overlay.
 */
function hideLoadingOverlay() {
  if (elements.loadingOverlay) {
    elements.loadingOverlay.style.display = 'none';
  }
}

/**
 * Format ISO 8601 date string to Norwegian format.
 *
 * @param {string} isoString - ISO 8601 date string
 * @returns {string} Formatted date string
 */
function formatDate(isoString) {
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString('no-NO', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}
