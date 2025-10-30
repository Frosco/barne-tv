# Epic 3: Parent Features & History

**Goal:** Provide comprehensive parent management capabilities and viewing history tracking.

**Deliverable:** Parent has complete control over settings and can review watch history.

## Story 3.1: Watch History and Manual Replay

As a parent,
I want to view complete watch history and manually replay any video,
so that I can see what my child watched and review content.

**Architecture Context:**

This story implements watch history display and manual replay functionality, building on architectural decisions from the foundation phase:

*Database Design (docs/architecture/database-schema.md):*
- `watch_history` table uses denormalized storage: `video_title` and `channel_name` are stored directly so history survives video deletion or content source removal
- `manual_play` flag (boolean): Set to `true` for admin preview playback, excluded from daily limit calculations (TIER 1 requirement)
- `watched_at` timestamps stored in UTC ISO 8601 format (e.g., "2025-01-03T10:30:00Z")
- Existing indexes: `idx_watch_history_watched_at` (sorting), `idx_watch_history_date` (date filtering), `idx_watch_history_video` (video lookups)
- Required new index: `idx_watch_history_channel` for channel filtering performance

*API Endpoints (docs/architecture/api-specification.md):*
- `GET /admin/history?limit=50&offset=0&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&channel=name&search=term`
  - Returns: `{history: [...], total: number}`
  - Requires admin session authentication via `require_auth()`
  - Response includes: id, videoId, videoTitle, channelName, watchedAt, completed, manualPlay, gracePlay, durationWatchedSeconds
- `POST /admin/history/replay` with `{videoId: string}`
  - Returns: `{success: true, videoId: string, embedUrl: string}`
  - Sets `manual_play=true` flag when logging view
  - Embed URL format: `https://www.youtube.com/embed/{videoId}?autoplay=1&rel=0&modestbranding=1`

*Frontend Integration:*
- Reuses existing `player.js` component (from Story 2.2) in modal context
- Admin template: `frontend/templates/admin/history.html`
- Admin module: `frontend/js/admin/history.js`
- Norwegian UI text throughout (dates, buttons, labels)
- Thumbnail URLs constructed from videoId: `https://i.ytimg.com/vi/{videoId}/default.jpg` (with fallback to videos table JOIN if needed)

*Technical Constraints:*
- All-synchronous operations (no async/await in backend)
- UTC time handling (TIER 1): Use `datetime.now(timezone.utc)` and `DATE('now')` in SQL
- SQL placeholders mandatory (TIER 1): Never use string formatting for queries
- Admin session required: All endpoints use `require_auth()` middleware

**Acceptance Criteria:**
1. Admin page displays all watched videos with timestamps
   - API: `GET /admin/history` with admin session authentication (`require_auth()`)
   - Template: `frontend/templates/admin/history.html`
   - Module: `frontend/js/admin/history.js`

2. History sorted by most recent first
   - SQL: `ORDER BY watched_at DESC`
   - Uses `idx_watch_history_watched_at` index for performance

3. Each entry shows: thumbnail, title, channel name, date/time watched, duration
   - **Thumbnail:** Constructed from videoId using `https://i.ytimg.com/vi/{videoId}/default.jpg` (with LEFT JOIN to videos table as fallback)
   - **Title & Channel:** Retrieved from denormalized `watch_history.video_title` and `watch_history.channel_name` (survives video deletion)
   - **Watched at:** UTC timestamp converted to local time in frontend, Norwegian date format
   - **Duration:** From `durationWatchedSeconds` field, formatted as MM:SS

4. Filtering options: by date range, by channel, ~~by child (future-proofing)~~
   - **Date range:** Query parameters `date_from=YYYY-MM-DD` and `date_to=YYYY-MM-DD` (replaces single `date` parameter)
   - **Channel filter:** Query parameter `channel=name` (requires new `idx_watch_history_channel` index)
   - **Child filtering:** Removed from v1 scope (no `child_id` in current schema)
   - Filters work in combination (AND logic)

5. Search functionality to find specific videos by title
   - Query parameter: `search=term`
   - Implementation: SQL `LIKE '%term%' COLLATE NOCASE` for v1
   - Future optimization: SQLite FTS5 virtual table if performance degrades

6. "Play Video" button opens video in modal player within admin interface
   - API: `POST /admin/history/replay` with `{videoId: string}`
   - Returns: `{success: true, videoId: string, embedUrl: string}`
   - Player: Reuses existing `player.js` component from Story 2.2 in modal context (not fullscreen navigation)
   - Technology: YouTube IFrame API with parameters `autoplay=1&rel=0&modestbranding=1`
   - Closes on ESC key, returns to history page

7. Video plays without adding to child's history (admin preview mode)
   - Database: `manual_play=true` flag set in watch_history row
   - **TIER 1 requirement:** Videos with `manual_play=true` are excluded from daily limit calculations
   - Logic: `WHERE manual_play = 0 AND grace_play = 0` in all limit queries
   - Only logs history if video completes (ESC cancels without logging)

8. History data stored permanently (not cleared automatically)
   - Denormalized design rationale: `video_title` and `channel_name` stored in `watch_history` table
   - Parent can review history even after videos are deleted or content sources removed
   - No automatic cleanup or archival

9. Export history to CSV functionality (optional - Phase 4 enhancement)
   - API: `GET /admin/history/export?format=csv&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&channel=name`
   - Response: `Content-Type: text/csv` with `Content-Disposition: attachment; filename=history_YYYY-MM-DD.csv`
   - Encoding: UTF-8 with BOM (Excel compatibility)
   - Date format: Norwegian DD.MM.YYYY HH:MM (converted from UTC)
   - Columns: Date/Time, Video Title, Channel Name, Duration Watched (MM:SS), Completed (Yes/No), Manual Play (Yes/No), Grace Play (Yes/No)

10. Pagination for long history lists (50 entries per page)
    - API parameters: `limit=50` (default), `offset=0` (default)
    - Response includes: `{history: [...], total: number}` where `total` is total count for pagination UI
    - Implementation: Offset-based pagination (adequate for single-family dataset size)
    - Frontend: Previous/Next buttons, page number display

11. Norwegian UI text throughout interface
    - All labels, buttons, and messages in Norwegian (e.g., "Spill av igjen" for Play Again button)
    - Date/time formatting: Norwegian locale (DD.MM.YYYY HH:MM)
    - Error messages in Norwegian for user-facing errors
    - Code/logs remain in English per coding standards

12. Admin session authentication required
    - All endpoints protected by `require_auth()` middleware
    - Session cookie: HttpOnly, Secure, SameSite=Lax
    - 24-hour session expiry (in-memory storage, acceptable for single-family deployment)
    - Redirects to login page if session expired

13. UTC time handling with local display
    - **TIER 1 requirement:** All backend time operations use `datetime.now(timezone.utc)`
    - Database queries use `DATE('now')` for current date
    - Frontend converts UTC timestamps to browser local time for display
    - Date range filters accept local dates but query UTC timestamps correctly

**Dependencies:**
- Story 2.2 (Video Playback): Reuses `player.js` component and YouTube IFrame API integration
- Story 1.4 (Admin Authentication): Extends existing admin session management and `require_auth()` middleware
- Database schema from Story 1.1: Uses existing `watch_history` table structure

**Technical Implementation Notes:**

*Database Query Pattern:*
```sql
-- Combined filter query with proper parameter binding (TIER 1: SQL placeholders mandatory)
SELECT h.*,
       COALESCE(v.thumbnail_url,
                'https://i.ytimg.com/vi/' || h.video_id || '/default.jpg') as thumbnail_url
FROM watch_history h
LEFT JOIN videos v ON v.video_id = h.video_id
WHERE 1=1
  AND (? IS NULL OR DATE(h.watched_at) >= ?)
  AND (? IS NULL OR DATE(h.watched_at) <= ?)
  AND (? IS NULL OR h.channel_name = ?)
  AND (? IS NULL OR h.video_title LIKE '%' || ? || '%' COLLATE NOCASE)
ORDER BY h.watched_at DESC
LIMIT ? OFFSET ?
```

*Required Index Addition:*
```sql
CREATE INDEX idx_watch_history_channel ON watch_history(channel_name);
```

*Player Integration Pattern:*
- Admin modal uses same YouTube IFrame API configuration as child fullscreen player
- Modal context: overlay with close button (not full navigation)
- On close: return to history page at same scroll position
- ESC key handler: close modal without logging (existing pattern from Story 2.2)

*Performance Considerations:*
- Expected dataset: 100s to 1000s of rows (single family, months of usage)
- Offset pagination adequate (no cursor-based pagination needed)
- LIKE search acceptable for v1 (consider FTS5 if history exceeds 10,000+ entries)
- Indexes cover common query patterns (date + channel filters)

*CSV Export Implementation (Optional - Phase 4):*
- Same filter parameters as history endpoint for consistency
- UTF-8 with BOM encoding for Norwegian character support in Excel
- Streaming response for large datasets (unlikely but future-proof)
- File naming: `history_YYYY-MM-DD.csv` using export date

## Story 3.2: Configuration Settings Interface

As a parent,
I want to configure application settings via the admin interface,
so that I can customize behavior and limits.

**Architecture Context:**

This story implements the configuration settings interface for parent control, building on architectural decisions from the foundation phase:

*Database Design (docs/architecture/database-schema.md):*
- `settings` table uses key-value storage with JSON-encoded string values for consistency
- Schema: `key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL, created_at TEXT`
- Default settings initialized on database creation:
  - `daily_limit_minutes`: '30' (time-based limits, not video-count)
  - `grid_size`: '9' (number of video thumbnails)
  - `audio_enabled`: 'true' (lowercase string boolean)
  - `admin_password_hash`: '""' (bcrypt hash, empty until set)
- All values stored as JSON-encoded strings regardless of type
- `updated_at` timestamps in UTC ISO 8601 format

*API Endpoints (docs/architecture/api-specification.md):*
- `GET /admin/settings`
  - Returns: `{settings: {daily_limit_minutes: 30, grid_size: 9, audio_enabled: true}}`
  - Requires admin session authentication via `require_auth()`
  - Note: `admin_password_hash` never returned (security)
- `PUT /admin/settings` with partial update support
  - Request: `{daily_limit_minutes?: number, grid_size?: number, audio_enabled?: boolean}`
  - Response: `{success: true, settings: {...}, message: "Innstillinger lagret"}`
  - Validation via Pydantic models (see Input Validation below)
  - Only specified fields updated, others unchanged

*Database Queries (backend/db/queries.py):*
- `get_setting(key: str) -> str` - Returns JSON-encoded string value, raises KeyError if not found
- `set_setting(key: str, value: str) -> None` - Upsert behavior with `INSERT OR REPLACE`, caller must JSON-encode values
- Always use SQL placeholders (TIER 1 requirement)
- Context manager pattern: `with get_connection() as conn:`

*Input Validation (docs/architecture/security-implementation.md):*
```python
class UpdateSettingsRequest(BaseModel):
    daily_limit_minutes: int = Field(None, ge=5, le=180)  # 5 min to 3 hours
    grid_size: int = Field(None, ge=4, le=15)              # Minimum functional to reasonable max
    audio_enabled: bool = None                              # No range validation
```
- Pydantic enforces type safety and ranges at API boundary
- Partial updates supported (all fields optional)
- Generic error messages for invalid input (don't expose validation details)

*Frontend Integration:*
- Admin template: `frontend/templates/admin/settings.html`
- Admin module: `frontend/src/admin/settings.js`
- API client functions: `fetchSettings()`, `updateSettings(settings)`
- Norwegian UI text throughout (labels, buttons, success/error messages)
- Form validation client-side mirrors backend validation

*Technical Constraints:*
- All-synchronous operations (no async/await in backend)
- UTC time handling (TIER 1): Use `datetime.now(timezone.utc)` for `updated_at` timestamps
- SQL placeholders mandatory (TIER 1): Never use string formatting for queries
- Admin session required: All endpoints use `require_auth()` middleware
- Settings changes apply immediately (no service restart needed)

*Hardcoded UX Patterns (NOT configurable):*
- Warning thresholds: 10, 5, 2 minutes remaining (fixed)
- Wind-down start: 10 minutes remaining (fixed)
- Grace video max duration: 5 minutes (fixed)
- These patterns are intentionally not exposed as settings to maintain consistent UX

*Integration with Daily Limit System:*
- `daily_limit_minutes` setting is foundation for daily limit state machine
- State calculation: `minutesRemaining = daily_limit_minutes - minutesWatched`
- Wind-down mode activates when `minutesRemaining <= 10`
- Only counts videos where `manual_play=false AND grace_play=false`

**Acceptance Criteria:**
1. Settings page accessible from admin dashboard
   - Route: `/admin/settings`
   - Template: `frontend/templates/admin/settings.html`
   - Module: `frontend/src/admin/settings.js`
   - Requires admin session (redirects to login if expired)

2. Daily time limit setting (default: 30 minutes, range: 5-180 minutes)
   - Database key: `daily_limit_minutes`
   - Pydantic validation: `int = Field(None, ge=5, le=180)`
   - UI: Number input with min=5, max=180, step=5
   - Label: "Daglig grense (minutter)" with help text explaining time-based limits
   - Changes apply immediately to daily limit calculations

3. Grid size setting (default: 9 videos, range: 4-15)
   - Database key: `grid_size`
   - Pydantic validation: `int = Field(None, ge=4, le=15)`
   - UI: Number input or slider with min=4, max=15
   - Label: "Antall videoer i rutenettet"
   - Changes visible on next child interface load

4. Audio feedback enable/disable toggle (default: enabled)
   - Database key: `audio_enabled`
   - Pydantic validation: `bool = None`
   - UI: Toggle switch or checkbox
   - Label: "Lydvarsler aktivert"
   - Help text: Explains warning sounds at 10, 5, 2 minutes remaining
   - Changes apply immediately to warning system

5. Settings stored in database (settings table)
   - All values stored as JSON-encoded strings for consistency
   - Upsert behavior: `INSERT OR REPLACE` pattern
   - Timestamps updated on every change (`updated_at` in UTC)

6. Settings changes apply immediately without restart
   - Settings loaded fresh on each API call (no caching)
   - No service restart required
   - Acceptable for single-instance deployment

7. "Reset to Defaults" button available
   - API: `POST /admin/settings/reset`
   - Resets to: `daily_limit_minutes=30, grid_size=9, audio_enabled=true`
   - Confirmation dialog: "Tilbakestill alle innstillinger til standardverdier?"
   - Success message: "Innstillinger tilbakestilt"
   - Admin password NOT reset (security)

8. Settings validation at API boundary
   - Pydantic models enforce type safety and ranges
   - Invalid input returns 422 Unprocessable Entity with Norwegian error message
   - Generic error messages (don't expose internal validation details)
   - Example: "Ugyldig verdi for daglig grense" (Invalid value for daily limit)

9. Settings page includes help text explaining each option
   - Daily limit: Explains time-based system, wind-down mode, grace video
   - Grid size: Explains impact on child interface layout
   - Audio: Explains warning sounds and when they play
   - Norwegian text throughout
   - Tooltips or expandable help sections for detailed explanations

10. Norwegian UI text throughout interface
    - All labels, buttons, and messages in Norwegian
    - Success message: "Innstillinger lagret"
    - Reset confirmation: "Tilbakestill alle innstillinger til standardverdier?"
    - Error messages: Generic Norwegian phrases (e.g., "Noe gikk galt")
    - Code/logs remain in English per coding standards

11. Admin session authentication required
    - All endpoints protected by `require_auth()` middleware
    - Session cookie: HttpOnly, Secure, SameSite=Lax
    - 24-hour session expiry (in-memory storage, acceptable for single-family deployment)
    - Redirects to login page if session expired

12. Form state management
    - Display current values on page load via `GET /admin/settings`
    - Enable/disable submit button based on changes (dirty state tracking)
    - Loading states during API calls
    - Success/error message display
    - Form reset to current values on cancel

**Dependencies:**
- Story 1.4 (Admin Authentication): Extends existing admin session management and `require_auth()` middleware
- Database schema from Story 1.1: Uses existing `settings` table structure
- Story 2.1 (Daily Limits): Settings directly impact daily limit state machine calculations

**Technical Implementation Notes:**

*Database Query Pattern:*
```python
# Get setting (backend/db/queries.py)
def get_setting(key: str) -> str:
    with get_connection() as conn:
        result = conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,)
        ).fetchone()
        if result is None:
            raise KeyError(f"Setting not found: {key}")
        return result[0]  # JSON-encoded string

# Set setting with upsert
def set_setting(key: str, value: str) -> None:
    from datetime import datetime, timezone
    updated_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, updated_at)
        )
```

*JSON Encoding Pattern:*
```python
import json

# Simple values stored as strings (current implementation)
set_setting('daily_limit_minutes', '30')
set_setting('audio_enabled', 'true')  # Lowercase string

# Caller handles parsing
limit = int(get_setting('daily_limit_minutes'))
audio = get_setting('audio_enabled') == 'true'
```

*API Route Pattern:*
```python
@app.get("/admin/settings")
def get_settings(session_token: str = Depends(require_auth)):
    daily_limit = int(get_setting('daily_limit_minutes'))
    grid_size = int(get_setting('grid_size'))
    audio_enabled = get_setting('audio_enabled') == 'true'

    return {
        "settings": {
            "daily_limit_minutes": daily_limit,
            "grid_size": grid_size,
            "audio_enabled": audio_enabled
        }
    }
    # Note: admin_password_hash never returned

@app.put("/admin/settings")
def update_settings(
    request: UpdateSettingsRequest,
    session_token: str = Depends(require_auth)
):
    # Partial update: only update provided fields
    if request.daily_limit_minutes is not None:
        set_setting('daily_limit_minutes', str(request.daily_limit_minutes))
    if request.grid_size is not None:
        set_setting('grid_size', str(request.grid_size))
    if request.audio_enabled is not None:
        set_setting('audio_enabled', 'true' if request.audio_enabled else 'false')

    # Return updated settings
    return {
        "success": True,
        "settings": get_all_settings(),
        "message": "Innstillinger lagret"
    }
```

*Frontend API Client Usage:*
```javascript
// frontend/src/admin/settings.js
import { fetchSettings, updateSettings } from '../shared/api.js';

async function loadSettings() {
    const data = await fetchSettings();
    populateForm(data.settings);
}

async function saveSettings(formData) {
    const data = await updateSettings(formData);
    showMessage(data.message);  // "Innstillinger lagret"
}
```

*Integration with Daily Limit State Machine:*
When `daily_limit_minutes` changes, the state machine recalculates on next video selection:
```javascript
// Daily limit state recalculation
const dailyLimit = settings.daily_limit_minutes;
const minutesWatched = calculateMinutesWatched(date);  // Excludes manual_play/grace_play
const minutesRemaining = dailyLimit - minutesWatched;

// State transitions based on remaining time
if (minutesRemaining > 10) {
    currentState = 'normal';
} else if (minutesRemaining > 0) {
    currentState = 'winddown';  // Filter videos by duration
} else if (graceAvailable) {
    currentState = 'grace';  // Offer one video ≤5 minutes
} else {
    currentState = 'locked';  // Locked until midnight UTC
}
```

*Performance Considerations:*
- Settings loaded on each API call (no caching) - acceptable for low-frequency admin operations
- Single-instance deployment - no distributed cache coordination needed
- Settings table has 4-5 rows maximum - no indexing beyond PRIMARY KEY needed
- In-memory session storage - settings changes visible immediately without cache invalidation

*Validation Error Handling:*
```python
# Pydantic validation errors caught by FastAPI
# Return 422 with Norwegian message
from fastapi import HTTPException

try:
    validate_settings(request)
except ValidationError as e:
    raise HTTPException(
        status_code=422,
        detail="Ugyldig verdi for innstillinger"  # Generic Norwegian message
    )
```

## Story 3.X: Admin Help & Documentation

As a parent using the admin interface,
I want inline help and guidance,
so that I can effectively manage the application.

**Acceptance Criteria:**
1. Help text appears on each admin page explaining functionality
2. Getting Started guide created in Norwegian (docs/getting-started-no.md)
3. FAQ section added to admin interface with common questions
4. Tooltips on complex settings (hover to see explanation)
5. Link to full documentation from admin dashboard
6. Contact/support information displayed (if applicable)
7. Version number displayed in admin footer
8. Help text explains key concepts: channels, playlists, daily limits, etc.

---
