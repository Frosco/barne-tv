# API Specification

The application uses a REST API for communication between frontend and backend. All endpoints return JSON responses (except static file serving). The API is organized into two logical groups: **Child Interface** (public, unauthenticated) and **Admin Interface** (protected by session authentication).

## API Design Principles

- **Child endpoints**: Minimal, focused on video selection and playback tracking
- **Admin endpoints**: CRUD operations for content management
- **Session-based auth**: Cookie-based sessions for admin, no auth for child
- **JSON responses**: All API responses use consistent JSON structure
- **Error handling**: Standardized error response format

## Base URL Structure

```
Production:  https://youtube-viewer.yourdomain.com
Local Dev:   http://localhost:8000
```

## Authentication Flow

**Admin Session:**
```javascript
/**
 * @typedef {Object} SessionCookie
 * @property {string} session_id - Encrypted session identifier
 * @property {number} expires - Expiration timestamp (24 hours from login)
 */
```

**Admin endpoints require valid session cookie.** If missing or expired:
```json
{
  "error": "Unauthorized",
  "redirect": "/admin/login"
}
```

---

## Child Interface Endpoints

### GET /api/videos

**Purpose:** Fetch videos for the child's grid based on watch history and time limits.

**Authentication:** None required

**Query Parameters:**
- `count` (optional, default 9): Number of videos to return (4-15)

**Request Example:**
```http
GET /api/videos?count=9
```

**Response Success (200):**
```json
{
  "videos": [
    {
      "videoId": "dQw4w9WgXcQ",
      "title": "Excavator Song for Kids",
      "youtubeChannelName": "Blippi",
      "thumbnailUrl": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
      "durationSeconds": 245
    }
  ],
  "dailyLimit": {
    "date": "2025-01-03",
    "minutesWatched": 15,
    "minutesRemaining": 15,
    "currentState": "normal",
    "resetTime": "2025-01-04T00:00:00Z"
  }
}
```

**Response Error (503):**
```json
{
  "error": "No videos available",
  "message": "Ingen videoer tilgjengelig. Be foreldrene legge til kanaler."
}
```

### POST /api/videos/watch

**Purpose:** Log that a video was watched (called when video ends or ESC pressed).

**Authentication:** None required

**Request Body:**
```json
{
  "videoId": "dQw4w9WgXcQ",
  "completed": true,
  "durationWatchedSeconds": 245
}
```

**Response Success (200):**
```json
{
  "success": true,
  "dailyLimit": {
    "date": "2025-01-03",
    "minutesWatched": 19,
    "minutesRemaining": 11,
    "currentState": "winddown",
    "resetTime": "2025-01-04T00:00:00Z"
  }
}
```

### POST /api/videos/unavailable

**Purpose:** Mark video as unavailable when YouTube returns playback error.

**Authentication:** None required

**Request Body:**
```json
{
  "videoId": "dQw4w9WgXcQ"
}
```

**Response Success (200):**
```json
{
  "success": true
}
```

### GET /api/limit/status

**Purpose:** Check current daily limit status without fetching videos.

**Authentication:** None required

**Response Success (200):**
```json
{
  "dailyLimit": {
    "date": "2025-01-03",
    "minutesWatched": 28,
    "minutesRemaining": 2,
    "currentState": "winddown",
    "resetTime": "2025-01-04T00:00:00Z"
  }
}
```

---

## Admin Interface Endpoints

### POST /admin/login

**Purpose:** Authenticate parent and create session.

**Authentication:** None required (creates session)

**Request Body:**
```json
{
  "password": "parent_password_here"
}
```

**Response Success (200):**
```json
{
  "success": true,
  "redirect": "/admin/dashboard"
}
```

**Sets cookie:** `session_id` (HttpOnly, Secure, SameSite=Lax, Max-Age=86400)

**Response Error (401):**
```json
{
  "error": "Invalid password",
  "message": "Feil passord"
}
```

### POST /admin/logout

**Purpose:** End admin session.

**Authentication:** Required

**Response Success (200):**
```json
{
  "success": true,
  "redirect": "/admin/login"
}
```

### GET /admin/sources

**Purpose:** List all content sources with metadata.

**Authentication:** Required

**Response Success (200):**
```json
{
  "sources": [
    {
      "id": 1,
      "sourceId": "UCrwObTfqv8u1KO7Fgk-FXHQ",
      "sourceType": "channel",
      "name": "Blippi",
      "videoCount": 487,
      "lastRefresh": "2025-01-03T08:00:00Z",
      "fetchMethod": "api",
      "addedAt": "2025-01-01T12:00:00Z"
    }
  ]
}
```

### POST /admin/sources

**Purpose:** Add new content source (channel or playlist).

**Authentication:** Required

**Request Body:**
```json
{"input": "https://www.youtube.com/channel/UCrwObTfqv8u1KO7Fgk-FXHQ"}
```

**Response Success (200):**
```json
{
  "success": true,
  "source": {
    "id": 3,
    "sourceId": "UCrwObTfqv8u1KO7Fgk-FXHQ",
    "sourceType": "channel",
    "name": "Blippi",
    "videoCount": 487,
    "lastRefresh": "2025-01-03T10:15:00Z",
    "fetchMethod": "api",
    "addedAt": "2025-01-03T10:15:00Z"
  },
  "videosAdded": 487,
  "message": "Kanal lagt til: Blippi (487 videoer)"
}
```

**Response Partial Fetch (200):**
```json
{
  "success": true,
  "partial": true,
  "source": {
    "id": 3,
    "sourceId": "UCrwObTfqv8u1KO7Fgk-FXHQ",
    "sourceType": "channel",
    "name": "Blippi",
    "videoCount": 600,
    "lastRefresh": "2025-01-03T10:15:00Z",
    "fetchMethod": "api",
    "addedAt": "2025-01-03T10:15:00Z"
  },
  "videosAdded": 600,
  "estimatedTotal": "flere",
  "message": "Lagt til 600 videoer (nettverksfeil). Klikk 'Oppdater' for å hente resten.",
  "retryAvailable": true
}
```

**Response Error (409):**
```json
{
  "error": "Already exists",
  "message": "Denne kanalen er allerede lagt til"
}
```

### POST /admin/sources/{id}/refresh

**Purpose:** Manually refresh videos from a content source.

**Authentication:** Required

**Response Success (200):**
```json
{
  "success": true,
  "videosAdded": 12,
  "videosUpdated": 3,
  "lastRefresh": "2025-01-03T11:00:00Z",
  "message": "Oppdatert: 12 nye videoer"
}
```

### POST /admin/refresh-all

**Purpose:** Refresh all content sources (called by weekly systemd timer).

**Authentication:** Required

**Response Success (200):**
```json
{
  "success": true,
  "sourcesRefreshed": 8,
  "totalVideosAdded": 45,
  "message": "Alle kilder oppdatert"
}
```

### DELETE /admin/sources/{id}

**Purpose:** Remove content source and all its videos (cascade delete).

**Authentication:** Required

**Response Success (200):**
```json
{
  "success": true,
  "videosRemoved": 487,
  "message": "Kilde fjernet: Blippi (487 videoer slettet)"
}
```

### GET /admin/history

**Purpose:** Get watch history with optional filtering.

**Authentication:** Required

**Query Parameters:**
- `limit` (optional, default 50): Number of entries
- `offset` (optional, default 0): Pagination offset
- `date` (optional): Filter by date (YYYY-MM-DD)

**Response Success (200):**
```json
{
  "history": [
    {
      "id": 123,
      "videoId": "dQw4w9WgXcQ",
      "videoTitle": "Excavator Song for Kids",
      "channelName": "Blippi",
      "watchedAt": "2025-01-03T10:30:00Z",
      "completed": true,
      "manualPlay": false,
      "gracePlay": false,
      "durationWatchedSeconds": 245
    }
  ],
  "total": 156
}
```

### POST /admin/history/replay

**Purpose:** Manually play specific video (bypasses time limit).

**Authentication:** Required

**Request Body:**
```json
{
  "videoId": "dQw4w9WgXcQ"
}
```

**Response Success (200):**
```json
{
  "success": true,
  "videoId": "dQw4w9WgXcQ",
  "embedUrl": "https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1&rel=0&modestbranding=1"
}
```

### POST /admin/videos/ban

**Purpose:** Ban a video from appearing in child's grid.

**Authentication:** Required

**Request Body:**
```json
{
  "videoId": "dQw4w9WgXcQ"
}
```

**Response Success (200):**
```json
{
  "success": true,
  "message": "Video blokkert"
}
```

### DELETE /admin/videos/ban/{videoId}

**Purpose:** Unban a video.

**Authentication:** Required

**Response Success (200):**
```json
{
  "success": true,
  "message": "Video tillatt igjen"
}
```

### GET /admin/settings

**Purpose:** Get all current settings.

**Authentication:** Required

**Response Success (200):**
```json
{
  "settings": {
    "daily_limit_minutes": 30,
    "grid_size": 9,
    "audio_enabled": true
  }
}
```

### PUT /admin/settings

**Purpose:** Update settings (partial update supported).

**Authentication:** Required

**Request Body:**
```json
{
  "daily_limit_minutes": 45,
  "grid_size": 12
}
```

**Response Success (200):**
```json
{
  "success": true,
  "settings": {
    "daily_limit_minutes": 45,
    "grid_size": 12,
    "audio_enabled": true
  },
  "message": "Innstillinger lagret"
}
```

### POST /admin/limit/reset

**Purpose:** Reset daily limit (parent override for special occasions).

**Authentication:** Required

**Response Success (200):**
```json
{
  "success": true,
  "message": "Grense tilbakestilt (12 videoer slettet)"
}
```

### GET /admin/backup

**Purpose:** Download database backup.

**Authentication:** Required

**Response:** Binary SQLite database file

### GET /admin/stats

**Purpose:** Dashboard statistics.

**Authentication:** Required

**Response Success (200):**
```json
{
  "totalVideos": 1245,
  "totalSources": 8,
  "videosWatchedToday": 12,
  "minutesWatchedToday": 28,
  "bannedVideosCount": 3,
  "lastRefresh": "2025-01-03T08:00:00Z"
}
```

### GET /health

**Purpose:** Health check endpoint for monitoring.

**Authentication:** None required

**Response Success (200):**
```json
{
  "status": "ok",
  "timestamp": "2025-01-04T10:30:00Z"
}
```

---

## Error Response Format

All errors follow consistent structure:

```javascript
/**
 * @typedef {Object} ErrorResponse
 * @property {string} error - Error type
 * @property {string} message - Human-readable message (Norwegian for admin)
 * @property {string} [redirect] - Optional redirect URL for auth errors
 */
```

**HTTP Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (auth required)
- `404` - Not Found
- `409` - Conflict (duplicate resource)
- `500` - Internal Server Error
- `503` - Service Unavailable (YouTube API down)

---

