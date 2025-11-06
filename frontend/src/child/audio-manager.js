/**
 * Audio Manager (Story 4.5)
 *
 * Manages audio feedback for the child interface with:
 * - Non-blocking audio preloading (AC 6)
 * - Volume control from backend settings
 * - Graceful fallback if audio fails (AC 9)
 * - Parent enable/disable control (AC 4)
 */

// =============================================================================
// Audio Cache & Preloading (AC 6: Don't delay interactions)
// =============================================================================

/**
 * Module-scoped cache for preloaded audio.
 * Each Audio element is preloaded on module initialization.
 * @type {Object.<string, HTMLAudioElement>}
 */
const audioCache = {
  click: new Audio('/sounds/click.mp3'),
  transition: new Audio('/sounds/transition.mp3'),
  warningChime: new Audio('/sounds/warning-chime.mp3'),
  graceNotification: new Audio('/sounds/grace-notification.mp3'),
};

/**
 * Settings cache to avoid repeated API calls.
 * @type {{audioEnabled: boolean|null, volume: number|null}}
 */
const settingsCache = {
  audioEnabled: null,
  volume: null,
};

/**
 * Preload all sounds on module initialization (non-blocking async).
 * AC 6: Sounds load quickly and don't delay interactions.
 */
Object.values(audioCache).forEach((audio) => {
  try {
    audio.load(); // Non-blocking async preload
    audio.volume = 0.7; // Default volume, will be updated from settings
  } catch (err) {
    // AC 9: Graceful fallback - log warning but don't break app
    console.warn('[Audio] Failed to preload audio:', err);
  }
});

// =============================================================================
// Volume & Settings Helpers
// =============================================================================

/**
 * Get volume setting from backend or cache.
 * AC 5: Volume controls in parent interface.
 *
 * @returns {number} Volume level (0.0-1.0), defaults to 0.7 if fetch fails
 */
async function getVolumeFromSettings() {
  // Return cached value if available
  if (settingsCache.volume !== null) {
    return settingsCache.volume;
  }

  try {
    const response = await fetch('/api/admin/settings');
    if (!response.ok) {
      console.warn(
        '[Audio] Failed to fetch settings, using default volume 0.7'
      );
      return 0.7;
    }

    const data = await response.json();
    const volume = data.settings?.audioVolume ?? 0.7;
    settingsCache.volume = volume;
    return volume;
  } catch (err) {
    // AC 9: Graceful fallback
    console.warn('[Audio] Error fetching volume settings:', err);
    return 0.7; // Default 70% volume
  }
}

/**
 * Check if audio is enabled in settings.
 * AC 4: Parent setting to enable/disable all sounds.
 *
 * @returns {Promise<boolean>} True if audio enabled, false otherwise
 */
export async function isAudioEnabled() {
  // Return cached value if available
  if (settingsCache.audioEnabled !== null) {
    return settingsCache.audioEnabled;
  }

  try {
    const response = await fetch('/api/admin/settings');
    if (!response.ok) {
      console.warn('[Audio] Failed to fetch settings, assuming audio enabled');
      return true; // Default to enabled
    }

    const data = await response.json();
    const enabled = data.settings?.audioEnabled ?? true;
    settingsCache.audioEnabled = enabled;
    return enabled;
  } catch (err) {
    // AC 9: Graceful fallback - assume enabled
    console.warn('[Audio] Error fetching audio enabled setting:', err);
    return true;
  }
}

/**
 * Set audio enabled state and persist to backend.
 * AC 4: Parent setting to enable/disable all sounds.
 *
 * @param {boolean} enabled - Whether to enable audio
 * @returns {Promise<void>}
 */
export async function setAudioEnabled(enabled) {
  try {
    const response = await fetch('/api/admin/settings', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ audioEnabled: enabled }),
    });

    if (!response.ok) {
      console.error('[Audio] Failed to update audio enabled setting');
      return;
    }

    // Update cache
    settingsCache.audioEnabled = enabled;
    console.log(`[Audio] Audio ${enabled ? 'enabled' : 'disabled'}`);
  } catch (err) {
    // AC 9: Graceful fallback - log error but don't throw
    console.error('[Audio] Error updating audio enabled setting:', err);
  }
}

/**
 * Clear settings cache (useful for testing or when settings change).
 * @private
 */
export function clearSettingsCache() {
  settingsCache.audioEnabled = null;
  settingsCache.volume = null;
}

// =============================================================================
// Audio Playback Functions
// =============================================================================

/**
 * Play click sound on thumbnail interaction.
 * AC 1: Playful "pop" sound on thumbnail click.
 *
 * @returns {Promise<void>}
 */
export async function playClickSound() {
  // Check if audio is enabled
  const enabled = await isAudioEnabled();
  if (!enabled) {
    return;
  }

  try {
    // Clone audio node to allow overlapping playback (rapid clicks)
    const sound = audioCache.click.cloneNode();
    sound.volume = await getVolumeFromSettings();

    // AC 9: Use .catch() for Promise rejection (autoplay policies)
    sound.play().catch((err) => {
      console.warn('[Audio] Failed to play click sound:', err);
      // Graceful fallback - application works without audio
    });
  } catch (err) {
    // AC 9: Comprehensive error handling
    console.error('[Audio] Unexpected error playing click sound:', err);
  }
}

/**
 * Play transition sound when returning to grid.
 * AC 2: Gentle transition sound when returning to grid.
 *
 * @returns {Promise<void>}
 */
export async function playTransitionSound() {
  // Check if audio is enabled
  const enabled = await isAudioEnabled();
  if (!enabled) {
    return;
  }

  try {
    // Clone audio node for independent playback
    const sound = audioCache.transition.cloneNode();
    sound.volume = await getVolumeFromSettings();

    // AC 9: Handle autoplay policy rejections
    sound.play().catch((err) => {
      console.warn('[Audio] Failed to play transition sound:', err);
    });
  } catch (err) {
    console.error('[Audio] Unexpected error playing transition sound:', err);
  }
}

/**
 * Play warning chime for time limit warnings.
 * AC 3: Pleasant chime for warnings (not jarring).
 *
 * @param {string} warningType - Type of warning ('10min', '5min', '2min')
 * @returns {Promise<void>}
 */
export async function playWarningChime(warningType) {
  // Check if audio is enabled
  const enabled = await isAudioEnabled();
  if (!enabled) {
    return;
  }

  try {
    // Use same gentle chime for all warning types (AC 3: not jarring)
    const sound = audioCache.warningChime.cloneNode();
    sound.volume = await getVolumeFromSettings();

    // AC 9: Handle autoplay policy rejections
    sound.play().catch((err) => {
      console.warn(
        `[Audio] Failed to play warning chime (${warningType}):`,
        err
      );
    });
  } catch (err) {
    console.error('[Audio] Unexpected error playing warning chime:', err);
  }
}

/**
 * Play grace video notification sound.
 * Called when grace screen is displayed (Story 4.3 integration).
 *
 * @returns {Promise<void>}
 */
export async function playGraceNotification() {
  // Check if audio is enabled
  const enabled = await isAudioEnabled();
  if (!enabled) {
    return;
  }

  try {
    const sound = audioCache.graceNotification.cloneNode();
    sound.volume = await getVolumeFromSettings();

    // AC 9: Handle autoplay policy rejections
    sound.play().catch((err) => {
      console.warn('[Audio] Failed to play grace notification sound:', err);
    });
  } catch (err) {
    console.error('[Audio] Unexpected error playing grace notification:', err);
  }
}

/**
 * Play limit locked notification sound.
 * Called when daily limit is fully consumed (locked state).
 *
 * NOTE: This function exists but was not explicitly required in Story 4.5.
 * Kept for backward compatibility with Story 4.2.
 *
 * @returns {Promise<void>}
 */
export async function playLimitLockedSound() {
  // Check if audio is enabled
  const enabled = await isAudioEnabled();
  if (!enabled) {
    return;
  }

  try {
    // Reuse warning chime for locked state (gentle notification)
    const sound = audioCache.warningChime.cloneNode();
    sound.volume = await getVolumeFromSettings();

    // AC 9: Handle autoplay policy rejections
    sound.play().catch((err) => {
      console.warn('[Audio] Failed to play limit locked sound:', err);
    });
  } catch (err) {
    console.error('[Audio] Unexpected error playing limit locked sound:', err);
  }
}
