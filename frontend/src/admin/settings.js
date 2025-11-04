/**
 * Admin Settings Module (Story 3.2)
 *
 * Handles:
 * - Loading and displaying current settings
 * - Client-side form validation
 * - Dirty state tracking (enable/disable save button)
 * - Saving changes (partial update)
 * - Resetting to defaults
 *
 * TIER 2 Rules:
 * - All API calls wrapped in try/catch with Norwegian error messages
 * - Consistent error handling
 *
 * TIER 3 Rules:
 * - Norwegian user messages
 * - No localStorage/sessionStorage
 */

import { fetchSettings, updateSettings, resetSettings } from '../shared/api.js';
import { createTooltip } from '../shared/help.js';

// State
let originalSettings = {};
let isDirty = false;

/**
 * Initialize settings page.
 * Load current settings and attach event listeners.
 */
export function initSettings() {
  loadSettings();

  // Initialize tooltips (Story 3.X)
  initTooltips();

  // Attach form submit handler
  const form = document.getElementById('settings-form');
  if (form) {
    form.addEventListener('submit', handleSubmit);
  }

  // Attach reset button handler
  const resetBtn = document.getElementById('reset-btn');
  if (resetBtn) {
    resetBtn.addEventListener('click', handleReset);
  }

  // Attach engagement reset button handler (Story 4.4)
  const resetEngagementBtn = document.getElementById('reset-engagement-btn');
  if (resetEngagementBtn) {
    resetEngagementBtn.addEventListener('click', handleResetEngagement);
  }

  // Attach input change handlers for dirty tracking
  const inputs = form.querySelectorAll('input');
  inputs.forEach((input) => {
    input.addEventListener('input', handleInputChange);
  });
}

/**
 * Initialize tooltips for settings (Story 3.X).
 * Adds info icon tooltips next to each setting label.
 */
function initTooltips() {
  // Daily limit tooltip
  const dailyLimitLabel = document.querySelector('label[for="daily-limit"]');
  if (dailyLimitLabel) {
    const dailyLimitTooltip = createTooltip(
      'ℹ️',
      'Grensen tilbakestilles hver natt kl. 00:00 UTC. Videoer som går over grensen avbrytes eller får fullføre basert på lengde.',
      'tooltip-daily-limit'
    );
    dailyLimitLabel.appendChild(dailyLimitTooltip);
  }

  // Grid size tooltip
  const gridSizeLabel = document.querySelector('label[for="grid-size"]');
  if (gridSizeLabel) {
    const gridSizeTooltip = createTooltip(
      'ℹ️',
      'Færre videoer gir større bilder. Flere videoer gir mer variasjon men mindre bilder.',
      'tooltip-grid-size'
    );
    gridSizeLabel.appendChild(gridSizeTooltip);
  }

  // Audio enabled tooltip
  const audioLabel = document.querySelector('label[for="audio-enabled"]');
  if (audioLabel) {
    const audioTooltip = createTooltip(
      'ℹ️',
      "Lydvarsler er enkle 'pling'-lyder, ikke forstyrrende alarmer.",
      'tooltip-audio-enabled'
    );
    audioLabel.appendChild(audioTooltip);
  }
}

/**
 * Load current settings from API and populate form.
 */
async function loadSettings() {
  try {
    showLoading(true);

    const settings = await fetchSettings();

    // Store original values for dirty tracking
    originalSettings = { ...settings };

    // Populate form fields
    document.getElementById('daily-limit').value = settings.daily_limit_minutes;
    document.getElementById('grid-size').value = settings.grid_size;
    document.getElementById('audio-enabled').checked = settings.audio_enabled;

    // Reset dirty state
    isDirty = false;

    showLoading(false);
    updateSaveButton(); // Call after showLoading to avoid override
  } catch (error) {
    showLoading(false);
    showMessage('Kunne ikke laste innstillinger', 'error');
    console.error('Error loading settings:', error);
  }
}

/**
 * Handle input change events for dirty state tracking.
 */
function handleInputChange() {
  const currentSettings = getFormValues();

  // Check if any field differs from original
  isDirty =
    currentSettings.daily_limit_minutes !==
      originalSettings.daily_limit_minutes ||
    currentSettings.grid_size !== originalSettings.grid_size ||
    currentSettings.audio_enabled !== originalSettings.audio_enabled;

  // Validate fields
  const isValid = validateForm();

  updateSaveButton(isValid);
}

/**
 * Get current form values.
 * @returns {Object} Current form values
 */
function getFormValues() {
  return {
    daily_limit_minutes: parseInt(
      document.getElementById('daily-limit').value,
      10
    ),
    grid_size: parseInt(document.getElementById('grid-size').value, 10),
    audio_enabled: document.getElementById('audio-enabled').checked,
  };
}

/**
 * Validate form fields (client-side).
 * Shows inline validation errors.
 * @returns {boolean} True if valid, false otherwise
 */
function validateForm() {
  let isValid = true;

  // Validate daily limit (5-180)
  const dailyLimit = parseInt(document.getElementById('daily-limit').value, 10);
  const dailyLimitError = document.getElementById('daily-limit-error');

  if (isNaN(dailyLimit) || dailyLimit < 5 || dailyLimit > 180) {
    dailyLimitError.textContent = 'Verdien må være mellom 5 og 180';
    dailyLimitError.style.display = 'block';
    isValid = false;
  } else {
    dailyLimitError.textContent = '';
    dailyLimitError.style.display = 'none';
  }

  // Validate grid size (4-15)
  const gridSize = parseInt(document.getElementById('grid-size').value, 10);
  const gridSizeError = document.getElementById('grid-size-error');

  if (isNaN(gridSize) || gridSize < 4 || gridSize > 15) {
    gridSizeError.textContent = 'Verdien må være mellom 4 og 15';
    gridSizeError.style.display = 'block';
    isValid = false;
  } else {
    gridSizeError.textContent = '';
    gridSizeError.style.display = 'none';
  }

  return isValid;
}

/**
 * Update save button state based on dirty flag and validation.
 * @param {boolean} isValid - Whether form is valid
 */
function updateSaveButton(isValid = true) {
  const saveBtn = document.getElementById('save-btn');
  saveBtn.disabled = !isDirty || !isValid;
}

/**
 * Handle form submit event.
 * @param {Event} event - Submit event
 */
async function handleSubmit(event) {
  event.preventDefault();

  if (!validateForm()) {
    return;
  }

  try {
    showLoading(true);
    hideMessage();

    // Get changed values only (partial update)
    const currentSettings = getFormValues();
    const changedSettings = {};

    if (
      currentSettings.daily_limit_minutes !==
      originalSettings.daily_limit_minutes
    ) {
      changedSettings.daily_limit_minutes = currentSettings.daily_limit_minutes;
    }
    if (currentSettings.grid_size !== originalSettings.grid_size) {
      changedSettings.grid_size = currentSettings.grid_size;
    }
    if (currentSettings.audio_enabled !== originalSettings.audio_enabled) {
      changedSettings.audio_enabled = currentSettings.audio_enabled;
    }

    // Call API
    const response = await updateSettings(changedSettings);

    // Update original settings
    originalSettings = { ...response.settings };
    isDirty = false;

    showLoading(false);
    updateSaveButton(); // Call after showLoading to avoid override
    showMessage(response.message, 'success');
  } catch (error) {
    showLoading(false);
    showMessage('Noe gikk galt', 'error');
    console.error('Error saving settings:', error);
  }
}

/**
 * Handle reset button click.
 * Shows confirmation dialog before resetting.
 */
async function handleReset() {
  // Confirmation dialog
  const confirmed = confirm(
    'Tilbakestill alle innstillinger til standardverdier?'
  );
  if (!confirmed) {
    return;
  }

  try {
    showLoading(true);
    hideMessage();

    // Call API
    const response = await resetSettings();

    // Update original settings
    originalSettings = { ...response.settings };

    // Reload form with default values
    document.getElementById('daily-limit').value =
      response.settings.daily_limit_minutes;
    document.getElementById('grid-size').value = response.settings.grid_size;
    document.getElementById('audio-enabled').checked =
      response.settings.audio_enabled;

    isDirty = false;
    updateSaveButton();

    showLoading(false);
    showMessage(response.message, 'success');
  } catch (error) {
    showLoading(false);
    showMessage('Noe gikk galt', 'error');
    console.error('Error resetting settings:', error);
  }
}

/**
 * Show loading state.
 * @param {boolean} loading - Whether loading
 */
function showLoading(loading) {
  const form = document.getElementById('settings-form');
  const inputs = form.querySelectorAll('input, button');

  inputs.forEach((input) => {
    input.disabled = loading;
  });

  if (loading) {
    form.classList.add('loading');
  } else {
    form.classList.remove('loading');
  }
}

/**
 * Show message to user.
 * @param {string} text - Message text
 * @param {string} type - Message type ('success' or 'error')
 */
function showMessage(text, type) {
  const container = document.getElementById('message-container');
  const textEl = document.getElementById('message-text');

  textEl.textContent = text;
  container.className = `message-container message-${type}`;
  container.style.display = 'block';

  // Auto-hide success messages after 3 seconds
  if (type === 'success') {
    setTimeout(() => {
      hideMessage();
    }, 3000);
  }
}

/**
 * Hide message.
 */
function hideMessage() {
  const container = document.getElementById('message-container');
  container.style.display = 'none';
}

/**
 * Handle engagement reset button click (Story 4.4).
 * Shows confirmation dialog before resetting engagement data.
 */
async function handleResetEngagement() {
  // Confirmation dialog
  const confirmed = confirm('Er du sikker? Dette kan ikke angres.');
  if (!confirmed) {
    return;
  }

  try {
    showLoading(true);
    hideMessage();

    // Call API
    const response = await fetch('/admin/engagement/reset', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }

    const data = await response.json();

    showLoading(false);
    showMessage(data.message || 'Engasjementsdata tilbakestilt', 'success');
  } catch (error) {
    showLoading(false);
    showMessage('Kunne ikke tilbakestille engasjementsdata', 'error');
    console.error('Error resetting engagement data:', error);
  }
}

// Initialize on DOM ready (skip in test environment)
// eslint-disable-next-line no-undef
if (typeof process === 'undefined' || process.env.NODE_ENV !== 'test') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSettings);
  } else {
    initSettings();
  }
}
