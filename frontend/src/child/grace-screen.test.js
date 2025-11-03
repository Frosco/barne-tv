/**
 * Unit tests for grace-screen.js (Story 4.3, Task 17).
 *
 * Tests grace screen functionality including:
 * - Time countdown calculation
 * - Button handlers
 * - Video grid rendering
 * - Grace video selection
 *
 * Target: 70% coverage (acceptable for UI components)
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { calculateTimeUntilReset, initGraceScreen } from './grace-screen.js';

describe('grace-screen', () => {
  describe('calculateTimeUntilReset', () => {
    afterEach(() => {
      vi.useRealTimers();
    });

    it('should return formatted Norwegian time string with hours', () => {
      // AC 9: Countdown displays time until reset in Norwegian

      // Mock current time: 2025-01-15 14:30:00 UTC
      const mockNow = new Date('2025-01-15T14:30:00Z');
      vi.useFakeTimers();
      vi.setSystemTime(mockNow);

      // Midnight UTC tomorrow: 2025-01-16 00:00:00 UTC
      // Difference: 9 hours 30 minutes

      const result = calculateTimeUntilReset();

      expect(result).toBe('9 timer og 30 minutter');
    });

    it('should return formatted Norwegian time string without hours', () => {
      // Mock current time: 2025-01-15 23:15:00 UTC
      const mockNow = new Date('2025-01-15T23:15:00Z');
      vi.useFakeTimers();
      vi.setSystemTime(mockNow);

      // Midnight UTC tomorrow: 2025-01-16 00:00:00 UTC
      // Difference: 0 hours 45 minutes

      const result = calculateTimeUntilReset();

      expect(result).toBe('45 minutter');
    });

    it('should handle time close to midnight', () => {
      // Mock current time: 2025-01-15 23:58:00 UTC
      const mockNow = new Date('2025-01-15T23:58:00Z');
      vi.useFakeTimers();
      vi.setSystemTime(mockNow);

      // Midnight UTC tomorrow: 2025-01-16 00:00:00 UTC
      // Difference: 0 hours 2 minutes

      const result = calculateTimeUntilReset();

      expect(result).toBe('2 minutter');
    });
  });

  describe('initGraceScreen', () => {
    beforeEach(() => {
      // Set up DOM structure for grace screen
      document.body.innerHTML = `
        <div class="grace-screen">
          <div class="grace-content">
            <button id="grace-yes-btn">Ja, én til! 🎉</button>
            <button id="grace-no-btn">Nei, ha det! 👋</button>
            <span id="time-until-reset"></span>
            <div id="grace-video-grid"></div>
          </div>
        </div>
      `;
    });

    afterEach(() => {
      document.body.innerHTML = '';
      vi.clearAllMocks();
      vi.useRealTimers();
    });

    it('should attach click handlers to buttons', () => {
      // AC 3: Two buttons exist and are interactive

      const yesButton = document.getElementById('grace-yes-btn');
      const noButton = document.getElementById('grace-no-btn');

      // Spy on addEventListener
      const yesAddEventListener = vi.spyOn(yesButton, 'addEventListener');
      const noAddEventListener = vi.spyOn(noButton, 'addEventListener');

      initGraceScreen();

      expect(yesAddEventListener).toHaveBeenCalledWith(
        'click',
        expect.any(Function)
      );
      expect(noAddEventListener).toHaveBeenCalledWith(
        'click',
        expect.any(Function)
      );
    });

    it('should update countdown display on init', () => {
      // AC 9: Countdown displays correctly

      // Mock current time
      const mockNow = new Date('2025-01-15T20:00:00Z');
      vi.useFakeTimers();
      vi.setSystemTime(mockNow);

      const countdownElement = document.getElementById('time-until-reset');

      initGraceScreen();

      // Should show 4 hours until midnight UTC
      expect(countdownElement.textContent).toBe('4 timer og 0 minutter');
    });

    it('should navigate to goodbye when No button clicked', async () => {
      // AC 6: "Nei" button navigates to goodbye

      // Mock window.location.href
      delete window.location;
      window.location = { href: '' };

      const noButton = document.getElementById('grace-no-btn');

      initGraceScreen();

      // Simulate click
      noButton.click();

      expect(window.location.href).toBe('/goodbye');
    });

    it('should fetch and display grace videos when Yes button clicked', async () => {
      // AC 11: "Ja" button fetches grace videos and shows grid

      // Mock fetch
      const mockVideos = [
        {
          videoId: 'grace1',
          title: 'Grace Video 1',
          thumbnailUrl: 'https://example.com/thumb1.jpg',
          durationSeconds: 180,
        },
        {
          videoId: 'grace2',
          title: 'Grace Video 2',
          thumbnailUrl: 'https://example.com/thumb2.jpg',
          durationSeconds: 240,
        },
      ];

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ videos: mockVideos }),
        })
      );

      const yesButton = document.getElementById('grace-yes-btn');

      initGraceScreen();

      // Simulate click
      yesButton.click();

      // Wait for async operation
      await new Promise((resolve) => setTimeout(resolve, 10));

      // Assert: fetch called with correct URL
      expect(global.fetch).toHaveBeenCalledWith('/api/videos?count=6');

      // Assert: Grid is populated
      const gridContainer = document.getElementById('grace-video-grid');
      const videoCards = gridContainer.querySelectorAll('.video-card--grace');

      expect(videoCards.length).toBe(2);
      expect(gridContainer.style.display).toBe('grid');
    });

    it('should handle fetch error gracefully when Yes button clicked', async () => {
      // TIER 2 Rule 9: Handle API errors gracefully
      // Story 4.3 UX-001: Inline error instead of alert

      // Mock fetch failure
      global.fetch = vi.fn(() => Promise.reject(new Error('Network error')));

      const yesButton = document.getElementById('grace-yes-btn');
      const noButton = document.getElementById('grace-no-btn');

      initGraceScreen();

      // Simulate click
      yesButton.click();

      // Wait for async operation
      await new Promise((resolve) => setTimeout(resolve, 10));

      // Assert: Inline error displayed (check for error element in DOM)
      const errorElement = document.querySelector('.grace-error');
      expect(errorElement).toBeTruthy();
      expect(
        errorElement.querySelector('.grace-error__message').textContent
      ).toBe(
        'Ingen videoer tilgjengelig akkurat nå. Prøv igjen eller velg "Nei, ha det!"'
      );

      // Assert: Buttons re-enabled
      expect(yesButton.disabled).toBe(false);
      expect(noButton.disabled).toBe(false);
    });
  });

  describe('grace video grid rendering', () => {
    beforeEach(() => {
      document.body.innerHTML = `
        <div id="grace-video-grid"></div>
      `;
    });

    afterEach(() => {
      document.body.innerHTML = '';
      vi.clearAllMocks();
    });

    it('should render video cards with correct structure', async () => {
      // AC 11: Grace grid shows 4-6 videos
      // TIER 1 Rule 5: Use createElement and textContent

      const mockVideos = [
        {
          videoId: 'vid1',
          title: 'Test Video 1',
          thumbnailUrl: 'https://example.com/thumb1.jpg',
          durationSeconds: 180, // 3 minutes
        },
        {
          videoId: 'vid2',
          title: 'Test Video 2',
          thumbnailUrl: 'https://example.com/thumb2.jpg',
          durationSeconds: 300, // 5 minutes
        },
      ];

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ videos: mockVideos }),
        })
      );

      // Simulate grace screen setup
      document.body.innerHTML = `
        <button id="grace-yes-btn">Ja</button>
        <button id="grace-no-btn">Nei</button>
        <div id="grace-video-grid"></div>
      `;

      initGraceScreen();

      const yesButton = document.getElementById('grace-yes-btn');
      yesButton.click();

      await new Promise((resolve) => setTimeout(resolve, 10));

      const gridContainer = document.getElementById('grace-video-grid');
      const videoCards = gridContainer.querySelectorAll('.video-card--grace');

      // Assert: 2 video cards created
      expect(videoCards.length).toBe(2);

      // Assert: First card structure
      const firstCard = videoCards[0];
      expect(firstCard.dataset.videoId).toBe('vid1');
      expect(firstCard.dataset.duration).toBe('180');

      const thumbnail = firstCard.querySelector('.video-card__thumbnail');
      expect(thumbnail.src).toBe('https://example.com/thumb1.jpg');

      const title = firstCard.querySelector('.video-card__title');
      expect(title.textContent).toBe('Test Video 1');

      const duration = firstCard.querySelector('.video-card__duration');
      expect(duration.textContent).toBe('3 min'); // 180 seconds / 60 = 3
    });

    it('should navigate with gracePlay flag when video card clicked', async () => {
      // AC 5: Grace video selection uses gracePlay flag

      const mockVideos = [
        {
          videoId: 'grace_video_123',
          title: 'Grace Video',
          thumbnailUrl: 'https://example.com/thumb.jpg',
          durationSeconds: 240,
        },
      ];

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ videos: mockVideos }),
        })
      );

      // Mock window.location.href
      delete window.location;
      window.location = { href: '' };

      document.body.innerHTML = `
        <button id="grace-yes-btn">Ja</button>
        <button id="grace-no-btn">Nei</button>
        <div id="grace-video-grid"></div>
      `;

      initGraceScreen();

      const yesButton = document.getElementById('grace-yes-btn');
      yesButton.click();

      await new Promise((resolve) => setTimeout(resolve, 10));

      // Click on video card
      const videoCard = document.querySelector('.video-card--grace');
      videoCard.click();

      // Assert: Navigated with gracePlay flag
      expect(window.location.href).toBe(
        '/video/grace_video_123?gracePlay=true'
      );
    });

    it('should show Norwegian message when no videos available', async () => {
      // TIER 3 Rule 14: Norwegian UI messages
      // Story 4.3 UX-001: Inline error instead of alert

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ videos: [] }),
        })
      );

      document.body.innerHTML = `
        <button id="grace-yes-btn">Ja</button>
        <button id="grace-no-btn">Nei</button>
        <div class="grace-content">
          <div id="grace-video-grid"></div>
        </div>
      `;

      initGraceScreen();

      const yesButton = document.getElementById('grace-yes-btn');
      yesButton.click();

      await new Promise((resolve) => setTimeout(resolve, 10));

      // Assert: Inline error displayed with Norwegian message
      const errorElement = document.querySelector('.grace-error');
      expect(errorElement).toBeTruthy();
      expect(
        errorElement.querySelector('.grace-error__message').textContent
      ).toBe(
        'Ingen videoer tilgjengelig akkurat nå. Prøv igjen eller velg "Nei, ha det!"'
      );
    });
  });
});
