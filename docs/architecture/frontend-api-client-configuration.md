# Frontend API Client Configuration

All frontend API communication goes through a centralized API client in `shared/api.js`. This ensures consistent error handling, headers, and request configuration across the application.

## API Client Implementation

```javascript
// frontend/src/shared/api.js

/**
 * Centralized API client for all backend communication
 * Handles base URL, error handling, and response parsing
 */

// Base URL configuration (same origin for production)
const API_BASE_URL = window.location.origin;

/**
 * Generic API call function with error handling
 * @param {string} endpoint - API endpoint path (e.g., '/api/videos')
 * @param {Object} options - Fetch options (method, body, headers, etc.)
 * @returns {Promise<Object>} - Parsed JSON response
 * @throws {Error} - On network error or non-ok response
 */
async function apiCall(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const defaultOptions = {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    credentials: 'same-origin', // Include cookies for admin sessions
    ...options,
  };
  
  try {
    const response = await fetch(url, defaultOptions);
    
    // Check for HTTP errors
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        errorData.error || 'Request failed',
        errorData.message || `HTTP ${response.status}`
      );
    }
    
    // Parse JSON response
    return await response.json();
    
  } catch (error) {
    // Network errors (no response received)
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new ApiError(0, 'NetworkError', 'Ingen tilkobling til serveren');
    }
    
    // Re-throw ApiError instances
    if (error instanceof ApiError) {
      throw error;
    }
    
    // Unexpected errors
    console.error('Unexpected API error:', error);
    throw new ApiError(500, 'UnknownError', 'En uventet feil oppstod');
  }
}

/**
 * Custom error class for API errors
 */
class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

/**
 * API Methods - Child Interface
 */

export async function fetchVideos(count = 9) {
  return apiCall(`/api/videos?count=${count}`);
}

export async function logWatchedVideo(videoId, completed, durationWatchedSeconds) {
  return apiCall('/api/videos/watch', {
    method: 'POST',
    body: JSON.stringify({
      videoId,
      completed,
      durationWatchedSeconds,
    }),
  });
}

export async function markVideoUnavailable(videoId) {
  return apiCall('/api/videos/unavailable', {
    method: 'POST',
    body: JSON.stringify({ videoId }),
  });
}

export async function checkDailyLimit() {
  return apiCall('/api/limit/status');
}

/**
 * API Methods - Admin Interface
 */

export async function adminLogin(password) {
  return apiCall('/admin/login', {
    method: 'POST',
    body: JSON.stringify({ password }),
  });
}

export async function adminLogout() {
  return apiCall('/admin/logout', {
    method: 'POST',
  });
}

export async function fetchSources() {
  return apiCall('/admin/sources');
}

export async function addSource(input) {
  return apiCall('/admin/sources', {
    method: 'POST',
    body: JSON.stringify({ input }),
  });
}

export async function deleteSource(sourceId) {
  return apiCall(`/admin/sources/${sourceId}`, {
    method: 'DELETE',
  });
}

export async function refreshSource(sourceId) {
  return apiCall(`/admin/sources/${sourceId}/refresh`, {
    method: 'POST',
  });
}

export async function fetchWatchHistory(limit = 50, offset = 0) {
  return apiCall(`/admin/history?limit=${limit}&offset=${offset}`);
}

export async function replayVideo(videoId) {
  return apiCall('/admin/history/replay', {
    method: 'POST',
    body: JSON.stringify({ videoId }),
  });
}

export async function banVideo(videoId) {
  return apiCall('/admin/videos/ban', {
    method: 'POST',
    body: JSON.stringify({ videoId }),
  });
}

export async function fetchSettings() {
  return apiCall('/admin/settings');
}

export async function updateSettings(settings) {
  return apiCall('/admin/settings', {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}

export async function resetDailyLimit() {
  return apiCall('/admin/limit/reset', {
    method: 'POST',
  });
}

export async function fetchStats() {
  return apiCall('/admin/stats');
}

// Export ApiError for error handling in components
export { ApiError };
```

## Usage Examples

**Child Interface - Load Video Grid:**
```javascript
// frontend/src/child/grid.js
import { fetchVideos, ApiError } from '../shared/api.js';

async function loadVideoGrid() {
  const loadingElement = document.querySelector('[data-loading]');
  const gridElement = document.querySelector('[data-grid]');
  
  try {
    // Show loading state
    loadingElement.style.display = 'block';
    gridElement.style.display = 'none';
    
    // Fetch videos from API
    const data = await fetchVideos(9);
    
    // Render grid
    renderGrid(data.videos);
    updateLimitDisplay(data.dailyLimit);
    
    // Show grid
    loadingElement.style.display = 'none';
    gridElement.style.display = 'grid';
    
  } catch (error) {
    if (error instanceof ApiError) {
      console.error('API error:', error.code, error.message);
      
      if (error.status === 503) {
        // Service unavailable
        showMascotError('Ingen videoer tilgjengelig akkurat nå');
      } else {
        // Generic error
        showMascotError('Noe gikk galt');
      }
    } else {
      // Unexpected error
      console.error('Unexpected error:', error);
      showMascotError('Noe gikk galt');
    }
  }
}
```

**Child Interface - Log Watched Video:**
```javascript
// frontend/src/child/player.js
import { logWatchedVideo, markVideoUnavailable, ApiError } from '../shared/api.js';

async function handleVideoEnd(videoId, completed, watchedSeconds) {
  try {
    const result = await logWatchedVideo(videoId, completed, watchedSeconds);
    
    // Update local limit display
    updateLimitDisplay(result.dailyLimit);
    
    // Check if limit reached
    if (result.dailyLimit.currentState === 'grace') {
      window.location.href = '/grace';
    } else {
      returnToGrid();
    }
    
  } catch (error) {
    console.error('Failed to log watched video:', error);
    // Continue to grid anyway (log failure shouldn't block UX)
    returnToGrid();
  }
}

async function handleVideoError(videoId, errorCode) {
  // YouTube player reported error (video unavailable, etc.)
  try {
    await markVideoUnavailable(videoId);
  } catch (error) {
    console.error('Failed to mark video unavailable:', error);
  }
  
  // Show error to user
  showMascotError('Oops! Det videoen gjemmer seg!');
  
  // Auto-return after 5 seconds
  setTimeout(returnToGrid, 5000);
}
```

**Admin Interface - Add Source:**
```javascript
// frontend/src/admin/channels.js
import { addSource, ApiError } from '../shared/api.js';

async function handleAddSource(event) {
  event.preventDefault();
  
  const input = document.querySelector('#channel-input').value;
  const submitButton = document.querySelector('#submit-button');
  const errorElement = document.querySelector('#error-message');
  
  // Disable button during request
  submitButton.disabled = true;
  submitButton.textContent = 'Legger til...';
  errorElement.textContent = '';
  
  try {
    const result = await addSource(input);
    
    // Show success message
    if (result.partial) {
      showMessage(
        `${result.message} (${result.videosAdded} videoer lagt til)`,
        'warning'
      );
    } else {
      showMessage(result.message, 'success');
    }
    
    // Refresh source list
    await refreshSourceList();
    
    // Clear input
    document.querySelector('#channel-input').value = '';
    
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 409) {
        errorElement.textContent = 'Denne kanalen er allerede lagt til';
      } else if (error.status === 400) {
        errorElement.textContent = error.message || 'Ugyldig kanal URL';
      } else {
        errorElement.textContent = 'Kunne ikke legge til kanal. Prøv igjen.';
      }
    } else {
      errorElement.textContent = 'En uventet feil oppstod';
    }
    
    console.error('Error adding source:', error);
    
  } finally {
    // Re-enable button
    submitButton.disabled = false;
    submitButton.textContent = 'Legg til';
  }
}
```

## Error Handling Patterns

**Network Errors (No Connection):**
```javascript
try {
  const data = await fetchVideos();
} catch (error) {
  if (error instanceof ApiError && error.status === 0) {
    // Network error - no connection to server
    showError('Ingen tilkobling til serveren. Sjekk internettforbindelsen.');
  }
}
```

**HTTP Errors:**
```javascript
try {
  await adminLogin(password);
} catch (error) {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 401:
        showError('Feil passord');
        break;
      case 429:
        showError('For mange forsøk. Vent litt og prøv igjen.');
        break;
      case 500:
        showError('Serverfeil. Prøv igjen senere.');
        break;
      default:
        showError('En feil oppstod');
    }
  }
}
```

**Timeout Configuration (Optional):**
```javascript
// Add timeout to API calls if needed
async function apiCallWithTimeout(endpoint, options = {}, timeoutMs = 30000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  
  try {
    return await apiCall(endpoint, {
      ...options,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
}
```

## Testing the API Client

**Unit Test Example:**
```javascript
// frontend/tests/shared/api.test.js
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchVideos, ApiError } from '../../src/shared/api.js';

describe('API Client', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });
  
  it('fetchVideos returns video data on success', async () => {
    const mockData = {
      videos: [{ videoId: 'abc123', title: 'Test' }],
      dailyLimit: { minutesRemaining: 25 }
    };
    
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData
    });
    
    const result = await fetchVideos(9);
    
    expect(result).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/videos?count=9'),
      expect.any(Object)
    );
  });
  
  it('throws ApiError on HTTP error', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ error: 'ServiceUnavailable' })
    });
    
    await expect(fetchVideos()).rejects.toThrow(ApiError);
  });
  
  it('throws ApiError on network error', async () => {
    global.fetch.mockRejectedValueOnce(
      new TypeError('Failed to fetch')
    );
    
    await expect(fetchVideos()).rejects.toThrow(ApiError);
  });
});
```

---

