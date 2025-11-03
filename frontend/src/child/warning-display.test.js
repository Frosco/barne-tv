/**
 * Tests for Warning Display Component (Story 4.2)
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { showWarning, initWarningDisplay, cleanup } from './warning-display.js';
import * as audioManager from './audio-manager.js';

describe('Warning Display Component', () => {
  beforeEach(() => {
    // Clear DOM
    document.body.innerHTML = '';

    // Mock fetch with default success response
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });

    // Mock audio manager
    vi.spyOn(audioManager, 'playWarningChime').mockImplementation(() => {});
    vi.spyOn(audioManager, 'isAudioEnabled').mockReturnValue(true);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe('showWarning', () => {
    it('should create warning overlay with correct content for 10min warning', () => {
      // Story 4.3: Mascot PNG images instead of emoji
      showWarning('10min');

      const overlay = document.querySelector('.warning-overlay');
      expect(overlay).toBeTruthy();
      expect(overlay.classList.contains('warning--10min')).toBe(true);

      const title = overlay.querySelector('.warning-overlay__title');
      expect(title.textContent).toBe('10 minutter igjen!');

      const message = overlay.querySelector('.warning-overlay__message');
      expect(message.textContent).toContain('Du har god tid igjen!');

      // Mascot is now an image, not emoji
      const mascotContainer = overlay.querySelector('.warning-overlay__mascot');
      const mascotImg = mascotContainer.querySelector('img');
      expect(mascotImg).toBeTruthy();
      expect(mascotImg.src).toContain('/images/mascot/mascot-happy.png');
    });

    it('should create warning overlay with correct content for 5min warning', () => {
      showWarning('5min');

      const overlay = document.querySelector('.warning-overlay');
      expect(overlay).toBeTruthy();
      expect(overlay.classList.contains('warning--5min')).toBe(true);

      const title = overlay.querySelector('.warning-overlay__title');
      expect(title.textContent).toBe('5 minutter igjen!');

      const message = overlay.querySelector('.warning-overlay__message');
      expect(message.textContent).toContain('Snart er tiden ute');
    });

    it('should create warning overlay with correct content for 2min warning', () => {
      showWarning('2min');

      const overlay = document.querySelector('.warning-overlay');
      expect(overlay).toBeTruthy();
      expect(overlay.classList.contains('warning--2min')).toBe(true);

      const title = overlay.querySelector('.warning-overlay__title');
      expect(title.textContent).toBe('2 minutter igjen!');

      const message = overlay.querySelector('.warning-overlay__message');
      expect(message.textContent).toContain('Bare 2 minutter igjen!');
    });

    it('should add active class after DOM insertion', async () => {
      showWarning('10min');

      const overlay = document.querySelector('.warning-overlay');

      // Wait for next animation frame
      await new Promise((resolve) => requestAnimationFrame(resolve));

      expect(overlay.classList.contains('warning-overlay--active')).toBe(true);
    });

    it('should play audio chime when audio is enabled', () => {
      audioManager.isAudioEnabled.mockReturnValue(true);

      showWarning('10min');

      expect(audioManager.playWarningChime).toHaveBeenCalledWith('10min');
    });

    it('should not play audio chime when audio is disabled', () => {
      audioManager.isAudioEnabled.mockReturnValue(false);

      showWarning('10min');

      expect(audioManager.playWarningChime).not.toHaveBeenCalled();
    });

    it('should log warning to backend', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true }),
      });

      showWarning('10min');

      // Wait for async logging
      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(global.fetch).toHaveBeenCalledWith('/api/warnings/log', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: expect.stringContaining('"warningType":"10min"'),
      });

      const callBody = JSON.parse(global.fetch.mock.calls[0][1].body);
      expect(callBody.warningType).toBe('10min');
      expect(callBody.shownAt).toMatch(/^\d{4}-\d{2}-\d{2}T/); // ISO 8601 format
    });

    it('should handle backend logging errors gracefully', async () => {
      const consoleError = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {});
      global.fetch.mockRejectedValue(new Error('Network error'));

      showWarning('10min');

      // Wait for async logging
      await new Promise((resolve) => setTimeout(resolve, 10));

      // Should not throw, just log error
      expect(consoleError).toHaveBeenCalledWith(
        'Failed to log warning to backend:',
        expect.any(Error)
      );

      // Overlay should still be visible
      const overlay = document.querySelector('.warning-overlay');
      expect(overlay).toBeTruthy();

      consoleError.mockRestore();
    });

    it('should auto-dismiss after 3 seconds', async () => {
      vi.useFakeTimers();

      showWarning('10min');

      const overlay = document.querySelector('.warning-overlay');
      expect(overlay).toBeTruthy();

      // Fast-forward 3 seconds
      vi.advanceTimersByTime(3000);

      // Should have dismissing class
      expect(overlay.classList.contains('warning-overlay--dismissing')).toBe(
        true
      );

      // Fast-forward animation duration
      vi.advanceTimersByTime(300);

      // Should be removed from DOM
      expect(document.querySelector('.warning-overlay')).toBeFalsy();

      vi.useRealTimers();
    });

    it('should dismiss warning when clicked', async () => {
      vi.useFakeTimers();

      showWarning('10min');

      const overlay = document.querySelector('.warning-overlay');
      expect(overlay).toBeTruthy();

      // Click overlay
      overlay.click();

      // Should have dismissing class
      expect(overlay.classList.contains('warning-overlay--dismissing')).toBe(
        true
      );

      // Fast-forward animation duration
      vi.advanceTimersByTime(300);

      // Should be removed from DOM
      expect(document.querySelector('.warning-overlay')).toBeFalsy();

      vi.useRealTimers();
    });

    it('should have correct ARIA attributes for accessibility', () => {
      showWarning('10min');

      const overlay = document.querySelector('.warning-overlay');
      expect(overlay.getAttribute('role')).toBe('alert');
      expect(overlay.getAttribute('aria-live')).toBe('assertive');

      const mascot = overlay.querySelector('.warning-overlay__mascot');
      expect(mascot.getAttribute('aria-hidden')).toBe('true');
    });

    it('should log error for invalid warning type', () => {
      const consoleError = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {});

      showWarning('invalid');

      expect(consoleError).toHaveBeenCalledWith(
        'Invalid warning type: invalid'
      );
      expect(document.querySelector('.warning-overlay')).toBeFalsy();

      consoleError.mockRestore();
    });

    it('should clear previous auto-dismiss timeout when manually dismissed', async () => {
      vi.useFakeTimers();

      showWarning('10min');

      const overlay = document.querySelector('.warning-overlay');

      // Manually dismiss before auto-dismiss
      vi.advanceTimersByTime(1000); // Only 1 second
      overlay.click();

      // Should dismiss immediately
      expect(overlay.classList.contains('warning-overlay--dismissing')).toBe(
        true
      );

      // Fast-forward past original auto-dismiss time
      vi.advanceTimersByTime(5000);

      // Should still only have been dismissed once
      expect(document.querySelector('.warning-overlay')).toBeFalsy();

      vi.useRealTimers();
    });
  });

  describe('initWarningDisplay', () => {
    it('should listen for warningTriggered events', () => {
      initWarningDisplay();

      // Simulate warningTriggered event from limit-tracker
      const event = new CustomEvent('warningTriggered', {
        detail: { warningType: '5min' },
      });
      window.dispatchEvent(event);

      // Should create warning overlay
      const overlay = document.querySelector('.warning-overlay');
      expect(overlay).toBeTruthy();
      expect(overlay.classList.contains('warning--5min')).toBe(true);
    });

    it('should log initialization to console', () => {
      const consoleLog = vi.spyOn(console, 'log').mockImplementation(() => {});

      initWarningDisplay();

      expect(consoleLog).toHaveBeenCalledWith(
        'Warning display system initialized'
      );

      consoleLog.mockRestore();
    });
  });

  describe('cleanup', () => {
    it('should remove all warning overlays', async () => {
      showWarning('10min');
      showWarning('5min');

      expect(document.querySelectorAll('.warning-overlay').length).toBe(2);

      cleanup();

      expect(document.querySelectorAll('.warning-overlay').length).toBe(0);
    });

    it('should clear active dismiss timeout', async () => {
      vi.useFakeTimers();

      showWarning('10min');

      const overlay = document.querySelector('.warning-overlay');
      expect(overlay).toBeTruthy();

      // Cleanup before auto-dismiss
      cleanup();

      // Fast-forward past auto-dismiss time
      vi.advanceTimersByTime(5000);

      // Overlay should be removed immediately by cleanup, not by timeout
      expect(document.querySelector('.warning-overlay')).toBeFalsy();

      vi.useRealTimers();
    });
  });
});
