/**
 * Audio Manager (Story 4.2 - Stub for Story 4.5)
 *
 * Stub implementation for audio playback functionality.
 * Will be fully implemented in Story 4.5 (Audio Features).
 *
 * For now, all audio operations just log to console.
 */

/**
 * Play warning chime sound.
 *
 * STUB: For Story 4.2, this just logs to console.
 * Will be implemented in Story 4.5 with actual audio playback.
 *
 * @param {string} warningType - Type of warning ('10min', '5min', '2min')
 */
export function playWarningChime(warningType) {
  console.log(`[Audio Stub] Would play warning chime for: ${warningType}`);
  // Story 4.5: Will play actual audio file based on warningType
  // - 10min: gentle chime
  // - 5min: medium chime
  // - 2min: urgent chime
}

/**
 * Play grace video notification sound.
 *
 * STUB: For Story 4.2, this just logs to console.
 * Will be implemented in Story 4.5.
 *
 */
export function playGraceNotification() {
  console.log('[Audio Stub] Would play grace notification sound');
  // Story 4.5: Will play special sound for grace video
}

/**
 * Play limit locked notification sound.
 *
 * STUB: For Story 4.2, this just logs to console.
 * Will be implemented in Story 4.5.
 */
export function playLimitLockedSound() {
  console.log('[Audio Stub] Would play limit locked sound');
  // Story 4.5: Will play sound when daily limit is fully consumed
}

/**
 * Check if audio is enabled in settings.
 *
 * STUB: For Story 4.2, always returns true.
 * Will be implemented in Story 4.5 to check actual settings.
 *
 * @returns {boolean} True if audio enabled, false otherwise
 */
export function isAudioEnabled() {
  // Story 4.5: Will check settings from backend API
  return true;
}

/**
 * Set audio enabled state.
 *
 * STUB: For Story 4.2, this just logs to console.
 * Will be implemented in Story 4.5.
 *
 * @param {boolean} enabled - Whether to enable audio
 */
export function setAudioEnabled(enabled) {
  console.log(`[Audio Stub] Would set audio enabled to: ${enabled}`);
  // Story 4.5: Will persist to backend settings
}
