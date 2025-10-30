/**
 * Tests for admin settings module (Story 3.2).
 *
 * Covers:
 * - Form rendering and population
 * - Dirty state tracking
 * - Client-side validation
 * - Save functionality
 * - Reset functionality
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { initSettings } from './settings.js';

// Mock fetch
global.fetch = vi.fn();

// Mock confirm
global.confirm = vi.fn();

describe('Settings form rendering', () => {
  beforeEach(() => {
    // Setup DOM
    document.body.innerHTML = `
      <form id="settings-form">
        <input type="number" id="daily-limit" />
        <input type="number" id="grid-size" />
        <input type="checkbox" id="audio-enabled" />
        <button type="submit" id="save-btn"></button>
        <button type="button" id="reset-btn"></button>
        <div id="message-container" style="display: none;">
          <span id="message-text"></span>
        </div>
        <span id="daily-limit-error"></span>
        <span id="grid-size-error"></span>
      </form>
    `;

    // Reset mocks
    fetch.mockReset();
    confirm.mockReset();
  });

  it('should load and display current settings', async () => {
    // Arrange: Mock API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        settings: {
          daily_limit_minutes: 30,
          grid_size: 9,
          audio_enabled: true,
        },
      }),
    });

    // Act: Initialize
    initSettings();
    await new Promise((resolve) => setTimeout(resolve, 100)); // Wait for async

    // Assert: Form populated
    expect(document.getElementById('daily-limit').value).toBe('30');
    expect(document.getElementById('grid-size').value).toBe('9');
    expect(document.getElementById('audio-enabled').checked).toBe(true);
  });

  it('should disable save button on initial load', async () => {
    // Arrange: Mock API
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        settings: {
          daily_limit_minutes: 30,
          grid_size: 9,
          audio_enabled: true,
        },
      }),
    });

    // Act
    initSettings();
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Assert: Save button disabled (form not dirty)
    expect(document.getElementById('save-btn').disabled).toBe(true);
  });
});

describe('Dirty state tracking', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <form id="settings-form">
        <input type="number" id="daily-limit" value="30" />
        <input type="number" id="grid-size" value="9" />
        <input type="checkbox" id="audio-enabled" checked />
        <button type="submit" id="save-btn" disabled></button>
        <button type="button" id="reset-btn"></button>
        <div id="message-container" style="display: none;">
          <span id="message-text"></span>
        </div>
        <span id="daily-limit-error"></span>
        <span id="grid-size-error"></span>
      </form>
    `;

    fetch.mockReset();
  });

  it('should enable save button when form changes', async () => {
    // Arrange: Mock API
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        settings: {
          daily_limit_minutes: 30,
          grid_size: 9,
          audio_enabled: true,
        },
      }),
    });

    initSettings();
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Act: Change input
    const dailyLimit = document.getElementById('daily-limit');
    dailyLimit.value = '45';
    dailyLimit.dispatchEvent(new Event('input', { bubbles: true }));

    // Assert: Save button enabled
    expect(document.getElementById('save-btn').disabled).toBe(false);
  });

  it('should disable save button after successful save', async () => {
    // Arrange: Mock API for load and save
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        settings: {
          daily_limit_minutes: 30,
          grid_size: 9,
          audio_enabled: true,
        },
      }),
    });

    initSettings();
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Change value
    document.getElementById('daily-limit').value = '45';
    document
      .getElementById('daily-limit')
      .dispatchEvent(new Event('input', { bubbles: true }));

    // Mock save response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        settings: {
          daily_limit_minutes: 45,
          grid_size: 9,
          audio_enabled: true,
        },
        message: 'Innstillinger lagret',
      }),
    });

    // Act: Submit form
    const form = document.getElementById('settings-form');
    form.dispatchEvent(
      new Event('submit', { bubbles: true, cancelable: true })
    );
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Assert: Save button disabled again
    expect(document.getElementById('save-btn').disabled).toBe(true);
  });
});

describe('Client-side validation', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <form id="settings-form">
        <input type="number" id="daily-limit" value="30" />
        <input type="number" id="grid-size" value="9" />
        <input type="checkbox" id="audio-enabled" checked />
        <button type="submit" id="save-btn"></button>
        <button type="button" id="reset-btn"></button>
        <div id="message-container" style="display: none;">
          <span id="message-text"></span>
        </div>
        <span id="daily-limit-error" style="display: none;"></span>
        <span id="grid-size-error" style="display: none;"></span>
      </form>
    `;

    fetch.mockReset();
  });

  it('should show error for daily limit out of range', async () => {
    // Arrange: Mock API
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        settings: {
          daily_limit_minutes: 30,
          grid_size: 9,
          audio_enabled: true,
        },
      }),
    });

    initSettings();
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Act: Set invalid value (below min)
    const dailyLimit = document.getElementById('daily-limit');
    dailyLimit.value = '4';
    dailyLimit.dispatchEvent(new Event('input', { bubbles: true }));

    // Assert: Error shown and save button disabled
    const errorEl = document.getElementById('daily-limit-error');
    expect(errorEl.style.display).toBe('block');
    expect(errorEl.textContent).toContain('mellom 5 og 180');
    expect(document.getElementById('save-btn').disabled).toBe(true);
  });

  it('should show error for grid size out of range', async () => {
    // Arrange: Mock API
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        settings: {
          daily_limit_minutes: 30,
          grid_size: 9,
          audio_enabled: true,
        },
      }),
    });

    initSettings();
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Act: Set invalid value (above max)
    const gridSize = document.getElementById('grid-size');
    gridSize.value = '16';
    gridSize.dispatchEvent(new Event('input', { bubbles: true }));

    // Assert: Error shown and save button disabled
    const errorEl = document.getElementById('grid-size-error');
    expect(errorEl.style.display).toBe('block');
    expect(errorEl.textContent).toContain('mellom 4 og 15');
    expect(document.getElementById('save-btn').disabled).toBe(true);
  });
});

describe('Save functionality', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <form id="settings-form">
        <input type="number" id="daily-limit" value="30" />
        <input type="number" id="grid-size" value="9" />
        <input type="checkbox" id="audio-enabled" checked />
        <button type="submit" id="save-btn"></button>
        <button type="button" id="reset-btn"></button>
        <div id="message-container" style="display: none;">
          <span id="message-text"></span>
        </div>
        <span id="daily-limit-error"></span>
        <span id="grid-size-error"></span>
      </form>
    `;

    fetch.mockReset();
  });

  it('should call PUT /api/admin/settings with changed values only', async () => {
    // Arrange: Mock API
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        settings: {
          daily_limit_minutes: 30,
          grid_size: 9,
          audio_enabled: true,
        },
      }),
    });

    initSettings();
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Change only daily limit
    document.getElementById('daily-limit').value = '60';

    // Mock save response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        settings: {
          daily_limit_minutes: 60,
          grid_size: 9,
          audio_enabled: true,
        },
        message: 'Innstillinger lagret',
      }),
    });

    // Act: Submit
    const form = document.getElementById('settings-form');
    form.dispatchEvent(
      new Event('submit', { bubbles: true, cancelable: true })
    );
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Assert: Only changed field sent
    const putCall = fetch.mock.calls.find(
      (call) => call[0] === '/api/admin/settings' && call[1]?.method === 'PUT'
    );
    expect(putCall).toBeDefined();
    const body = JSON.parse(putCall[1].body);
    expect(body.daily_limit_minutes).toBe(60);
    expect(body.grid_size).toBeUndefined(); // Not changed
    expect(body.audio_enabled).toBeUndefined(); // Not changed
  });

  it('should show success message after save', async () => {
    // Arrange: Mock API
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        settings: {
          daily_limit_minutes: 30,
          grid_size: 9,
          audio_enabled: true,
        },
      }),
    });

    initSettings();
    await new Promise((resolve) => setTimeout(resolve, 100));

    document.getElementById('daily-limit').value = '45';

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        settings: {
          daily_limit_minutes: 45,
          grid_size: 9,
          audio_enabled: true,
        },
        message: 'Innstillinger lagret',
      }),
    });

    // Act
    const form = document.getElementById('settings-form');
    form.dispatchEvent(
      new Event('submit', { bubbles: true, cancelable: true })
    );
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Assert: Success message shown
    expect(document.getElementById('message-container').style.display).not.toBe(
      'none'
    );
    expect(document.getElementById('message-text').textContent).toContain(
      'Innstillinger lagret'
    );
  });
});

describe('Reset functionality', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <form id="settings-form">
        <input type="number" id="daily-limit" value="60" />
        <input type="number" id="grid-size" value="12" />
        <input type="checkbox" id="audio-enabled" />
        <button type="submit" id="save-btn"></button>
        <button type="button" id="reset-btn"></button>
        <div id="message-container" style="display: none;">
          <span id="message-text"></span>
        </div>
        <span id="daily-limit-error"></span>
        <span id="grid-size-error"></span>
      </form>
    `;

    fetch.mockReset();
    confirm.mockReset();
  });

  it('should show confirmation dialog before reset', async () => {
    // Arrange: Mock API
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        settings: {
          daily_limit_minutes: 60,
          grid_size: 12,
          audio_enabled: false,
        },
      }),
    });

    initSettings();
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Mock user cancels
    confirm.mockReturnValueOnce(false);

    // Act: Click reset
    document.getElementById('reset-btn').click();

    // Assert: Confirmation shown
    expect(confirm).toHaveBeenCalledWith(
      'Tilbakestill alle innstillinger til standardverdier?'
    );
  });

  it('should call POST /api/admin/settings/reset on confirm', async () => {
    // Arrange: Mock API
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        settings: {
          daily_limit_minutes: 60,
          grid_size: 12,
          audio_enabled: false,
        },
      }),
    });

    initSettings();
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Mock user confirms
    confirm.mockReturnValueOnce(true);

    // Mock reset response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        settings: {
          daily_limit_minutes: 30,
          grid_size: 9,
          audio_enabled: true,
        },
        message: 'Innstillinger tilbakestilt',
      }),
    });

    // Act: Click reset
    document.getElementById('reset-btn').click();
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Assert: Reset API called
    const resetCall = fetch.mock.calls.find(
      (call) => call[0] === '/api/admin/settings/reset'
    );
    expect(resetCall).toBeDefined();
    expect(resetCall[1].method).toBe('POST');
  });

  it('should reload settings after reset', async () => {
    // Arrange: Mock API
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        settings: {
          daily_limit_minutes: 60,
          grid_size: 12,
          audio_enabled: false,
        },
      }),
    });

    initSettings();
    await new Promise((resolve) => setTimeout(resolve, 100));

    confirm.mockReturnValueOnce(true);

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        settings: {
          daily_limit_minutes: 30,
          grid_size: 9,
          audio_enabled: true,
        },
        message: 'Innstillinger tilbakestilt',
      }),
    });

    // Act
    document.getElementById('reset-btn').click();
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Assert: Form shows defaults
    expect(document.getElementById('daily-limit').value).toBe('30');
    expect(document.getElementById('grid-size').value).toBe('9');
    expect(document.getElementById('audio-enabled').checked).toBe(true);
  });
});
