/**
 * Shared API client functions (Story 3.2+)
 *
 * Provides reusable functions for all admin API calls.
 * Handles authentication redirects consistently.
 *
 * TIER 2 Rule 11: Comprehensive error handling for frontend fetch.
 */

/**
 * Fetch current settings from the server.
 * @returns {Promise<Object>} Settings object with daily_limit_minutes, grid_size, audio_enabled
 * @throws {Error} If fetch fails or authentication required
 */
export async function fetchSettings() {
  const response = await fetch('/api/admin/settings', {
    method: 'GET',
    credentials: 'include', // Include session cookie
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Session expired - redirect to login
      window.location.href = '/admin/login';
      return;
    }
    throw new Error('Failed to fetch settings');
  }

  const data = await response.json();
  return data.settings;
}

/**
 * Update settings on the server (partial update).
 * @param {Object} changedSettings - Object with only changed setting keys/values
 * @returns {Promise<Object>} Response with success, settings, and message
 * @throws {Error} If update fails
 */
export async function updateSettings(changedSettings) {
  const response = await fetch('/api/admin/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(changedSettings),
  });

  if (!response.ok) {
    if (response.status === 401) {
      window.location.href = '/admin/login';
      return;
    }
    throw new Error('Failed to update settings');
  }

  return await response.json();
}

/**
 * Reset all settings to defaults.
 * @returns {Promise<Object>} Response with success, default settings, and message
 * @throws {Error} If reset fails
 */
export async function resetSettings() {
  const response = await fetch('/api/admin/settings/reset', {
    method: 'POST',
    credentials: 'include',
  });

  if (!response.ok) {
    if (response.status === 401) {
      window.location.href = '/admin/login';
      return;
    }
    throw new Error('Failed to reset settings');
  }

  return await response.json();
}
