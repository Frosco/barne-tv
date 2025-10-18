# Epic 1: Foundation & Infrastructure

**Goal:** Establish complete development infrastructure, YouTube integration, and content management before proceeding to child interface.

**Deliverable:** Parent can add channels via admin interface; system is ready for child interface development with all foundational infrastructure in place.

## Story 1.1: Project Foundation and Basic Server Setup

As a developer,
I want to establish the project structure with a Python FastAPI backend and complete initialization,
so that I have a working foundation for adding features.

**Acceptance Criteria:**
1. Monorepo structure created with /backend, /frontend, and /static directories
2. FastAPI application runs locally with a health check endpoint
3. Basic Nginx configuration template created for reverse proxy
4. Static file serving configured for CSS, JavaScript, and images
5. Project README with setup instructions (see AC 12 for minimum content)
6. Git repository initialized with .gitignore for Python
7. Python dependencies managed with uv (pyproject.toml with FastAPI, uvicorn, google-api-python-client)
8. **Database schema initialized using backend/db/init_db.py**
9. **Admin password set via command-line argument during database initialization**
10. **.env.example file created with all required environment variables:**
    - DATABASE_PATH=/opt/youtube-viewer/data/app.db
    - YOUTUBE_API_KEY=your_api_key_here
    - ALLOWED_HOSTS=localhost,127.0.0.1
11. **Empty service modules created with basic structure:**
    - backend/services/__init__.py
    - backend/services/viewing_session.py (with docstring and imports)
    - backend/services/content_source.py (with docstring and imports)
12. **README.md created with minimum content:**
    - Project name and description
    - Prerequisites (Python 3.11.7, uv, Node.js 20.x)
    - Installation instructions
    - Environment variable setup
    - How to run locally
    - How to run tests

## Story 1.X: Testing Infrastructure Setup

As a developer,
I want a complete testing infrastructure with frameworks and structure,
so that I can write tests for all features.

**Acceptance Criteria:**
1. pytest installed (8.0.0) with pytest-mock (3.12.0) and pytest-cov (4.1.0)
2. Vitest installed (1.1.0) with happy-dom (12.10.3) for frontend tests
3. pytest.ini configured with test paths, markers (tier1, security, performance), and options
4. vitest.config.js configured with happy-dom environment and coverage settings
5. Complete tests/ directory structure created (backend/, frontend/, integration/, e2e/)
6. Backend conftest.py created with test database fixtures
7. Sample backend test created (test_health.py) verifying health endpoint
8. Sample frontend test created (sample.test.js) verifying test infrastructure
9. Coverage reporting configured (pytest-cov, vitest v8 provider)
10. README updated with test commands (pytest, npm test, coverage reports)

## Story 1.Y: Frontend Foundation & Build Setup

As a developer,
I want a complete frontend infrastructure with build pipeline,
so that I can develop the child and admin interfaces.

**Acceptance Criteria:**
1. Frontend directory structure created (src/, public/, templates/)
2. package.json created with all required dependencies (Vite, Vitest, ESLint, Prettier)
3. Vite configuration (vite.config.js) created with correct build settings
4. Entry point files created (src/child.js, src/admin.js)
5. Main CSS file created (src/main.css) with design system placeholders
6. Base HTML template created (templates/base.html) with proper meta tags
7. ESLint and Prettier configured for code quality
8. Vite dev server runs successfully with hot reload
9. Production build completes successfully (npm run build outputs to static/)
10. Frontend README created with development instructions

## Story 1.Z: Design System Implementation

As a developer,
I want a complete design system with reusable CSS components,
so that I can build consistent UI across the application.

**Acceptance Criteria:**
1. CSS custom properties implemented for all design tokens (colors, typography, spacing)
2. Typography classes created for all text scales (H1-H3, body, caption)
3. Spacing utility classes created using 8px base scale
4. Color palette implemented with semantic naming (primary, success, error, etc.)
5. Component base classes created (video-card, action-button, warning-overlay, etc.)
6. Responsive breakpoint system implemented with media queries
7. Focus indicator styles implemented for keyboard navigation
8. Screen reader utility class (.sr-only) created
9. Design system documented in frontend/README.md

## Story 1.2: YouTube API Setup

As a developer,
I want the YouTube Data API v3 properly configured and credentials secured,
so that the application can fetch video data.

**Acceptance Criteria:**
1. YouTube Data API v3 enabled in Google Cloud Console
2. API key generated with appropriate restrictions (HTTP referrer or IP restrictions)
3. API key stored in .env file (YOUTUBE_API_KEY)
4. API key never committed to version control (.env in .gitignore)
5. google-api-python-client dependency installed and verified
6. API quota monitoring setup (daily quota tracking in database)
7. Error handling for quota exceeded scenarios
8. Documentation created for API key setup process
9. API key validation function implemented (test with simple request)

## Story 1.3: YouTube API Integration for Video Fetching

As a parent,
I want the system to fetch complete video lists from YouTube channels and playlists,
so that all available content from approved sources is accessible.

**Acceptance Criteria:**
1. YouTube Data API v3 client configured with API key from environment
2. Function to fetch all videos from a channel (paginated)
3. Function to fetch all videos from a playlist
4. Extract video ID, title, thumbnail URL, duration, and publish date
5. Handle pagination for channels with many videos
6. Cache video metadata in SQLite database
7. Gracefully handle API quota limits with appropriate error messages
9. Track API quota usage and display in admin interface
10. Batch API calls efficiently to minimize quota consumption

## Story 1.4: Basic Admin Authentication

As a parent,
I want a simple password-protected login to access admin features,
so that children cannot access management functions.

**Acceptance Criteria:**
1. Admin login page created with password field
2. Password authentication using bcrypt (stored hash in database)
3. Session management with secure cookies (httpOnly, secure in production)
4. Login redirects to admin dashboard on success
5. Invalid password shows clear error message
6. Session timeout after 24 hours of inactivity
7. Logout functionality clears session
8. All admin routes protected (redirect to login if not authenticated)

## Story 1.5: Channel Management

As a parent,
I want to add and remove YouTube channels via the admin interface,
so that I control what content is available.

**Acceptance Criteria:**
1. Admin page displays list of all added channels with thumbnails
2. "Add Channel" form accepts YouTube channel URL or channel ID
3. System validates channel exists and fetches channel name/thumbnail
4. Channel stored in database with metadata (name, channel_id, thumbnail)
5. "Remove" button next to each channel with confirmation dialog
6. Removing channel also removes associated cached videos
7. Channel list updates in real-time after add/remove
8. Error handling for invalid URLs or non-existent channels
9. Support for both channel URLs and playlist URLs
10. Initial fetch of videos triggered immediately after adding channel

---
