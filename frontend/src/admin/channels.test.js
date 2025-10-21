/**
 * Unit tests for channel management module (Story 1.5).
 *
 * Tests:
 * - renderChannelTable() - Renders channel data correctly
 * - handleAddChannel() - Input validation and API interaction
 * - handleRemove() - Confirmation dialog and DELETE API call
 * - handleRefresh() - POST refresh API call
 *
 * Testing strategy:
 * - Use happy-dom for DOM testing
 * - Mock fetch() calls with vitest
 * - Test error handling and user feedback
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Mock fetch globally
global.fetch = vi.fn();

// =============================================================================
// TEST DATA
// =============================================================================

const mockChannels = [
  {
    id: 1,
    sourceId: 'UCtest1',
    sourceType: 'channel',
    name: 'Test Channel 1',
    videoCount: 50,
    lastRefresh: '2023-12-01T00:00:00Z',
    addedAt: '2023-11-01T00:00:00Z',
  },
  {
    id: 2,
    sourceId: 'PLtest2',
    sourceType: 'playlist',
    name: 'Test Playlist 1',
    videoCount: 30,
    lastRefresh: '2023-12-02T00:00:00Z',
    addedAt: '2023-11-02T00:00:00Z',
  },
];

// =============================================================================
// SETUP/TEARDOWN
// =============================================================================

beforeEach(() => {
  // Clear fetch mock
  fetch.mockClear();

  // Setup basic DOM structure
  document.body.innerHTML = `
    <div data-message-container class="message-container hidden">
      <span data-message-text></span>
    </div>
    <form data-add-channel-form>
      <input type="text" data-channel-input placeholder="YouTube kanal URL eller ID" />
      <button type="submit" data-add-button>Legg til</button>
    </form>
    <table data-channels-table>
      <tbody data-channels-tbody>
        <tr data-loading-row>
          <td colspan="5">Laster...</td>
        </tr>
        <tr data-empty-state class="hidden">
          <td colspan="5">Ingen kanaler lagt til</td>
        </tr>
      </tbody>
    </table>
    <div data-confirm-dialog class="hidden">
      <p data-confirm-message></p>
      <p data-confirm-details></p>
      <button data-confirm-cancel>Avbryt</button>
      <button data-confirm-delete>Ja, fjern</button>
    </div>
    <div data-loading-overlay class="hidden">
      <span>Laster...</span>
    </div>
  `;
});

afterEach(() => {
  document.body.innerHTML = '';
});

// =============================================================================
// renderChannelTable() TESTS
// =============================================================================

describe('renderChannelTable', () => {
  it('renders correct number of rows', async () => {
    // Import module
    const { initChannelManagement } = await import('./channels.js');

    // Mock successful API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: mockChannels }),
    });

    // Initialize
    initChannelManagement();

    // Wait for loadChannels to complete
    await vi.waitFor(() => {
      const rows = document.querySelectorAll('[data-channels-tbody] tr');
      // Should have 2 channel rows (loading/empty rows hidden)
      const visibleRows = Array.from(rows).filter(
        (row) =>
          !row.hasAttribute('data-loading-row') &&
          !row.hasAttribute('data-empty-state')
      );
      expect(visibleRows.length).toBe(2);
    });
  });

  it('displays channel names correctly', async () => {
    const { initChannelManagement } = await import('./channels.js');

    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: mockChannels }),
    });

    initChannelManagement();

    await vi.waitFor(() => {
      const tbody = document.querySelector('[data-channels-tbody]');
      expect(tbody.textContent).toContain('Test Channel 1');
      expect(tbody.textContent).toContain('Test Playlist 1');
    });
  });

  it('attaches event listeners to action buttons', async () => {
    const { initChannelManagement } = await import('./channels.js');

    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: mockChannels }),
    });

    initChannelManagement();

    await vi.waitFor(() => {
      // Check that refresh and remove buttons exist
      const refreshButtons = document.querySelectorAll('[data-refresh-btn]');
      const removeButtons = document.querySelectorAll('[data-remove-btn]');

      expect(refreshButtons.length).toBe(2);
      expect(removeButtons.length).toBe(2);
    });
  });

  it('shows empty state when no channels', async () => {
    const { initChannelManagement } = await import('./channels.js');

    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: [] }),
    });

    initChannelManagement();

    await vi.waitFor(() => {
      const emptyState = document.querySelector('[data-empty-state]');
      expect(emptyState.style.display).toBe('block');
    });
  });
});

// =============================================================================
// handleAddChannel() TESTS
// =============================================================================

describe('handleAddChannel', () => {
  it('validates input not empty', async () => {
    const { initChannelManagement } = await import('./channels.js');

    // Mock initial load
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: [] }),
    });

    initChannelManagement();

    await vi.waitFor(() => {
      const input = document.querySelector('[data-channel-input]');
      expect(input).toBeTruthy();
    });

    // Try to submit with empty input
    const form = document.querySelector('[data-add-channel-form]');
    const input = document.querySelector('[data-channel-input]');
    input.value = '';

    const submitEvent = new Event('submit', {
      bubbles: true,
      cancelable: true,
    });
    form.dispatchEvent(submitEvent);

    // Should not make API call with empty input
    // (Initial load was 1 call, no additional calls should be made)
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('makes correct API call with valid input', async () => {
    const { initChannelManagement } = await import('./channels.js');

    // Mock initial load
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: [] }),
    });

    initChannelManagement();

    await vi.waitFor(() => {
      const input = document.querySelector('[data-channel-input]');
      expect(input).toBeTruthy();
    });

    // Mock add channel response
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => ({
        success: true,
        videosAdded: 42,
        message: 'Kanal lagt til: Test Channel (42 videoer)',
      }),
    });

    // Mock reload channels
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: mockChannels }),
    });

    // Fill and submit form
    const form = document.querySelector('[data-add-channel-form]');
    const input = document.querySelector('[data-channel-input]');
    input.value = 'https://www.youtube.com/channel/UCtest';

    const submitEvent = new Event('submit', {
      bubbles: true,
      cancelable: true,
    });
    form.dispatchEvent(submitEvent);

    await vi.waitFor(() => {
      // Should have made POST request to /admin/sources
      const calls = fetch.mock.calls;
      const addCall = calls.find(
        (call) => call[0] === '/admin/sources' && call[1]?.method === 'POST'
      );
      expect(addCall).toBeTruthy();
      expect(addCall[1].body).toContain('UCtest');
    });
  });

  it('shows success message on successful add', async () => {
    const { initChannelManagement } = await import('./channels.js');

    // Mock initial load
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: [] }),
    });

    initChannelManagement();

    await vi.waitFor(() => {
      const input = document.querySelector('[data-channel-input]');
      expect(input).toBeTruthy();
    });

    // Mock successful add
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => ({
        success: true,
        videosAdded: 42,
        message: 'Kanal lagt til: Test Channel (42 videoer)',
      }),
    });

    // Mock reload
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: mockChannels }),
    });

    const form = document.querySelector('[data-add-channel-form]');
    const input = document.querySelector('[data-channel-input]');
    input.value = 'https://www.youtube.com/channel/UCtest';

    form.dispatchEvent(
      new Event('submit', { bubbles: true, cancelable: true })
    );

    await vi.waitFor(() => {
      const messageContainer = document.querySelector(
        '[data-message-container]'
      );
      const messageText = document.querySelector('[data-message-text]');
      expect(messageContainer.classList.contains('hidden')).toBe(false);
      expect(messageText.textContent).toContain('Kanal lagt til');
    });
  });

  it('shows error message on failure', async () => {
    const { initChannelManagement } = await import('./channels.js');

    // Mock initial load
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: [] }),
    });

    initChannelManagement();

    await vi.waitFor(() => {
      const input = document.querySelector('[data-channel-input]');
      expect(input).toBeTruthy();
    });

    // Mock error response
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: () => ({
        error: 'Invalid input',
        message: 'Ugyldig YouTube-URL',
      }),
    });

    const form = document.querySelector('[data-add-channel-form]');
    const input = document.querySelector('[data-channel-input]');
    input.value = 'invalid-url';

    form.dispatchEvent(
      new Event('submit', { bubbles: true, cancelable: true })
    );

    await vi.waitFor(() => {
      const messageText = document.querySelector('[data-message-text]');
      expect(messageText.textContent).toContain('Ugyldig');
    });
  });

  it('clears input field after successful add', async () => {
    const { initChannelManagement } = await import('./channels.js');

    // Mock initial load
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: [] }),
    });

    initChannelManagement();

    await vi.waitFor(() => {
      const input = document.querySelector('[data-channel-input]');
      expect(input).toBeTruthy();
    });

    // Mock successful add
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => ({
        success: true,
        videosAdded: 42,
        message: 'Kanal lagt til',
      }),
    });

    // Mock reload
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: mockChannels }),
    });

    const form = document.querySelector('[data-add-channel-form]');
    const input = document.querySelector('[data-channel-input]');
    input.value = 'https://www.youtube.com/channel/UCtest';

    form.dispatchEvent(
      new Event('submit', { bubbles: true, cancelable: true })
    );

    await vi.waitFor(() => {
      expect(input.value).toBe('');
    });
  });
});

// =============================================================================
// handleRemove() TESTS
// =============================================================================

describe('handleRemove', () => {
  it('shows confirmation dialog when remove button clicked', async () => {
    const { initChannelManagement } = await import('./channels.js');

    // Mock initial load with channels
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: mockChannels }),
    });

    initChannelManagement();

    await vi.waitFor(() => {
      const removeButtons = document.querySelectorAll('[data-remove-btn]');
      expect(removeButtons.length).toBeGreaterThan(0);
    });

    // Click remove button
    const removeBtn = document.querySelector('[data-remove-btn]');
    removeBtn.click();

    await vi.waitFor(() => {
      const dialog = document.querySelector('[data-confirm-dialog]');
      expect(dialog.style.display).toBe('flex');
    });
  });

  it('makes DELETE call when confirmed', async () => {
    const { initChannelManagement } = await import('./channels.js');

    // Mock initial load
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: mockChannels }),
    });

    initChannelManagement();

    await vi.waitFor(() => {
      const removeButtons = document.querySelectorAll('[data-remove-btn]');
      expect(removeButtons.length).toBeGreaterThan(0);
    });

    // Click remove button
    const removeBtn = document.querySelector('[data-remove-btn]');
    removeBtn.click();

    await vi.waitFor(() => {
      const dialog = document.querySelector('[data-confirm-dialog]');
      expect(dialog.style.display).toBe('flex');
    });

    // Mock DELETE response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({
        success: true,
        videosRemoved: 50,
        message: 'Kilde fjernet: Test Channel 1 (50 videoer slettet)',
      }),
    });

    // Mock reload
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: [] }),
    });

    // Click confirm button
    const confirmBtn = document.querySelector('[data-confirm-delete]');
    confirmBtn.click();

    await vi.waitFor(() => {
      // Check DELETE was called
      const deleteCalls = fetch.mock.calls.filter(
        (call) => call[1]?.method === 'DELETE'
      );
      expect(deleteCalls.length).toBeGreaterThan(0);
    });
  });

  it('does not call API when cancelled', async () => {
    const { initChannelManagement } = await import('./channels.js');

    // Mock initial load
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: mockChannels }),
    });

    initChannelManagement();

    await vi.waitFor(() => {
      const removeButtons = document.querySelectorAll('[data-remove-btn]');
      expect(removeButtons.length).toBeGreaterThan(0);
    });

    const initialCallCount = fetch.mock.calls.length;

    // Click remove button
    const removeBtn = document.querySelector('[data-remove-btn]');
    removeBtn.click();

    await vi.waitFor(() => {
      const dialog = document.querySelector('[data-confirm-dialog]');
      expect(dialog.style.display).toBe('flex');
    });

    // Click cancel button
    const cancelBtn = document.querySelector('[data-confirm-cancel]');
    cancelBtn.click();

    // Wait a bit to ensure no API call was made
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Should not have made any additional API calls
    expect(fetch.mock.calls.length).toBe(initialCallCount);
  });
});

// =============================================================================
// handleRefresh() TESTS
// =============================================================================

describe('handleRefresh', () => {
  it('makes POST call to refresh endpoint', async () => {
    const { initChannelManagement } = await import('./channels.js');

    // Mock initial load
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: mockChannels }),
    });

    initChannelManagement();

    await vi.waitFor(() => {
      const refreshButtons = document.querySelectorAll('[data-refresh-btn]');
      expect(refreshButtons.length).toBeGreaterThan(0);
    });

    // Mock refresh response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({
        success: true,
        videosAdded: 5,
        message: 'Oppdatert: 5 nye videoer',
      }),
    });

    // Mock reload
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: mockChannels }),
    });

    // Click refresh button
    const refreshBtn = document.querySelector('[data-refresh-btn]');
    refreshBtn.click();

    await vi.waitFor(() => {
      // Check POST to refresh endpoint was called
      const postCalls = fetch.mock.calls.filter(
        (call) => call[1]?.method === 'POST'
      );
      const refreshCall = postCalls.find((call) =>
        call[0].includes('/refresh')
      );
      expect(refreshCall).toBeTruthy();
    });
  });

  it('shows success message after refresh', async () => {
    const { initChannelManagement } = await import('./channels.js');

    // Mock initial load
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: mockChannels }),
    });

    initChannelManagement();

    await vi.waitFor(() => {
      const refreshButtons = document.querySelectorAll('[data-refresh-btn]');
      expect(refreshButtons.length).toBeGreaterThan(0);
    });

    // Mock refresh response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({
        success: true,
        videosAdded: 5,
        message: 'Oppdatert: 5 nye videoer',
      }),
    });

    // Mock reload
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: mockChannels }),
    });

    // Click refresh button
    const refreshBtn = document.querySelector('[data-refresh-btn]');
    refreshBtn.click();

    await vi.waitFor(() => {
      const messageText = document.querySelector('[data-message-text]');
      expect(messageText.textContent).toContain('Oppdatert');
    });
  });

  it('shows error message on refresh failure', async () => {
    const { initChannelManagement } = await import('./channels.js');

    // Mock initial load
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => ({ sources: mockChannels }),
    });

    initChannelManagement();

    await vi.waitFor(() => {
      const refreshButtons = document.querySelectorAll('[data-refresh-btn]');
      expect(refreshButtons.length).toBeGreaterThan(0);
    });

    // Mock error response
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: () => ({
        error: 'Not found',
        message: 'Kilde ikke funnet',
      }),
    });

    // Click refresh button
    const refreshBtn = document.querySelector('[data-refresh-btn]');
    refreshBtn.click();

    await vi.waitFor(() => {
      const messageText = document.querySelector('[data-message-text]');
      expect(messageText.textContent).toContain('ikke funnet');
    });
  });
});
