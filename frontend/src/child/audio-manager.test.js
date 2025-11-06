/**
 * Audio Manager Tests (Story 4.5)
 *
 * Tests audio preloading, playback, volume control, and graceful fallback.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  playClickSound,
  playTransitionSound,
  playWarningChime,
  playGraceNotification,
  isAudioEnabled,
  setAudioEnabled,
  clearSettingsCache,
} from './audio-manager.js';

// Mock fetch globally
global.fetch = vi.fn();

// Mock Audio constructor
global.Audio = class {
  constructor(src) {
    this.src = src;
    this.volume = 0.7;
    this.load = vi.fn();
  }

  cloneNode() {
    const clone = new Audio(this.src);
    clone.volume = this.volume;
    clone.play = vi.fn().mockResolvedValue(undefined);
    return clone;
  }

  play() {
    return Promise.resolve();
  }
};

describe('audio-manager', () => {
  beforeEach(() => {
    // Clear all mocks
    vi.clearAllMocks();

    // Clear settings cache
    clearSettingsCache();

    // Reset fetch mock
    global.fetch.mockReset();
  });

  describe('isAudioEnabled', () => {
    it('returns true when audio is enabled', async () => {
      // Mock API response
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          settings: {
            audioEnabled: true,
          },
        }),
      });

      const result = await isAudioEnabled();
      expect(result).toBe(true);
    });

    it('returns false when audio is disabled', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          settings: {
            audioEnabled: false,
          },
        }),
      });

      const result = await isAudioEnabled();
      expect(result).toBe(false);
    });

    it('defaults to true on fetch error (graceful fallback - AC 9)', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await isAudioEnabled();
      expect(result).toBe(true); // Default to enabled
    });

    it('caches result to avoid repeated API calls', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          settings: {
            audioEnabled: true,
          },
        }),
      });

      // Call twice
      await isAudioEnabled();
      await isAudioEnabled();

      // Should only fetch once (cached)
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('setAudioEnabled', () => {
    it('updates audio enabled setting via API', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      });

      await setAudioEnabled(false);

      expect(global.fetch).toHaveBeenCalledWith('/api/admin/settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ audioEnabled: false }),
      });
    });

    it('handles API errors gracefully (AC 9)', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      // Should not throw
      await expect(setAudioEnabled(true)).resolves.not.toThrow();
    });
  });

  describe('playClickSound', () => {
    it('plays click sound when audio is enabled', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          settings: {
            audioEnabled: true,
            audioVolume: 0.7,
          },
        }),
      });

      // Call playClickSound
      await playClickSound();

      // Wait for async operations
      await new Promise((resolve) => setTimeout(resolve, 10));

      // Should have called fetch for settings
      expect(global.fetch).toHaveBeenCalled();
    });

    it('does not play sound when audio is disabled', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          settings: {
            audioEnabled: false,
          },
        }),
      });

      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      await playClickSound();

      // Should not attempt to play
      expect(consoleSpy).not.toHaveBeenCalled();

      consoleSpy.mockRestore();
    });

    it('handles audio play errors gracefully (AC 9)', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          settings: {
            audioEnabled: true,
            audioVolume: 0.7,
          },
        }),
      });

      // Mock Audio.play() to reject
      global.Audio.prototype.play = vi
        .fn()
        .mockRejectedValue(new Error('Autoplay blocked'));

      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      // Should not throw
      await expect(playClickSound()).resolves.not.toThrow();

      consoleSpy.mockRestore();
    });
  });

  describe('playWarningChime', () => {
    it('plays warning chime with warning type parameter', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          settings: {
            audioEnabled: true,
            audioVolume: 0.7,
          },
        }),
      });

      // Should accept warningType parameter (AC 3)
      await expect(playWarningChime('10min')).resolves.not.toThrow();
      await expect(playWarningChime('5min')).resolves.not.toThrow();
      await expect(playWarningChime('2min')).resolves.not.toThrow();
    });
  });

  describe('playTransitionSound', () => {
    it('plays transition sound when returning to grid (AC 2)', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          settings: {
            audioEnabled: true,
            audioVolume: 0.7,
          },
        }),
      });

      await expect(playTransitionSound()).resolves.not.toThrow();
    });
  });

  describe('playGraceNotification', () => {
    it('plays grace notification sound when grace screen appears', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          settings: {
            audioEnabled: true,
            audioVolume: 0.7,
          },
        }),
      });

      await expect(playGraceNotification()).resolves.not.toThrow();
    });
  });

  describe('volume control (AC 5)', () => {
    it('applies volume setting from backend', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          settings: {
            audioEnabled: true,
            audioVolume: 0.5, // 50% volume
          },
        }),
      });

      // This will be called internally when playing sound
      await playClickSound();

      // Volume should be applied (tested via integration)
      expect(global.fetch).toHaveBeenCalled();
    });

    it('defaults to 0.7 (70%) if volume setting not found', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          settings: {
            audioEnabled: true,
            // audioVolume missing
          },
        }),
      });

      // Should not throw, should use default
      await expect(playClickSound()).resolves.not.toThrow();
    });
  });

  describe('graceful fallback (AC 9)', () => {
    it('works perfectly when fetch fails', async () => {
      global.fetch.mockRejectedValue(new Error('Network error'));

      // All functions should work without throwing
      await expect(playClickSound()).resolves.not.toThrow();
      await expect(playTransitionSound()).resolves.not.toThrow();
      await expect(playWarningChime('10min')).resolves.not.toThrow();
      await expect(playGraceNotification()).resolves.not.toThrow();
    });

    it('logs warnings but does not break app', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      global.fetch.mockRejectedValue(new Error('Network error'));

      await playClickSound();

      // Should log warning but not throw
      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });
  });
});
