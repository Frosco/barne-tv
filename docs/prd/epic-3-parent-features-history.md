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

**Acceptance Criteria:**
1. Settings page accessible from admin dashboard
2. Daily video limit setting (default: 5 videos, range: 1-20)
3. Audio feedback enable/disable toggle (default: enabled)
4. Mascot interactions enable/disable (default: enabled)
5. Smart selection algorithm enable/disable (default: enabled)
6. Settings stored in database (settings table)
7. Settings changes apply immediately without restart
8. "Reset to Defaults" button available
9. Settings validation (e.g., limit must be positive integer)
10. Settings page includes help text explaining each option

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
