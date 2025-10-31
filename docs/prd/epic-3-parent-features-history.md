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

**Architecture Context:**

This story implements help and documentation features for the admin interface, building on architectural decisions from the foundation phase:

*Accessibility Requirements (docs/architecture/accessibility-implementation.md):*
- WCAG 2.1 Level AA compliance mandatory for all admin interfaces
- Help text patterns use `aria-describedby` for associating labels with explanatory text
- Tooltips must be keyboard accessible (not hover-only)
- Interactive help elements (FAQ accordions) use proper ARIA roles: `role="button"`, `aria-expanded`, `aria-controls`
- Screen reader support: help text announced when field receives focus
- Keyboard navigation: Tab to help icons, Enter/Space to activate tooltips
- Color contrast: Help text minimum 4.5:1 ratio, icons 3:1 ratio against background
- Focus indicators: Visible outline on all interactive help elements

*Frontend Structure (docs/architecture/source-tree.md):*
- Admin templates: `frontend/templates/admin/` (dashboard.html, channels.html, history.html, settings.html)
- Admin modules: `frontend/src/admin/` (dashboard.js, channels.js, history.js, settings.js)
- Shared components: `frontend/src/shared/` (help.js for tooltip/help text components)
- Static documentation: `docs/getting-started-no.md` (Markdown format, Norwegian language)
- Tests collocated: `frontend/src/shared/help.test.js` for help component tests

*API Patterns (docs/architecture/api-specification.md):*
- Version display: No dedicated endpoint needed, version read from `package.json` at build time and injected into base template
- All admin pages use `require_auth()` middleware for session authentication
- Norwegian error messages throughout (e.g., "Kunne ikke laste hjelp")

*Component Organization (docs/architecture/components.md):*
- Progressive enhancement: Help text present in HTML, JavaScript adds interactivity (tooltips, accordions)
- Reusable help component in `frontend/src/shared/help.js` provides tooltip and expandable help patterns
- No global state: Help component state managed per-instance

*Norwegian UI Requirements (docs/architecture/coding-standards.md):*
- All help text, labels, and documentation in Norwegian
- Code and logs remain in English
- FAQ questions and answers in Norwegian
- Getting Started guide entirely in Norwegian

**Acceptance Criteria:**

1. **Help text appears on each admin page explaining functionality**
   - **Channels page** (`frontend/templates/admin/channels.html`):
     - Help text above channel input: "Lim inn YouTube-kanal URL eller kanal-ID"
     - Explain channel vs playlist: "Kanaler inneholder alle videoer fra en YouTube-konto. Spillelister er kuraterte samlinger."
     - Help for "Oppdater" button: "Henter nye videoer fra denne kanalen"
   - **History page** (`frontend/templates/admin/history.html`):
     - Explain filters: "Filtrer historikk etter dato, kanal eller søk etter tittel"
     - Explain "Spill av igjen": "Spiller av video uten å telle mot barnets daglige grense"
   - **Settings page** (`frontend/templates/admin/settings.html`):
     - Daily limit help: "Hvor mange minutter barnet kan se videoer hver dag. Videoen går over i 'avslutningsmodus' ved 10 minutter igjen."
     - Grid size help: "Antall videoer som vises på skjermen samtidig (4-15)"
     - Audio help: "Lydvarsler spilles av ved 10, 5, og 2 minutter igjen"
   - **Dashboard page** (`frontend/templates/admin/dashboard.html`):
     - Statistics explanation: "Oversikt over dagens aktivitet og totale innhold"
   - Implementation: Help text uses `<span class="help-text">` with `id` attributes, associated via `aria-describedby` on inputs
   - Styling: Smaller font, muted color, icon prefix (ℹ️ or question mark icon)

2. **Getting Started guide created in Norwegian**
   - Location: `docs/getting-started-no.md` (Markdown format)
   - Sections:
     - **Velkommen** - Brief introduction to application purpose
     - **Første oppsett** - Initial setup steps (login, add first channel)
     - **Legge til kanaler** - How to find and add YouTube channels/playlists
     - **Administrere innstillinger** - Explain daily limit, grid size, audio settings
     - **Se historikk** - How to view watch history and replay videos
     - **Nøkkelkonsepter** - Explain channels, playlists, daily limits, wind-down mode, grace video
     - **Vanlige spørsmål** - Quick FAQ (3-5 common questions)
   - Tone: Friendly, clear, non-technical
   - Length: ~500-800 words
   - Format: Markdown with headings, lists, and emphasis
   - Accessibility: Proper heading hierarchy (h1, h2, h3), descriptive link text
   - Not served via web interface in v1 (parent reads locally or prints)

3. **FAQ section added to admin interface**
   - Location: `frontend/templates/admin/dashboard.html` (expandable section at bottom)
   - Component: `frontend/src/shared/help.js` provides `createFAQ()` function
   - Structure: Collapsible accordion with questions
   - Questions included (Norwegian):
     - "Hvordan legger jeg til en ny YouTube-kanal?" - Step-by-step with screenshot reference
     - "Hva er forskjellen på kanaler og spillelister?" - Clear explanation
     - "Hvordan fungerer den daglige grensen?" - Explain time-based limit, wind-down, grace video
     - "Kan barnet se videoer etter at grensen er nådd?" - Explain grace video (one video ≤5 min)
     - "Hva betyr 'avslutningsmodus'?" - Explain wind-down mode filtering
     - "Hvordan kan jeg spille av en spesifikk video for barnet?" - Explain "Spill av igjen" feature
     - "Telles foreldre-avspilling mot barnets grense?" - Explain `manual_play=true` exclusion
   - Accessibility:
     - Each question is `<button role="button" aria-expanded="false" aria-controls="faq-answer-1">`
     - Answers wrapped in `<div id="faq-answer-1" hidden>`
     - Keyboard: Tab to question, Enter/Space to expand/collapse
     - Screen reader: Announces expanded/collapsed state
   - Styling: Clear visual distinction (background color change when expanded)

4. **Tooltips on complex settings (keyboard accessible)**
   - Implementation: `frontend/src/shared/help.js` provides `createTooltip()` function
   - Trigger: Info icon (ℹ️) next to setting label
   - Activation: Click icon OR focus icon + Enter/Space (not hover-only)
   - Content: Short explanation in Norwegian (2-3 sentences max)
   - Tooltips added to:
     - Daily limit setting: "Grensen tilbakestilles hver natt kl. 00:00 UTC. Videoer som går over grensen avbrytes eller får fullføre basert på lengde."
     - Grid size setting: "Færre videoer gir større bilder. Flere videoer gir mer variasjon men mindre bilder."
     - Audio setting: "Lydvarsler er enkle 'pling'-lyder, ikke forstyrrende alarmer."
   - Accessibility:
     - Tooltip content has `role="tooltip"` and `id="tooltip-daily-limit"`
     - Trigger button has `aria-describedby="tooltip-daily-limit"`
     - ESC key closes tooltip
     - Focus returns to trigger button after close
     - Color contrast: 4.5:1 minimum for tooltip text
   - Positioning: Above or below trigger (avoid obscuring content)
   - Styling: Light background, subtle shadow, arrow pointing to trigger

5. **Link to full documentation from admin dashboard**
   - Location: `frontend/templates/admin/dashboard.html` in header or sidebar
   - Link text: "📖 Kom i gang" (accessible text, not just icon)
   - Target: Opens `docs/getting-started-no.md` in new window (if served) OR displays instructions to read local file
   - Alternative for v1: Display message: "Se docs/getting-started-no.md for full veiledning"
   - Accessibility:
     - Clear link text (not "click here")
     - `target="_blank"` with `rel="noopener noreferrer"` if external
     - Screen reader hint if opens in new window: `aria-label="Åpne dokumentasjon i nytt vindu"`
   - Styling: Prominent but not distracting (secondary button style)

6. **Contact/support information** (CLARIFICATION: NOT APPLICABLE for v1)
   - Self-hosted family application - no support channel needed
   - Parent is the administrator - no external support contact
   - Future consideration: If project open-sourced, add GitHub Issues link
   - For v1: Omit this feature entirely

7. **Version number displayed in admin footer**
   - Location: `frontend/templates/base.html` footer (inherited by all admin pages)
   - Source: Read from `package.json` version field at build time
   - Implementation: Vite injects version via `import.meta.env.VITE_APP_VERSION`
   - Display format: "Versjon 1.2.3" (Norwegian label)
   - Styling: Small, muted text in footer (non-intrusive)
   - Accessibility: Semantic footer tag, version text readable by screen readers
   - No link or interaction (static display only)
   - Future enhancement: Link to changelog/release notes

8. **Help text explains key concepts**
   - **Kanaler** (Channels): "En YouTube-kanal inneholder alle videoer publisert av en bestemt YouTube-konto. Når du legger til en kanal, hentes alle dens videoer."
   - **Spillelister** (Playlists): "En spilleliste er en kuratert samling videoer. Dette kan være laget av kanaleieren eller andre brukere."
   - **Daglig grense** (Daily Limit): "Tidsbegrensning for hvor lenge barnet kan se videoer hver dag. Grensen tilbakestilles ved midnatt (UTC). Videoer i 'avslutningsmodus' og 'takkvideo' telles ikke mot neste dag."
   - **Avslutningsmodus** (Wind-down Mode): "Når det er mindre enn 10 minutter igjen, filtreres rutenettet til å bare vise korte videoer som passer i gjenstående tid. Dette hjelper barnet med å avslutte naturlig."
   - **Takkvideo** (Grace Video): "Etter at grensen er nådd, får barnet velge én siste video (maks 5 minutter). Denne telles ikke mot dagens eller morgendagens grense."
   - **Manuell avspilling** (Manual Play): "Når du som forelder spiller av en video fra historikken, telles den ikke mot barnets daglige grense."
   - Location: Integrated into help text on relevant pages (Settings for limits, Dashboard for overview)
   - Format: Short definitions (1-2 sentences each) in Norwegian
   - Accessibility: Each concept defined when first encountered, with consistent terminology throughout interface

**Dependencies:**
- Story 3.1 (Watch History): Help text explains manual replay feature
- Story 3.2 (Settings): Help text explains each setting in detail
- Story 1.4 (Admin Authentication): All admin pages require authentication
- Accessibility Implementation (docs/architecture/accessibility-implementation.md): WCAG 2.1 AA compliance patterns

**Technical Implementation Notes:**

*Tooltip Component Pattern (frontend/src/shared/help.js):*
```javascript
/**
 * Create keyboard-accessible tooltip
 * @param {string} triggerText - Text/icon for trigger button
 * @param {string} tooltipContent - Help text content
 * @param {string} tooltipId - Unique ID for tooltip element
 * @returns {HTMLElement} - Trigger button with tooltip
 */
export function createTooltip(triggerText, tooltipContent, tooltipId) {
  const container = document.createElement('span');
  container.className = 'tooltip-container';

  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'tooltip-trigger';
  trigger.textContent = triggerText;
  trigger.setAttribute('aria-describedby', tooltipId);

  const tooltip = document.createElement('div');
  tooltip.id = tooltipId;
  tooltip.role = 'tooltip';
  tooltip.className = 'tooltip-content';
  tooltip.textContent = tooltipContent;
  tooltip.hidden = true;

  trigger.addEventListener('click', () => {
    tooltip.hidden = !tooltip.hidden;
    trigger.setAttribute('aria-expanded', !tooltip.hidden);
  });

  // Close on ESC key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !tooltip.hidden) {
      tooltip.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
      trigger.focus();
    }
  });

  container.appendChild(trigger);
  container.appendChild(tooltip);
  return container;
}
```

*FAQ Accordion Pattern:*
```html
<section class="faq-section" aria-labelledby="faq-heading">
  <h2 id="faq-heading">Vanlige spørsmål</h2>

  <div class="faq-item">
    <button
      class="faq-question"
      aria-expanded="false"
      aria-controls="faq-answer-1"
    >
      Hvordan legger jeg til en ny YouTube-kanal?
    </button>
    <div id="faq-answer-1" class="faq-answer" hidden>
      <p>Gå til "Kanaler"-fanen, lim inn kanal URL, og klikk "Legg til"...</p>
    </div>
  </div>

  <!-- More FAQ items... -->
</section>
```

*Help Text Styling (CSS):*
```css
.help-text {
  display: block;
  font-size: 0.875rem;
  color: var(--color-text-secondary); /* 5.8:1 contrast ratio */
  margin-top: 0.25rem;
}

.help-text::before {
  content: 'ℹ️ ';
  margin-right: 0.25rem;
}

.tooltip-trigger {
  background: transparent;
  border: none;
  cursor: help;
  padding: 0.25rem;
  font-size: 1rem;
}

.tooltip-trigger:focus {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.tooltip-content {
  position: absolute;
  background: var(--color-white);
  border: 1px solid var(--color-border);
  padding: 0.75rem;
  max-width: 300px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 1000;
}
```

*Version Injection Pattern (vite.config.js):*
```javascript
import { defineConfig } from 'vite';
import { readFileSync } from 'fs';

const packageJson = JSON.parse(readFileSync('./package.json', 'utf-8'));

export default defineConfig({
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(packageJson.version)
  },
  // ... other config
});
```

*Getting Started Guide Structure:*
```markdown
# Kom i gang med Safe YouTube Viewer for Kids

## Velkommen
Denne applikasjonen lar barnet ditt se YouTube-videoer fra godkjente kanaler...

## Første oppsett
1. Logg inn med admin-passordet
2. Klikk på "Kanaler"-fanen
3. Lim inn URL til første YouTube-kanal...

## Legge til kanaler
For å finne en YouTube-kanal URL:
- Gå til kanalen på YouTube
- Kopier URL fra adressefeltet...

## [Continue with other sections]
```

*Performance Considerations:*
- Help text static (no API calls)
- Tooltips lazy-loaded (created on first interaction)
- FAQ accordion: Show/hide with CSS `hidden` attribute (no DOM manipulation)
- Version number cached at build time (no runtime lookups)

*Accessibility Testing Checklist:*
- [ ] All help text readable by screen readers
- [ ] Tooltips keyboard accessible (Tab, Enter, ESC)
- [ ] FAQ accordion keyboard navigable
- [ ] Color contrast meets WCAG AA (4.5:1 for text)
- [ ] Focus indicators visible on all interactive elements
- [ ] No keyboard traps in tooltip/FAQ interactions
- [ ] ARIA attributes correctly implemented (`aria-expanded`, `aria-controls`, `aria-describedby`)
- [ ] Heading hierarchy logical (h1 → h2 → h3)

---
