# Coding Standards

**CRITICAL NOTICE FOR AI AGENTS:** These standards directly control code generation. They are MANDATORY and override general best practices where conflicts arise. Standards are organized by severity - Child Safety rules are absolutely critical and cannot be violated under any circumstances.

## Core Standards

**Languages & Runtimes:**
- Python 3.11.7 (backend) - Use type hints, dataclasses, and modern patterns
- JavaScript ES2020+ (frontend) - Use ES6 modules, const/let (never var), async/await
- No TypeScript (simplification decision - vanilla JS only)

**Style & Linting:**
- Backend: Black (line length 100), Ruff for linting
- Frontend: Prettier (default config), ESLint with recommended rules
- Run `uv run black .` and `uv run ruff check .` before commits
- Run `npm run lint` before production builds

**File Naming:**
- Backend: `snake_case.py` for all Python files
- Frontend: `kebab-case.js` for JS files
- Templates: `kebab-case.html` for Jinja2 templates
- Never use spaces in filenames

**Test Organization:**
- Test files mirror source structure: `backend/services/viewing_session.py` → `tests/backend/services/test_viewing_session.py`
- Test functions: `test_<function_name>_<scenario>()` format
- Fixtures in `conftest.py` at appropriate level

---

## TIER 1: Child Safety Rules (Cannot Violate)

**These rules directly protect child safety and time limits. Violations could allow unlimited viewing, inappropriate content, or unauthorized access.**

### 1. Video Selection Filtering

```python
# ✅ CORRECT - Always filter banned and unavailable videos
def get_videos_for_grid(count: int):
    query = """
        SELECT * FROM videos 
        WHERE is_available = 1 
        AND video_id NOT IN (SELECT video_id FROM banned_videos)
        ORDER BY RANDOM()
        LIMIT ?
    """
    with get_connection() as conn:
        return conn.execute(query, (count,)).fetchall()

# ❌ WRONG - Missing banned video filter
def get_videos_for_grid(count: int):
    query = "SELECT * FROM videos WHERE is_available = 1"
    # Bug: Child can see banned videos
```

**Why critical:** Core safety feature - forgetting this filter exposes child to banned content.

### 2. Time Limit Calculation

```python
# ✅ CORRECT - Exclude manual_play and grace_play from limits
def calculate_minutes_watched(date: str) -> int:
    query = """
        SELECT COALESCE(SUM(duration_watched_seconds), 0) / 60
        FROM watch_history
        WHERE DATE(watched_at) = ?
        AND manual_play = 0
        AND grace_play = 0
    """
    with get_connection() as conn:
        return conn.execute(query, (date,)).fetchone()[0]

# ❌ WRONG - Including all plays in limit
def calculate_minutes_watched(date: str) -> int:
    query = """
        SELECT SUM(duration_watched_seconds) / 60
        FROM watch_history
        WHERE DATE(watched_at) = ?
    """
    # Bug: Parent's "play again" counts toward child's limit
```

**Why critical:** Time limit is core feature - wrong calculation allows unlimited viewing.

### 3. UTC Time for All Date Operations

```python
# ✅ CORRECT - Always use UTC for time calculations
from datetime import datetime, timezone

current_time = datetime.now(timezone.utc)
today = current_time.date().isoformat()

# SQLite queries
query = "SELECT * FROM watch_history WHERE DATE(watched_at) = DATE('now')"

# ❌ WRONG - Naive datetime causes midnight reset bugs
current_time = datetime.now()  # Ambiguous timezone
today = current_time.date()    # Wrong at midnight transitions
```

**Why critical:** Time limit resets at midnight - timezone bugs allow bypassing daily limits.

### 4. Admin Password Security

```python
# ✅ CORRECT - Use bcrypt for password hashing
from passlib.hash import bcrypt

# Storing password
hashed = bcrypt.hash(password)
db.set_setting('admin_password_hash', hashed)

# Verifying password
stored_hash = db.get_setting('admin_password_hash')
is_valid = bcrypt.verify(password, stored_hash)

# ❌ WRONG - Weak hashing or plain text
import hashlib
hashed = hashlib.sha256(password.encode()).hexdigest()  # Too weak
# Or worse:
password_plain = password  # Never store plain text
```

**Why critical:** Admin access protects settings - weak password security allows child to bypass limits.

### 5. Input Validation for All Parent Inputs

```python
# ✅ CORRECT - Validate and sanitize all inputs
def add_source(source_input: str) -> dict:
    # Validate length
    if not source_input or len(source_input) > 200:
        raise ValidationError("Invalid input length")
    
    # Sanitize and parse YouTube URL
    parsed = parse_youtube_url(source_input.strip())
    if not parsed:
        raise ValidationError("Not a valid YouTube URL or ID")
    
    # Proceed with validated input
    source_id = parsed['id']
    source_type = parsed['type']

# ❌ WRONG - No validation
def add_source(source_input: str) -> dict:
    # Directly using user input - SQL injection risk
    source_id = source_input
```

**Why critical:** Prevents SQL injection, XSS, and malicious URLs from breaking the system.

### 6. SQL Parameters - Always Use Placeholders

```python
# ✅ CORRECT - Parameterized queries prevent SQL injection
video_id = user_input
conn.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,))

# ❌ WRONG - String formatting enables SQL injection
video_id = user_input
conn.execute(f"SELECT * FROM videos WHERE video_id = '{video_id}'")
# Attacker input: "'; DROP TABLE videos; --"
```

**Why critical:** SQL injection could delete all videos, corrupt database, or expose data.

---

## TIER 2: Functionality Rules (Prevents Major Bugs)

**These rules prevent bugs that would break core features but don't directly compromise child safety.**

### 7. Database Access - Always Use Context Manager

```python
# ✅ CORRECT - Always use context manager, even for reads
def get_videos_for_grid(count: int) -> list[dict]:
    with get_connection() as conn:
        return conn.execute("SELECT ...").fetchall()

# ❌ WRONG - Manual connection management
def get_videos_for_grid(count: int) -> list[dict]:
    conn = sqlite3.connect(DATABASE_PATH)
    result = conn.execute("SELECT ...").fetchall()
    conn.commit()  # Easy to forget
    conn.close()   # Easy to forget
    return result
```

**Rationale:** Consistency for AI agents, automatic rollback on errors, future-proof for adding writes.

### 8. YouTube API - Always Use Retry Helper

```python
# ✅ CORRECT - Use the retry wrapper for all API calls
response = fetch_videos_with_retry(youtube, channel_id, page_token)

# ❌ WRONG - Direct API calls skip error handling and retries
response = youtube.search().list(
    channelId=channel_id,
    part="id",
    maxResults=50
).execute()
```

**Rationale:** Handles transient errors, respects quota limits, provides consistent error messages.

### 9. Frontend API Calls - Always Handle Errors

```javascript
// ✅ CORRECT - Comprehensive error handling
async function loadVideos() {
    try {
        const response = await fetch('/api/videos');
        if (!response.ok) {
            showErrorMascot('Noe gikk galt');
            return;
        }
        const data = await response.json();
        renderGrid(data.videos);
    } catch (e) {
        console.error('Failed to load videos:', e);
        showErrorMascot('Noe gikk galt');
    }
}

// ❌ WRONG - Unhandled promise rejection crashes UI
async function loadVideos() {
    const response = await fetch('/api/videos');
    const data = await response.json();  // Crashes on network error
    renderGrid(data.videos);
}
```

**Rationale:** Network errors are common - unhandled errors break child experience.

### 10. Session Validation - Use Helper Function

```python
# ✅ CORRECT - Use the auth helper
@app.get("/admin/sources")
async def list_sources(request: Request):
    require_auth(request)  # Raises 401 if not authenticated
    sources = content_source.list_sources()
    return {"sources": sources}

# ❌ WRONG - Manual session checking
@app.get("/admin/sources")
async def list_sources(request: Request):
    if 'session_id' not in request.cookies:
        return {"error": "Unauthorized"}  # Wrong pattern
```

**Rationale:** Consistent authentication, proper HTTP status codes, centralized session logic.

### 11. Video Duration - Store as Integer Seconds

```python
# ✅ CORRECT - Integer seconds in database
duration_seconds = 245  # 4 minutes 5 seconds

# Parse from YouTube API ISO 8601 format
import isodate
duration_str = "PT4M5S"
duration_seconds = int(isodate.parse_duration(duration_str).total_seconds())

# ❌ WRONG - String durations in database
duration = "PT4M5S"  # Can't filter by duration in SQL
# Or:
duration = "4:05"  # Ambiguous format
```

**Rationale:** Wind-down mode filters videos by duration - needs integer for SQL comparisons.

### 12. API Response Format - Consistent Structure

```python
# ✅ CORRECT - Consistent response structure
return {
    "success": True,
    "videos": videos,
    "dailyLimit": daily_limit
}

# For errors:
return {
    "error": "VideoUnavailable",
    "message": "Video ikke tilgjengelig"
}

# ❌ WRONG - Bare data without structure
return videos  # Frontend doesn't know if this is error or success
```

**Rationale:** Frontend expects consistent format - inconsistency causes parsing errors.

---

## TIER 3: Code Quality Rules (Best Practices)

**These rules improve code quality and maintainability but don't directly impact functionality.**

### 13. All Backend Operations Are Synchronous

```python
# ✅ CORRECT - Synchronous functions, FastAPI handles threading
def get_videos_for_grid(count: int) -> list[dict]:
    with get_connection() as conn:
        return conn.execute("SELECT ...").fetchall()

# ❌ WRONG - No async/await in this project
async def get_videos_for_grid(count: int) -> list[dict]:
    # We're all-sync by design
```

**Rationale:** Simplification for single-user deployment, FastAPI runs sync code in thread pool.

### 14. Norwegian User-Facing Messages

```python
# ✅ CORRECT - Norwegian for all user messages
raise NoVideosAvailableError("Ingen videoer tilgjengelig")
return {"message": "Kanal lagt til: Blippi (487 videoer)"}

# ❌ WRONG - English user messages
raise NoVideosAvailableError("No videos available")

# NOTE: Logs, comments, and code remain in English
logger.error("Failed to fetch channel videos")  # OK in English
```

**Rationale:** Norwegian family, child interface must be Norwegian, technical logs can be English.

### 15. No localStorage/sessionStorage in Frontend

```javascript
// ✅ CORRECT - Use in-memory state
let currentVideos = [];
let dailyLimit = null;

// ❌ WRONG - Browser storage not supported
localStorage.setItem('videos', JSON.stringify(videos));
sessionStorage.setItem('limit', JSON.stringify(limit));
```

**Rationale:** Browser storage APIs not available in all deployment contexts.

### 16. Environment Variables via Config Module

```python
# ✅ CORRECT - Access through config module
from backend.config import DATABASE_PATH, YOUTUBE_API_KEY

def initialize():
    conn = sqlite3.connect(DATABASE_PATH)

# ❌ WRONG - Direct environment access scattered everywhere
import os
db_path = os.getenv('DATABASE_PATH')
```

**Rationale:** Centralized configuration, easier to mock in tests, clear dependencies.

---

## Frontend-Specific Standards

### File Organization

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
│   ├── child/         # Child-specific modules
│   ├── admin/         # Admin-specific modules
│   └── shared/        # Shared utilities
└── css/               # Stylesheets
```

### CSS Standards

```css
/* ✅ CORRECT - BEM-like naming */
.video-card { }
.video-card__thumbnail { }
.video-card__title { }
.video-card--loading { }

/* ✅ CORRECT - CSS Custom Properties for theming */
:root {
  --color-primary: #FFDB4D;
  --color-text: #2D3436;
  --space-md: 16px;
  --shadow-md: 0 4px 6px rgba(0,0,0,0.15);
}

.video-card {
  color: var(--color-text);
  padding: var(--space-md);
  box-shadow: var(--shadow-md);
}

/* ❌ WRONG - Inline styles */
<div style="color: #2D3436; padding: 16px;">

/* ❌ WRONG - Deep nesting */
.grid .row .col .card .header .title { }  /* Too specific */
```

### Jinja2 Template Patterns

```jinja2
{# ✅ CORRECT - Template inheritance #}
{% extends "base.html" %}

{% block content %}
  <div class="video-grid">
    {% for video in videos %}
    ```markdown
      {% include "components/video-card.html" %}
    {% endfor %}
  </div>
{% endblock %}

{# ✅ CORRECT - Data attributes for JS hooks #}
<div class="video-card" 
     data-video-id="{{ video.video_id }}"
     data-duration="{{ video.duration_seconds }}">
  <img src="{{ video.thumbnail_url }}" alt="">
  <h3>{{ video.title }}</h3>
</div>

{# ❌ WRONG - IDs for JS hooks #}
<div id="video-{{ video.video_id }}">
  {# Not unique if card appears multiple times #}
</div>
```

### JavaScript Module Pattern

```javascript
// ✅ CORRECT - Module with public interface
// frontend/src/child/grid.js

export function renderGrid(videos) {
  const container = document.querySelector('[data-grid]');
  container.innerHTML = '';
  videos.forEach(video => {
    const card = createCard(video);
    container.appendChild(card);
  });
  attachCardListeners();
}

// Private helpers - not exported
function createCard(video) {
  const card = document.createElement('div');
  card.className = 'video-card';
  card.dataset.videoId = video.videoId;
  
  const img = document.createElement('img');
  img.src = video.thumbnailUrl;
  img.alt = '';
  
  const title = document.createElement('h3');
  title.textContent = video.title;
  
  card.appendChild(img);
  card.appendChild(title);
  
  return card;
}

function attachCardListeners() {
  document.querySelectorAll('.video-card').forEach(card => {
    card.addEventListener('click', handleCardClick);
  });
}

// ❌ WRONG - Everything in global scope
function renderGrid(videos) { }
function createCard(video) { }  // Pollutes global scope
```

### State Management Pattern

```javascript
// ✅ CORRECT - Centralized state
// frontend/src/shared/state.js

let appState = {
  currentVideos: [],
  dailyLimit: null,
  isLoading: false
};

export function updateState(updates) {
  appState = { ...appState, ...updates };
  notifyListeners();
}

export function getState() {
  return { ...appState };  // Return copy for immutability
}

// ❌ WRONG - Global variables scattered
window.currentVideos = [];  // In grid.js
window.dailyLimit = null;   // In limit-tracker.js
// Leads to confusion about single source of truth
```

### Asset References

```javascript
// ✅ CORRECT - Relative paths, Vite handles bundling
const mascot = new Image();
mascot.src = '/images/mascot/happy.svg';

const chime = new Audio('/sounds/gentle-chime.mp3');

// In HTML templates:
<img src="/images/mascot/wave.svg" alt="Mascot">

// ❌ WRONG - Absolute URLs or hardcoded paths
mascot.src = 'https://youtube-viewer.com/static/mascot.svg';
mascot.src = 'file:///opt/youtube-viewer/static/mascot.svg';
```

### ESLint Configuration

```json
// .eslintrc.json
{
  "env": {
    "browser": true,
    "es2021": true
  },
  "extends": "eslint:recommended",
  "parserOptions": {
    "ecmaVersion": 2021,
    "sourceType": "module"
  },
  "rules": {
    "no-unused-vars": "error",
    "no-undef": "error",
    "require-await": "error",
    "no-shadow": "warn",
    "no-console": "off"
  }
}
```

```json
// package.json scripts
{
  "scripts": {
    "dev": "vite",
    "build": "vite build && npm run lint",
    "lint": "eslint frontend/src/**/*.js",
    "lint:fix": "eslint frontend/src/**/*.js --fix"
  }
}
```

---

## Python Type Hints

```python
# ✅ CORRECT - Use type hints for public functions
def get_videos_for_grid(
    count: int,
    max_duration: int | None = None
) -> list[dict]:
    """Fetch videos for the child's grid."""
    with get_connection() as conn:
        # ... implementation
        return videos

# ✅ CORRECT - Use dataclasses for structured data
from dataclasses import dataclass

@dataclass
class DailyLimit:
    date: str
    minutes_watched: int
    minutes_remaining: int
    current_state: str

# ❌ WRONG - No type hints makes intent unclear
def get_videos_for_grid(count, max_duration=None):
    # AI agents must guess parameter types
```

---

## Vite Configuration

```javascript
// vite.config.js
export default {
  root: 'frontend',
  build: {
    outDir: '../static',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        child: 'frontend/src/child.js',
        admin: 'frontend/src/admin.js'
      }
    }
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
}
```

---

## Key Takeaways for AI Agents

**TIER 1 - NEVER VIOLATE (Child Safety):**
- ✅ Always filter banned videos from child selection
- ✅ Exclude manual_play and grace_play from time limits
- ✅ Use UTC for all time calculations
- ✅ Hash passwords with bcrypt only
- ✅ Validate all parent inputs before processing
- ✅ Use SQL placeholders, never string formatting

**TIER 2 - IMPORTANT (Functionality):**
- ✅ Always use database context manager
- ✅ Always use YouTube API retry helper
- ✅ Always handle frontend fetch errors
- ✅ Use session validation helper for admin routes
- ✅ Store video durations as integer seconds
- ✅ Use consistent API response format

**TIER 3 - GOOD PRACTICE (Quality):**
- ✅ All backend operations synchronous
- ✅ Norwegian messages for users, English for logs
- ✅ No browser localStorage/sessionStorage
- ✅ Access environment via config module
- ✅ Use type hints for clarity
- ✅ Follow frontend module patterns

**When in Doubt:**
- Check if the rule is Tier 1 (safety-critical) - if yes, follow exactly
- Look for similar patterns in existing code
- Err on the side of safety and simplicity
- Use type hints to document intent

---

