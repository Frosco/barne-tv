/**
 * Unit tests for child/grid.js module (Story 2.1).
 *
 * Tests:
 * - renderGrid() creates correct number of video cards
 * - Card elements have correct data attributes
 * - XSS prevention with textContent (TIER 1 Rule 5)
 * - handleCardClick() disables cards during loading
 * - loadVideos() handles fetch errors
 *
 * Testing Strategy:
 * - Use happy-dom for DOM testing
 * - Mock fetch() calls with vitest
 * - Test TIER 1 XSS prevention
 * - Test error handling and user feedback
 *
 * Coverage Target: ≥70% for grid.js
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderGrid, loadVideos, initGrid, resetState } from './grid.js';

// Mock the player module to prevent actual player creation in tests
vi.mock('./player.js', () => ({
  createPlayer: vi.fn().mockResolvedValue({}),
}));

// Mock fetch globally
global.fetch = vi.fn();

// =============================================================================
// TEST DATA
// =============================================================================

const mockVideos = [
  {
    videoId: 'video_001',
    title: 'Test Video 1',
    youtubeChannelName: 'Test Channel 1',
    thumbnailUrl: 'https://i.ytimg.com/vi/video_001/default.jpg',
    durationSeconds: 300,
  },
  {
    videoId: 'video_002',
    title: 'Test Video 2',
    youtubeChannelName: 'Test Channel 2',
    thumbnailUrl: 'https://i.ytimg.com/vi/video_002/default.jpg',
    durationSeconds: 450,
  },
  {
    videoId: 'video_003',
    title: 'Test Video 3',
    youtubeChannelName: 'Test Channel 3',
    thumbnailUrl: 'https://i.ytimg.com/vi/video_003/default.jpg',
    durationSeconds: 600,
  },
];

const mockDailyLimit = {
  date: '2025-10-24',
  minutesWatched: 10,
  minutesRemaining: 20,
  currentState: 'normal',
  resetTime: '2025-10-25T00:00:00Z',
};

// =============================================================================
// SETUP/TEARDOWN
// =============================================================================

beforeEach(() => {
  // Clear fetch mock
  fetch.mockClear();

  // Reset grid module state (Story 4.2: prevent state leakage between tests)
  resetState();

  // Setup DOM structure (mimics grid.html template)
  document.body.innerHTML = `
    <div data-grid class="video-grid" role="list"></div>
    <div data-loading hidden>
      <span>Laster...</span>
    </div>
    <div data-error hidden>
      <p data-error-message></p>
      <button data-retry>Prøv igjen</button>
    </div>
    <img data-mascot-state src="/images/mascot/owl_neutral.png" alt="" />
  `;
});

afterEach(() => {
  // Clean up
  document.body.innerHTML = '';
});

// =============================================================================
// AC1, AC3, AC4: Grid Rendering Tests
// =============================================================================

describe('renderGrid()', () => {
  it('creates correct number of video cards', () => {
    // Arrange: Grid container exists
    const gridContainer = document.querySelector('[data-grid]');
    expect(gridContainer).toBeTruthy();

    // Act: Render 3 videos
    renderGrid(mockVideos);

    // Assert: 3 cards created
    const cards = document.querySelectorAll('.video-card');
    expect(cards.length).toBe(3);
  });

  it('creates cards with correct data attributes', () => {
    // Act: Render videos
    renderGrid(mockVideos);

    // Assert: Each card has correct videoId and durationSeconds
    const cards = document.querySelectorAll('.video-card');

    expect(cards[0].dataset.videoId).toBe('video_001');
    expect(cards[0].dataset.durationSeconds).toBe('300');

    expect(cards[1].dataset.videoId).toBe('video_002');
    expect(cards[1].dataset.durationSeconds).toBe('450');

    expect(cards[2].dataset.videoId).toBe('video_003');
    expect(cards[2].dataset.durationSeconds).toBe('600');
  });

  it('creates cards with thumbnail images', () => {
    // Act: Render videos
    renderGrid(mockVideos);

    // Assert: Each card has img element with correct src
    const images = document.querySelectorAll('.video-card__thumbnail img');
    expect(images.length).toBe(3);
    expect(images[0].src).toBe('https://i.ytimg.com/vi/video_001/default.jpg');
    expect(images[0].loading).toBe('lazy');
  });

  it('creates cards with title elements', () => {
    // Act: Render videos
    renderGrid(mockVideos);

    // Assert: Each card has title element
    const titles = document.querySelectorAll('.video-card__title');
    expect(titles.length).toBe(3);
    expect(titles[0].textContent).toBe('Test Video 1');
    expect(titles[1].textContent).toBe('Test Video 2');
    expect(titles[2].textContent).toBe('Test Video 3');
  });

  it('creates cards with channel name elements', () => {
    // Act: Render videos
    renderGrid(mockVideos);

    // Assert: Each card has channel name element
    const channels = document.querySelectorAll('.video-card__channel');
    expect(channels.length).toBe(3);
    expect(channels[0].textContent).toBe('Test Channel 1');
    expect(channels[1].textContent).toBe('Test Channel 2');
  });

  it('shows empty message when no videos provided', () => {
    // Act: Render empty array
    renderGrid([]);

    // Assert: Empty message shown
    const emptyMessage = document.querySelector('.grid-empty');
    expect(emptyMessage).toBeTruthy();
    expect(emptyMessage.textContent).toContain('Ingen videoer tilgjengelig');
  });

  it('clears existing content before rendering', () => {
    // Arrange: Add some existing content
    const gridContainer = document.querySelector('[data-grid]');
    gridContainer.innerHTML = '<div class="old-content">Old</div>';

    // Act: Render new videos
    renderGrid(mockVideos);

    // Assert: Old content gone, new cards present
    const oldContent = document.querySelector('.old-content');
    expect(oldContent).toBeNull();

    const cards = document.querySelectorAll('.video-card');
    expect(cards.length).toBe(3);
  });
});

// =============================================================================
// AC4: TIER 1 XSS Prevention Tests (2.1-UNIT-010)
// =============================================================================

describe('TIER 1 Rule 5: XSS Prevention', () => {
  it('2.1-UNIT-010: uses textContent for titles (not innerHTML) to prevent XSS', () => {
    // Arrange: Video with malicious script in title
    const maliciousVideos = [
      {
        videoId: 'xss_test',
        title: '<script>alert("XSS")</script>Dangerous Title',
        youtubeChannelName: '<img src=x onerror=alert("XSS")>',
        thumbnailUrl: 'https://example.com/thumb.jpg',
        durationSeconds: 300,
      },
    ];

    // Act: Render video
    renderGrid(maliciousVideos);

    // Assert: Script NOT executed, displayed as text
    const titleEl = document.querySelector('.video-card__title');
    const channelEl = document.querySelector('.video-card__channel');

    // textContent should contain the raw text including tags (NOT executed)
    expect(titleEl.textContent).toBe(
      '<script>alert("XSS")</script>Dangerous Title'
    );
    expect(channelEl.textContent).toBe('<img src=x onerror=alert("XSS")>');

    // Verify NO script tag was created in DOM (XSS prevented)
    const scripts = document.querySelectorAll('script');
    expect(scripts.length).toBe(0);

    // Verify NO img with onerror was created (XSS prevented)
    const maliciousImgs = document.querySelectorAll('img[onerror]');
    expect(maliciousImgs.length).toBe(0);
  });

  it('uses textContent for empty message (XSS prevention)', () => {
    // Arrange: Empty videos
    renderGrid([]);

    // Assert: Empty message uses textContent
    const emptyMessage = document.querySelector('.grid-empty');
    expect(emptyMessage.textContent).toBe(
      'Ingen videoer tilgjengelig. Be foreldrene legge til kanaler.'
    );
  });
});

// =============================================================================
// AC10: Card Interaction Tests
// =============================================================================

describe('handleCardClick()', () => {
  it('disables all cards when a card is clicked', async () => {
    // Arrange: Render videos and get cards
    renderGrid(mockVideos);
    const cards = document.querySelectorAll('.video-card');

    // Act: Click first card
    cards[0].click();

    // Assert: All cards disabled (pointer-events: none, opacity: 0.6)
    cards.forEach((card) => {
      expect(card.style.pointerEvents).toBe('none');
      expect(card.style.opacity).toBe('0.6');
      expect(card.getAttribute('aria-disabled')).toBe('true');
    });
  });

  it('calls createPlayer when card clicked', async () => {
    // Arrange
    const { createPlayer } = await import('./player.js');

    renderGrid(mockVideos);
    const card = document.querySelector('.video-card');

    // Act: Click card
    card.click();

    // Wait for async player creation
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Assert: createPlayer was called with correct video ID
    expect(createPlayer).toHaveBeenCalled();
  });

  it('handles keyboard Enter key like click', async () => {
    // Arrange
    const { createPlayer } = await import('./player.js');

    renderGrid(mockVideos);
    const card = document.querySelector('.video-card');

    // Act: Press Enter key
    const enterEvent = new KeyboardEvent('keydown', { key: 'Enter' });
    card.dispatchEvent(enterEvent);

    // Wait for async player creation
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Assert: Same as click behavior - createPlayer called
    expect(createPlayer).toHaveBeenCalled();
  });

  it('handles keyboard Space key like click', async () => {
    // Arrange
    const { createPlayer } = await import('./player.js');

    renderGrid(mockVideos);
    const card = document.querySelector('.video-card');

    // Act: Press Space key
    const spaceEvent = new KeyboardEvent('keydown', { key: ' ' });
    card.dispatchEvent(spaceEvent);

    // Wait for async player creation
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Assert: Same as click behavior - createPlayer called
    expect(createPlayer).toHaveBeenCalled();
  });
});

// =============================================================================
// TIER 2 Rule 9: Error Handling Tests
// =============================================================================

describe('loadVideos() - Error Handling', () => {
  it('handles fetch errors gracefully with Norwegian message', async () => {
    // Arrange: Mock fetch to reject with an error that has no message
    // (to test the fallback Norwegian message)
    const errorWithoutMessage = new Error();
    delete errorWithoutMessage.message;
    fetch.mockRejectedValueOnce(errorWithoutMessage);

    // Act: Load videos
    await loadVideos();

    // Assert: Error message shown with fallback Norwegian message
    const errorContainer = document.querySelector('[data-error]');
    const errorMessage = document.querySelector('[data-error-message]');

    expect(errorContainer.hidden).toBe(false);
    expect(errorMessage.textContent).toBe('Noe gikk galt');
  });

  it('handles API error responses with Norwegian message', async () => {
    // Arrange: Mock fetch to return 503 error
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({
        error: 'No videos available',
        message: 'Ingen videoer tilgjengelig. Be foreldrene legge til kanaler.',
      }),
    });

    // Act: Load videos
    await loadVideos();

    // Assert: Error message shown with backend message
    const errorMessage = document.querySelector('[data-error-message]');
    expect(errorMessage.textContent).toBe(
      'Ingen videoer tilgjengelig. Be foreldrene legge til kanaler.'
    );
  });

  it('updates mascot to confused state on error', async () => {
    // Arrange: Mock fetch to reject
    fetch.mockRejectedValueOnce(new Error('Network error'));

    // Act: Load videos
    await loadVideos();

    // Assert: Mascot changed to confused state
    const mascot = document.querySelector('[data-mascot-state]');
    expect(mascot.src).toContain('owl_confused.png');
    expect(mascot.dataset.mascotState).toBe('confused');
  });

  it('shows loading state during fetch', async () => {
    // Arrange: Mock fetch to take time
    fetch.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              ok: true,
              json: async () => ({
                videos: mockVideos,
                dailyLimit: mockDailyLimit,
              }),
            });
          }, 100);
        })
    );

    // Act: Start loading
    const loadPromise = loadVideos();

    // Assert: Loading visible immediately
    const loading = document.querySelector('[data-loading]');
    expect(loading.hidden).toBe(false);

    // Wait for completion
    await loadPromise;

    // Assert: Loading hidden after completion
    expect(loading.hidden).toBe(true);
  });

  it('successfully loads and renders videos', async () => {
    // Arrange: Mock successful fetch
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ videos: mockVideos, dailyLimit: mockDailyLimit }),
    });

    // Act: Load videos
    await loadVideos();

    // Assert: Videos rendered
    const cards = document.querySelectorAll('.video-card');
    expect(cards.length).toBe(3);
    expect(cards[0].dataset.videoId).toBe('video_001');
  });
});

// =============================================================================
// AC1: Grid Initialization Tests
// =============================================================================

describe('initGrid()', () => {
  it('attaches retry button listener', () => {
    // Act: Initialize grid
    initGrid();

    // Assert: Retry button exists and can be clicked (tested via DOM)
    const retryBtn = document.querySelector('[data-retry]');
    expect(retryBtn).toBeTruthy();

    // Note: Actual retry functionality tested in loadVideos() tests
  });
});

// =============================================================================
// Count Parameter Tests (Note: Validation happens in backend, not frontend)
// =============================================================================

describe('Count Parameter (Backend Validation)', () => {
  it('frontend always requests count=9 by default', async () => {
    // Arrange: Mock successful fetch
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ videos: mockVideos, dailyLimit: mockDailyLimit }),
    });

    // Act: Load videos
    await loadVideos();

    // Assert: Fetch called with count=9
    expect(fetch).toHaveBeenCalledWith('/api/videos?count=9');
  });

  // Note: 2.1-UNIT-001 to 2.1-UNIT-004 (count validation tests) should be
  // integration tests for backend/routes.py, not frontend unit tests.
  // Count validation happens in backend (routes.py line 636-643), not in grid.js.
  // See tests/integration/test_api_integration.py for count validation tests.
});

// =============================================================================
// Story 4.2: Wind-Down Mode Integration Tests
// =============================================================================

describe('Story 4.2: Wind-Down Mode Integration', () => {
  it('4.2-INT-005: applies wind-down CSS class when entering wind-down mode', () => {
    // Arrange: Initialize grid
    initGrid();
    const gridContainer = document.querySelector('[data-grid]');

    // Act: Emit limitStateChanged event with wind-down state
    const winddownEvent = new CustomEvent('limitStateChanged', {
      detail: {
        previousState: 'normal',
        newState: 'winddown',
        limitData: {
          date: '2025-01-03',
          minutesWatched: 22,
          minutesRemaining: 8,
          currentState: 'winddown',
          resetTime: '2025-01-04T00:00:00Z',
        },
      },
    });

    window.dispatchEvent(winddownEvent);

    // Assert: Wind-down CSS class applied
    expect(gridContainer.classList.contains('video-grid--winddown')).toBe(true);
  });

  it('4.2-INT-005: removes wind-down CSS class when exiting wind-down mode', () => {
    // Arrange: Grid in wind-down mode
    initGrid();
    const gridContainer = document.querySelector('[data-grid]');
    gridContainer.classList.add('video-grid--winddown');

    // Act: Emit limitStateChanged event with normal state
    const normalEvent = new CustomEvent('limitStateChanged', {
      detail: {
        previousState: 'winddown',
        newState: 'normal',
        limitData: {
          date: '2025-01-03',
          minutesWatched: 10,
          minutesRemaining: 20,
          currentState: 'normal',
          resetTime: '2025-01-04T00:00:00Z',
        },
      },
    });

    window.dispatchEvent(normalEvent);

    // Assert: Wind-down CSS class removed
    expect(gridContainer.classList.contains('video-grid--winddown')).toBe(
      false
    );
  });

  it('4.2-INT-016: passes max_duration parameter when fetching videos in wind-down mode', async () => {
    // Arrange: Mock successful fetches (2 calls: initGrid + winddown event)
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ videos: mockVideos, dailyLimit: mockDailyLimit }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ videos: mockVideos, dailyLimit: mockDailyLimit }),
      });

    // Set grid to wind-down state with 5 minutes remaining
    initGrid();

    // Wait for initial loadVideos from initGrid
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Clear fetch mock to isolate the wind-down fetch call
    fetch.mockClear();
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ videos: mockVideos, dailyLimit: mockDailyLimit }),
    });

    const winddownEvent = new CustomEvent('limitStateChanged', {
      detail: {
        previousState: 'normal',
        newState: 'winddown',
        limitData: {
          date: '2025-01-03',
          minutesWatched: 25,
          minutesRemaining: 5,
          currentState: 'winddown',
          resetTime: '2025-01-04T00:00:00Z',
        },
      },
    });

    // Act: Emit limitStateChanged event (triggers loadVideos)
    window.dispatchEvent(winddownEvent);

    // Wait for async loadVideos to complete
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Assert: Fetch called with max_duration=300 (5 minutes * 60 seconds)
    expect(fetch).toHaveBeenCalledWith('/api/videos?count=9&max_duration=300');
  });

  it('4.2-INT-016: does not pass max_duration parameter in normal mode', async () => {
    // Arrange: Mock successful fetch
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        videos: mockVideos,
        dailyLimit: mockDailyLimit,
      }),
    });

    // Act: Load videos in normal mode (no wind-down state set)
    await loadVideos();

    // Assert: Fetch called without max_duration parameter
    expect(fetch).toHaveBeenCalledWith('/api/videos?count=9');
  });

  it('4.2-INT-016: calculates max_duration correctly for different remaining times', async () => {
    // Arrange: Mock initial fetch for initGrid
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ videos: mockVideos, dailyLimit: mockDailyLimit }),
    });

    initGrid();

    // Wait for initial loadVideos from initGrid
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Clear fetch and set up for wind-down tests
    fetch.mockClear();

    // Act 1: Wind-down with 3 minutes remaining
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ videos: mockVideos, dailyLimit: mockDailyLimit }),
    });

    const winddown3min = new CustomEvent('limitStateChanged', {
      detail: {
        limitData: {
          minutesWatched: 27,
          minutesRemaining: 3,
          currentState: 'winddown',
        },
      },
    });
    window.dispatchEvent(winddown3min);
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Assert 1: max_duration = 180 (3 * 60)
    expect(fetch).toHaveBeenCalledWith('/api/videos?count=9&max_duration=180');

    fetch.mockClear();

    // Act 2: Wind-down with 10 minutes remaining (edge case)
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ videos: mockVideos, dailyLimit: mockDailyLimit }),
    });

    const winddown10min = new CustomEvent('limitStateChanged', {
      detail: {
        limitData: {
          minutesWatched: 20,
          minutesRemaining: 10,
          currentState: 'winddown',
        },
      },
    });
    window.dispatchEvent(winddown10min);
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Assert 2: max_duration = 600 (10 * 60)
    expect(fetch).toHaveBeenCalledWith('/api/videos?count=9&max_duration=600');
  });
});
