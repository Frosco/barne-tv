/**
 * Tests for Child Limit Tracker Module (Story 4.1, Task 10)
 *
 * Tests:
 * - Poll interval execution
 * - State change event emission
 * - Error handling and recovery
 * - Memory-only state (no localStorage)
 * - Page Visibility API integration
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { initLimitTracker, getCurrentState, cleanup } from './limit-tracker.js';

describe('Limit Tracker', () => {
  let fetchMock;
  let originalFetch;
  let eventListeners;

  beforeEach(() => {
    // Save original fetch
    originalFetch = global.fetch;

    // Set up fetch mock
    fetchMock = vi.fn();
    global.fetch = fetchMock;

    // Track event listeners (not mocking to allow real event system to work)
    eventListeners = {};

    // Clean up any existing timers
    vi.clearAllTimers();
    vi.useFakeTimers();
  });

  afterEach(() => {
    // Restore original fetch
    global.fetch = originalFetch;

    // Clean up tracker
    cleanup();

    // Restore timers
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('should fetch limit status immediately on init', async () => {
    // Arrange
    const mockLimitData = {
      date: '2025-01-03',
      minutesWatched: 10,
      minutesRemaining: 20,
      currentState: 'normal',
      resetTime: '2025-01-04T00:00:00Z',
    };

    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => mockLimitData,
    });

    // Act
    initLimitTracker();

    // Wait for initial fetch to complete (before any timers)
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    // Assert
    expect(fetchMock).toHaveBeenCalledWith('/api/limit/status');
  });

  it('should poll every 30 seconds', async () => {
    // Arrange
    const mockLimitData = {
      date: '2025-01-03',
      minutesWatched: 10,
      minutesRemaining: 20,
      currentState: 'normal',
      resetTime: '2025-01-04T00:00:00Z',
    };

    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => mockLimitData,
    });

    // Act
    initLimitTracker();

    // Wait for initial fetch
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    const initialCallCount = fetchMock.mock.calls.length;

    // Advance 30 seconds and wait for next fetch
    vi.advanceTimersByTime(30000);
    await vi.waitFor(() =>
      expect(fetchMock.mock.calls.length).toBe(initialCallCount + 1)
    );

    const secondCallCount = fetchMock.mock.calls.length;

    // Advance another 30 seconds and wait for next fetch
    vi.advanceTimersByTime(30000);
    await vi.waitFor(() =>
      expect(fetchMock.mock.calls.length).toBe(secondCallCount + 1)
    );
  });

  it('should emit limitStateChanged event when state changes', async () => {
    // Arrange
    const initialData = {
      date: '2025-01-03',
      minutesWatched: 10,
      minutesRemaining: 20,
      currentState: 'normal',
      resetTime: '2025-01-04T00:00:00Z',
    };

    const updatedData = {
      date: '2025-01-03',
      minutesWatched: 22,
      minutesRemaining: 8,
      currentState: 'winddown',
      resetTime: '2025-01-04T00:00:00Z',
    };

    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => initialData,
      })
      .mockResolvedValue({
        ok: true,
        json: async () => updatedData,
      });

    // Set up event listener
    const eventHandler = vi.fn();
    window.addEventListener('limitStateChanged', eventHandler);

    // Act
    initLimitTracker();

    // Wait for initial fetch
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    // Advance to next poll with state change
    vi.advanceTimersByTime(30000);

    // Wait for event to be emitted
    await vi.waitFor(() => expect(eventHandler).toHaveBeenCalledTimes(1));

    // Assert
    expect(eventHandler.mock.calls[0][0].detail).toMatchObject({
      previousState: 'normal',
      newState: 'winddown',
    });
  });

  it('should emit graceLimitReached event when entering grace state', async () => {
    // Arrange
    const initialData = {
      date: '2025-01-03',
      minutesWatched: 25,
      minutesRemaining: 5,
      currentState: 'winddown',
      resetTime: '2025-01-04T00:00:00Z',
    };

    const graceData = {
      date: '2025-01-03',
      minutesWatched: 30,
      minutesRemaining: 0,
      currentState: 'grace',
      resetTime: '2025-01-04T00:00:00Z',
    };

    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => initialData,
      })
      .mockResolvedValue({
        ok: true,
        json: async () => graceData,
      });

    // Set up event listeners
    const stateChangedHandler = vi.fn();
    const graceReachedHandler = vi.fn();
    window.addEventListener('limitStateChanged', stateChangedHandler);
    window.addEventListener('graceLimitReached', graceReachedHandler);

    // Act
    initLimitTracker();

    // Wait for initial fetch
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    // Enter grace state on next poll
    vi.advanceTimersByTime(30000);

    // Wait for events
    await vi.waitFor(() =>
      expect(stateChangedHandler).toHaveBeenCalledTimes(1)
    );
    await vi.waitFor(() =>
      expect(graceReachedHandler).toHaveBeenCalledTimes(1)
    );
  });

  it('should handle fetch errors gracefully without breaking polling', async () => {
    // Arrange
    const mockLimitData = {
      date: '2025-01-03',
      minutesWatched: 10,
      minutesRemaining: 20,
      currentState: 'normal',
      resetTime: '2025-01-04T00:00:00Z',
    };

    // First call fails, subsequent calls succeed
    fetchMock
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValue({
        ok: true,
        json: async () => mockLimitData,
      });

    // Act
    initLimitTracker();

    // Wait for first fetch (will fail)
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    // Polling should continue despite error
    vi.advanceTimersByTime(30000);

    // Wait for second fetch (will succeed)
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });

  it('should increase poll interval to 60s after 3 consecutive errors', async () => {
    // Arrange
    const mockLimitData = {
      date: '2025-01-03',
      minutesWatched: 10,
      minutesRemaining: 20,
      currentState: 'normal',
      resetTime: '2025-01-04T00:00:00Z',
    };

    // First 3 calls fail, 4th succeeds
    fetchMock
      .mockRejectedValueOnce(new Error('Error 1'))
      .mockRejectedValueOnce(new Error('Error 2'))
      .mockRejectedValueOnce(new Error('Error 3'))
      .mockResolvedValue({
        ok: true,
        json: async () => mockLimitData,
      });

    // Act
    initLimitTracker();

    // First fetch (fails)
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    // Second fetch after 30s (fails)
    vi.advanceTimersByTime(30000);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

    // Third fetch after 30s (fails)
    vi.advanceTimersByTime(30000);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));

    const callsAfter3Failures = fetchMock.mock.calls.length;

    // After 3 failures, interval should increase to 60s
    // Advance 30s - should NOT fetch yet
    await vi.advanceTimersByTimeAsync(30000);
    expect(fetchMock.mock.calls.length).toBe(callsAfter3Failures); // Still 3

    // Advance another 30s (total 60s) - should fetch now
    await vi.advanceTimersByTimeAsync(30000);
    await vi.waitFor(() =>
      expect(fetchMock.mock.calls.length).toBeGreaterThan(callsAfter3Failures)
    );
  });

  it('should store state in memory only (no localStorage)', async () => {
    // Arrange
    const mockLimitData = {
      date: '2025-01-03',
      minutesWatched: 15,
      minutesRemaining: 15,
      currentState: 'normal',
      resetTime: '2025-01-04T00:00:00Z',
    };

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => mockLimitData,
    });

    // Spy on localStorage
    const localStorageSpy = vi.spyOn(Storage.prototype, 'setItem');

    // Act
    initLimitTracker();
    await vi.runOnlyPendingTimersAsync();

    // Verify state is accessible
    const currentState = getCurrentState();
    expect(currentState).toEqual(mockLimitData);

    // Assert - localStorage should NEVER be used
    expect(localStorageSpy).not.toHaveBeenCalled();
  });

  it('should reset state on cleanup', async () => {
    // Arrange
    const mockLimitData = {
      date: '2025-01-03',
      minutesWatched: 10,
      minutesRemaining: 20,
      currentState: 'normal',
      resetTime: '2025-01-04T00:00:00Z',
    };

    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => mockLimitData,
    });

    // Act
    initLimitTracker();
    await vi.runOnlyPendingTimersAsync();

    // Verify state exists
    expect(getCurrentState()).not.toBeNull();

    // Clean up
    cleanup();

    // Assert - state should be cleared
    expect(getCurrentState()).toBeNull();

    // Polling should stop (no more fetches after cleanup)
    const fetchCountAfterCleanup = fetchMock.mock.calls.length;
    vi.advanceTimersByTime(60000);
    await vi.runOnlyPendingTimersAsync();
    expect(fetchMock.mock.calls.length).toBe(fetchCountAfterCleanup);
  });

  it('should pause polling when tab is hidden (Page Visibility API)', async () => {
    // Arrange
    const mockLimitData = {
      date: '2025-01-03',
      minutesWatched: 10,
      minutesRemaining: 20,
      currentState: 'normal',
      resetTime: '2025-01-04T00:00:00Z',
    };

    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => mockLimitData,
    });

    // Mock document visibility API
    Object.defineProperty(document, 'hidden', {
      writable: true,
      value: false,
    });

    // Act: Initialize tracker
    initLimitTracker();

    // Wait for initial fetch
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    const initialCallCount = fetchMock.mock.calls.length;

    // Simulate tab becoming hidden
    Object.defineProperty(document, 'hidden', {
      writable: true,
      value: true,
    });
    document.dispatchEvent(new Event('visibilitychange'));

    // Advance time by 30 seconds (normal poll interval)
    vi.advanceTimersByTime(30000);
    await vi.runOnlyPendingTimersAsync();

    // Assert: Polling should pause (no new fetch while hidden)
    expect(fetchMock.mock.calls.length).toBe(
      initialCallCount,
      'Polling should pause when tab is hidden'
    );

    // Simulate tab becoming visible again
    Object.defineProperty(document, 'hidden', {
      writable: true,
      value: false,
    });
    document.dispatchEvent(new Event('visibilitychange'));

    // Wait a bit for immediate resume fetch
    await vi.runOnlyPendingTimersAsync();

    // Polling should resume (fetch should happen)
    await vi.waitFor(() =>
      expect(fetchMock.mock.calls.length).toBeGreaterThan(initialCallCount)
    );
  });
});
