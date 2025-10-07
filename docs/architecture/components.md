# Components

Based on the architectural patterns, tech stack, and data models defined above, the application is organized into clear logical components. The backend uses a **simplified two-layer architecture** with direct database access, avoiding unnecessary abstraction while maintaining organized business logic.

```
Routes → Services → Database (direct SQL)
```

## Backend Component Architecture

### Simplified Service Layer

**Services:**
```
backend/services/
├── __init__.py
├── viewing_session.py    # Video selection + daily limits
├── content_source.py     # YouTube fetching + source management
└── auth.py              # Module with session functions
```

**Database Access:**
```
backend/db/
├── __init__.py
├── queries.py           # Direct SQL functions (synchronous)
├── init_db.py          # Database initialization
├── maintenance.py      # Cleanup operations
└── schema.sql          # DDL
```

**Routes:**
```
backend/
└── routes.py            # Single file with all routes
```

---

## Component: Routes (Single File)

**Responsibility:** HTTP request handling, input validation, response formatting

**Location:** `backend/routes.py`

**Organization:** Section-based comments separate child, admin, and static endpoints

All routes are synchronous and run in FastAPI's thread pool.

---

## Component: Viewing Session Service

**Responsibility:** Video selection and daily limit management

**Location:** `backend/services/viewing_session.py`

**Key Functions:**
- `get_videos_for_grid(count)` - Get videos with filtering based on state
- `log_watch_and_update(video_id, duration, completed)` - Log watch and recalculate limit
- `get_daily_limit()` - Calculate current limit state
- `should_interrupt_video(minutes_remaining, duration)` - Determine if video should be interrupted

**Key Design:** All database operations are synchronous. Runs in FastAPI thread pool.

---

## Component: Content Source Service

**Responsibility:** YouTube API integration and source management

**Location:** `backend/services/content_source.py`

**Key Functions:**
- `add_source(input)` - Add channel/playlist, fetch all videos
- `refresh_source(source_id)` - Re-fetch videos from source
- `refresh_all_sources()` - Re-fetch videos from all sources (weekly timer)
- `remove_source(source_id)` - Delete source and cascade videos
- `_fetch_channel_videos(channel_id)` - Paginate through all channel videos
- `_fetch_playlist_videos(playlist_id)` - Paginate through playlist videos
- `_fetch_video_details(video_ids)` - Get duration and metadata
- `_deduplicate_videos(videos)` - Remove duplicate video IDs
- `_parse_input(input)` - Parse various YouTube URL formats
- `fetch_videos_with_retry(youtube, channel_id, page_token, max_retries=3)` - Retry individual page fetches
- `fetch_all_channel_videos(youtube, channel_id)` - Returns tuple (videos, fetch_complete)

**Key Design:** All operations synchronous, runs in thread pool. Page-level retries with exponential backoff (0s, 1s, 2s). Returns partial fetch flag when network errors occur.

---

## Component: Authentication Module

**Responsibility:** Session management

**Location:** `backend/auth.py`

**Key Functions:**
- `create_session()` - Generate session ID, store in memory
- `validate_session(session_id)` - Check if valid and not expired
- `verify_password(password)` - Check against bcrypt hash
- `require_auth()` - FastAPI dependency for protected routes

**Key Design:** Simple module-level functions, in-memory session storage (single instance acceptable).

**Session Persistence Trade-off:** Sessions are stored in memory and will be lost on service restart. This is acceptable because:
- Only admin uses sessions (parent can re-login quickly)
- Service restarts are infrequent (deployments, crashes)
- No child data is lost (only adult convenience)
- Keeps architecture simple (no Redis/external session store needed)

---

## Component: Database Access Layer

**Responsibility:** Direct synchronous SQL operations

**Location:** `backend/db/queries.py`

**Key Functions:**
- Video queries: `get_available_videos()`, `get_video_by_video_id()`, `bulk_insert_videos()`, `update_video_availability()`
- Watch history: `insert_watch_history()`, `get_watch_history_for_date()`, `delete_watch_history_for_date()`
- Settings: `get_setting()`, `set_setting()`
- Sources: `get_all_content_sources()`, `get_source_by_id()`, `insert_content_source()`, `delete_content_source()`
- Banned videos: `insert_banned_video()`, `delete_banned_video()`
- API log: `log_api_call()`

**Key Design:** Context manager handles transactions automatically. Clear function names, direct SQL.

---

## Frontend Component Architecture

**Philosophy:** Simple, reusable patterns without framework overhead. Components are organized as **JS modules** with associated HTML templates and CSS classes.

**Directory Structure:**
```
frontend/
├── templates/          # Jinja2 server-rendered templates
│   ├── child/         # Child interface screens
│   └── admin/         # Admin interface screens
├── src/               # Vite entry points
│   ├── child.js
│   ├── admin.js
│   └── main.css
├── public/            # Static assets served as-is
│   ├── images/
│   └── sounds/
├── js/                # Application code
│   ├── child/         # Child interface logic
│   ├── admin/         # Admin interface logic
│   └── shared/        # Shared utilities
└── css/               # Stylesheets
```

**Component Organization Principles:**
1. **Server-side first:** HTML structure from Jinja2 templates
2. **Progressive enhancement:** JavaScript adds interactivity
3. **ES6 modules:** `type="module"` for clean imports
4. **CSS custom properties:** Theming and state transitions
5. **No global state:** Pass state explicitly

**Key Frontend Components:**
- **VideoGrid** (`grid.js`) - Render and manage thumbnail grid
- **VideoPlayer** (`player.js`) - YouTube IFrame API integration
- **LimitTracker** (`limit-tracker.js`) - Monitor time remaining
- **ChannelManagement** (`channels.js`) - Add/remove sources
- **API Client** (`api.js`) - Centralized API communication

---

