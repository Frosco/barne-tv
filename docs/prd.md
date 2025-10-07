# Safe YouTube Viewer for Kids Product Requirements Document (PRD)

## Goals and Background Context

### Goals

- Eliminate 100% of inappropriate content exposure by restricting videos exclusively to parent-approved YouTube channels and playlists
- Enable independent video selection for children ages 2-6 through a visual, child-friendly interface requiring no reading ability
- Reduce parental supervision from constant oversight to one-time setup through automated content curation
- Establish healthy screen time boundaries with automatic daily viewing limits (5 videos)
- Maintain engaging content freshness with 20-40% rewatch rate within 7-day periods (balancing novelty with comfort of familiar favorites)
- Create a frustration-free experience for both children and parents by removing content negotiation conflicts
- Enable simple content source management pi direct URL pasting or name entry for both channels and playlists

### Background Context

Parents struggle with YouTube's recommendation-driven model that optimizes for engagement over child safety, leading to inappropriate content discovery even within YouTube Kids. Current parental controls are either too complex or ineffective, requiring constant supervision and creating frequent conflicts when parents must deny video choices. This solution addresses the gap by providing complete parental control over content sources while maintaining the engaging visual selection experience children expect. By limiting content to pre-approved channels and playlists only and removing all discovery mechanisms, the application transforms YouTube from an open-ended platform into a curated, safe viewing environment that respects both child development needs and parental peace of mind. The interface uses Norwegian for all UI elements while allowing video content in any language.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2024-01-XX | 1.0 | Initial PRD Creation | PM |

## Requirements

### Functional

- **FR1:** The system shall display a configurable grid (4-15 thumbnails) with videos selected using gentle weighted randomization based on past engagement, favoring variety while allowing familiar content
- **FR2:** The system shall provide a password-protected parent interface for managing approved content sources
- **FR3:** The parent interface shall accept YouTube channel URLs, playlist URLs, or channel names to add new content sources
- **FR4:** The system shall play selected videos in fullscreen mode with spacebar (pause/play) and escape (exit fullscreen) keyboard controls
- **FR5:** The system shall automatically return to the video selection grid after each video ends without showing YouTube's end screen or recommendations
- **FR6:** The system shall track watch history and use it to gently deprioritize (not hide) recently watched videos in the selection algorithm
- **FR7:** The system shall display video titles below thumbnails and show channel names during playback
- **FR8:** The system shall enforce time-based daily viewing limits (default 30 minutes) with audio/visual warning at 5 minutes remaining
- **FR9:** The system shall offer a "one more video" grace option when daily limit is reached, limited to videos under 5 minutes
- **FR10:** The system shall implement a "winding down" mode in the last 10 minutes, filtering to show only videos that fit within remaining time using actual duration data
- **FR11:** The system shall display a child-friendly goodbye message after the grace video or when limit is fully reached
- **FR12:** The system shall prevent access to YouTube comments, live chat, and recommendation sections
- **FR13:** All user interface text shall be displayed in Norwegian while preserving original video titles
- **FR14:** The parent interface shall provide ability to remove channels/playlists and adjust grid size per child
- **FR15:** The system shall refresh available videos from approved sources weekly to include new content
- **FR16:** The parent interface shall allow configuration of daily time limit and grid size

### Non-Functional

- **NFR1:** Video playback shall begin within 3 seconds of thumbnail selection on standard broadband connection
- **NFR2:** The thumbnail grid shall render within 1 second of page load
- **NFR3:** The system shall operate within YouTube API daily quota limits for a single household
- **NFR4:** The parent password shall be stored securely using industry-standard hashing
- **NFR5:** The application shall be accessible only via direct URL and not indexed by search engines
- **NFR6:** The system shall function on modern browsers (Chrome, Firefox, Safari, Edge) released within the last 2 years
- **NFR7:** The interface shall be responsive and usable on both desktop and tablet devices
- **NFR8:** The system shall gracefully handle unavailable videos (removed, private, or region-locked)
- **NFR9:** The weighted randomization shall maintain 20-40% familiar content while ensuring 60-80% variety
- **NFR10:** The system shall continue functioning if individual channels or playlists become unavailable
- **NFR11:** No user data or viewing history shall be shared with third parties beyond required YouTube API calls
- **NFR12:** The warning tone/notification shall be audible but not jarring, using child-friendly sounds

## User Interface Design Goals

### Overall UX Vision
A colorful, playful interface that empowers young children to make independent choices within parent-defined boundaries. The design eliminates cognitive overload through simplicity - no text-dependent navigation, no complex menus, no infinite scrolling. Every interaction should feel predictable and safe, like choosing toys from a toy box rather than navigating a store.

### Key Interaction Paradigms
- **Visual-First Selection:** Large, clear thumbnails as the only decision point
- **Single-Click Simplicity:** One click to select, automatic progression
- **Predictable Returns:** Always return to the same home grid after videos
- **Gentle Boundaries:** Soft transitions when limits are reached, not abrupt stops
- **Invisible Complexity:** All configuration hidden behind parent gateway
- **Audio Feedback:** Playful sounds confirm actions (with disable option)

### Core Screens and Views
- **Home Grid View:** The main selection interface with configurable video thumbnails
- **Video Playback View:** Fullscreen video with YouTube's standard hover progress bar
- **Wind-Down Transition Screen:** Softer visual/audio cue when approaching time limit
- **Daily Limit Reached Screen:** Friendly goodbye with tomorrow's promise featuring mascot
- **Grace Video Selection:** Filtered grid showing only short videos for "one more"
- **Parent Gateway:** Simple password entry to access management
- **Channel Management Dashboard:** Add/remove sources, configure settings
- **Settings Panel:** Grid size, time limits, sound toggles, and other preferences
- **Video History View:** Parent-accessible list of recently watched videos for manual replay

### Accessibility: WCAG AA
Standard web accessibility compliance ensuring the app is usable by parents and children with various needs.

### Branding
- **Visual Style:** Bright, colorful design with yellow as accent color among rainbow palette
- **Typography:** Large, friendly fonts for the Norwegian UI text
- **Animation:** Playful, bouncy transitions between states
- **Sound Design:** Cheerful selection sounds and gentle notifications (optional via settings)
- **Character/Mascot:** Friendly animated character for transitions and limit messages

### Target Device and Platforms: Web Responsive
- **Primary:** Laptop/desktop computers with mouse interaction
- **Secondary:** Tablet support with touch optimization
- **Responsive design** adapting to both device types
- Landscape orientation preferred for video viewing
- Click-first interactions with touch as progressive enhancement

## Technical Assumptions

### Repository Structure: Monorepo

### Service Architecture: Monolith

### Testing Requirements: Unit + Integration

### Additional Technical Assumptions and Requests

**Frontend Technology:**
- Vanilla JavaScript with minimal dependencies (no build step if possible)
- Simple DOM manipulation for the video grid
- YouTube IFrame API for player embedding
- CSS Grid/Flexbox for responsive layout

**Backend Technology:**
- Python with FastAPI (simple, fast, minimal boilerplate)
- uv for Python package management (fast, modern alternative to pip)
- Jinja2 templates for server-side rendering where appropriate
- Static file serving for assets
- YouTube Data API v3 for both channels and playlists (primary approach)
- RSS parsing as fallback option (only shows 15 most recent videos)

**Database:**
- SQLite for persistence

**YouTube API Configuration:**
- Google Cloud project with YouTube Data API v3 enabled
- API key stored as environment variable
- Daily quota: 10,000 units (sufficient for initial channel loads and daily refreshes)
- Channel video fetch: ~100 units per channel (one-time, then cached)
- Playlist fetch: 1 unit per playlist
- Video metadata caching to minimize repeated API calls

**Deployment:**
- Direct deployment to Hetzner VPS (no Docker unless needed)
- Simple systemd service for the Python app
- Nginx reverse proxy
- Git pull + uv sync for updates

# Epic List

**Change Status:** ✅ APPROVED (Sprint Change Proposal - 2025-01-09)  
**Total Epics:** 5 (was 3)  
**Total Stories:** 19 (was 15)

---

## Epic Overview

**Epic 1: Foundation & Infrastructure (8 stories)**  
Establish complete development infrastructure, YouTube integration, and content management. Delivers: Parent can add channels, system ready for child interface.

**Epic 2: Child Viewing Experience (3 stories)**  
Implement child-facing interface for video selection and playback. Delivers: Child can watch videos from approved channels.

**Epic 3: Parent Features & History (3 stories)**  
Provide parent management and monitoring capabilities. Delivers: Complete parent control and history tracking.

**Epic 4: Time Limits & Enhancements (5 stories)**  
Implement time-based safety features and enhanced selection. Delivers: Complete MVP with all safety features.

**Epic 5: Deployment & Production Readiness (5 stories)**  
Production infrastructure, monitoring, and operations. Delivers: System ready for production use.

---

## Epic 1: Foundation & Infrastructure

**Goal:** Establish complete development infrastructure, YouTube integration, and content management before proceeding to child interface.

**Deliverable:** Parent can add channels via admin interface; system is ready for child interface development with all foundational infrastructure in place.

### Story 1.1: Project Foundation and Basic Server Setup

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
7. Python dependencies managed with uv (pyproject.toml with FastAPI, uvicorn, feedparser, google-api-python-client)
8. **Database schema initialized using backend/db/init_db.py**
9. **Admin password set via environment variable during initialization**
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

### Story 1.X: Testing Infrastructure Setup

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

### Story 1.Y: Frontend Foundation & Build Setup

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

### Story 1.Z: Design System Implementation

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

### Story 1.2: YouTube API Setup

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

### Story 1.3: YouTube API Integration for Video Fetching

As a parent,
I want the system to fetch complete video lists from YouTube channels and playlists,
so that all available content from approved sources is accessible.

**Acceptance Criteria:**
1. YouTube Data API v3 client configured with API key from environment
2. Function to fetch all videos from a channel (paginated, up to 500 videos)
3. Function to fetch all videos from a playlist (up to 200 videos)
4. Extract video ID, title, thumbnail URL, duration, and publish date
5. Handle pagination for channels with many videos
6. Cache video metadata in SQLite database
7. Gracefully handle API quota limits with appropriate error messages
8. RSS fallback function for channels if API fails (returns 15 most recent)
9. Track API quota usage and display in admin interface
10. Batch API calls efficiently to minimize quota consumption

### Story 1.4: Basic Admin Authentication

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

### Story 1.5: Channel Management

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

## Epic 2: Child Viewing Experience

**Goal:** Implement the child-facing interface for video selection and playback using content from Epic 1.

**Deliverable:** Child can select and watch videos from parent-approved channels in a safe, engaging interface.

### Story 2.1: Child-Friendly Video Grid Interface

As a child,
I want to see colorful video thumbnails in a grid,
so that I can choose what to watch.

**Acceptance Criteria:**
1. HTML page displays 3x3 grid of video thumbnails (9 videos)
2. Videos randomly selected from available content (from channels added in Story 1.5)
3. Thumbnails are large and clickable (minimum 200x150px)
4. Video titles appear below thumbnails in readable font
5. Colorful, playful CSS styling with yellow accents (using design system from Story 1.Z)
6. Page works on 1920x1080 screens (laptop primary)
7. Responsive layout adapts for tablet screens (1024x768 minimum)
8. No navigation elements or text-based menus
9. Mascot character visible in corner or header
10. Grid refreshes when returning from video playback

### Story 2.2: Video Playback

As a child,
I want to click a video thumbnail and watch the video,
so that I can enjoy the content.

**Acceptance Criteria:**
1. Clicking thumbnail opens full-screen video player
2. YouTube IFrame Player API embedded for playback
3. Player fills entire screen with minimal chrome
4. "Back to Videos" button prominently displayed (large, colorful)
5. Video plays immediately on load (autoplay enabled)
6. Player controls are child-friendly (large play/pause, volume)
7. Video completes and returns to grid automatically
8. Back button returns to grid without reloading entire page
9. Video playback tracked (video_id, timestamp, duration) in database
10. Error handling for failed video loads (show friendly message, return to grid)

### Story 2.3: Security and SEO Prevention

As a parent,
I want the application to prevent search engine indexing and unauthorized access,
so that the application remains private and safe.

**Acceptance Criteria:**
1. robots.txt file created blocking all crawlers (User-agent: *, Disallow: /)
2. Meta tags added to all pages (noindex, nofollow, noarchive)
3. X-Robots-Tag HTTP header added to all responses
4. Google-specific meta tags to prevent indexing (googlebot: noindex)
5. No external analytics or tracking scripts included
6. Content Security Policy (CSP) header configured to restrict external resources
7. Child interface has no external links or navigation away from application
8. YouTube player API only loads necessary components
9. HTTPS enforced in production (HTTP redirects to HTTPS)
10. Admin interface behind authentication (no anonymous access)

---

## Epic 3: Parent Features & History

**Goal:** Provide comprehensive parent management capabilities and viewing history tracking.

**Deliverable:** Parent has complete control over settings and can review watch history.

### Story 3.1: Watch History and Manual Replay

As a parent,
I want to view complete watch history and manually replay any video,
so that I can see what my child watched and review content.

**Acceptance Criteria:**
1. Admin page displays all watched videos with timestamps
2. History sorted by most recent first
3. Each entry shows: thumbnail, title, channel name, date/time watched, duration
4. Filtering options: by date range, by channel, by child (future-proofing)
5. Search functionality to find specific videos by title
6. "Play Video" button opens video in modal player within admin interface
7. Video plays without adding to child's history (admin preview mode)
8. History data stored permanently (not cleared automatically)
9. Export history to CSV functionality (optional)
10. Pagination for long history lists (50 entries per page)

### Story 3.2: Configuration Settings Interface

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

### Story 3.X: Admin Help & Documentation

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

## Epic 4: Time Limits & Enhancements

**Goal:** Implement time-based safety features and enhanced video selection for complete MVP.

**Deliverable:** Application with daily limits, warnings, mascot interactions, and smart selection.

### Story 4.1: Time-Based Viewing Limits

As a parent,
I want automatic daily viewing limits,
so that screen time is controlled without manual intervention.

**Acceptance Criteria:**
1. Viewing session tracked in database (start time, video count, status)
2. Daily limit retrieved from settings (default: 5 videos)
3. Session starts when child first selects a video
4. Video counter increments with each completed video
5. When limit reached, redirect to "That's All for Today" screen
6. Limit resets at midnight (configurable timezone)
7. Parent can reset limit early via admin interface
8. Session persists across browser refreshes
9. Partial videos count toward limit (>50% watched)
10. Admin dashboard shows current session status

### Story 4.2: Progressive Warning System and Wind-Down Mode

As a child,
I want gentle warnings before time is up,
so that I'm not surprised when videos end.

**Acceptance Criteria:**
1. Warning appears after video N-2 (e.g., after video 3 of 5)
2. Warning message: "2 videoer igjen!" displayed prominently
3. Warning uses friendly, encouraging language
4. After video N-1, message: "1 video igjen!"
5. Wind-down mode activates at video N-1 (visual changes: softer colors)
6. Mascot appears during warnings with encouraging messages
7. Warnings dismissible with "Ok, jeg forstår" button
8. No warnings if limit is 1 video (goes straight to goodbye)
9. Warnings logged for parent review
10. Audio chime plays with warnings (if audio enabled in settings)

### Story 4.3: Grace Video and Mascot Integration

As a child,
I want a friendly goodbye experience with one bonus "grace video",
so that ending feels positive and rewarding.

**Acceptance Criteria:**
1. After final video (video N), "You're All Done!" screen appears
2. Mascot character prominently displayed with goodbye message
3. Two buttons: "See You Tomorrow!" and "One More Video?"
4. "One More Video?" allowed once per day (grace video)
5. Grace video counted separately (not in daily limit)
6. After grace video, only goodbye screen shown (no second grace)
7. Grace video tracked in database with flag
8. Mascot animation or special visual when grace video granted
9. Goodbye screen includes time remaining until reset (e.g., "Come back in 8 timer!")
10. All text in Norwegian, child-friendly language

### Story 4.4: Engagement-Based Smart Selection

As a parent,
I want videos selected based on past engagement,
so that my child sees varied content they enjoy.

**Acceptance Criteria:**
1. Engagement score calculated per video (completion rate, replay frequency)
2. Videos weighted by engagement: high engagement = higher selection probability
3. Recently watched videos (last 24h) have lower weight (encourage variety)
4. Never completely hide videos (always small chance of selection)
5. Parent can reset engagement data via admin interface
6. Selection algorithm balances novelty and familiar favorites
7. Selection feels random to child despite weighting
8. Algorithm maintains variety across multiple channels
9. Edge case handling: all videos recently watched (select randomly)
10. Engagement data tracked in database (views table with completion percentage)

### Story 4.5: Audio Feedback System

As a child,
I want fun sounds when I select videos,
so that the experience feels playful and responsive.

**Acceptance Criteria:**
1. Playful "pop" sound on thumbnail click
2. Gentle transition sound when returning to grid
3. Pleasant chime for warnings (not jarring)
4. Parent setting to enable/disable all sounds
5. Volume controls in parent interface
6. Sounds load quickly and don't delay interactions
7. All audio files optimized for web (small file size, <100KB each)
8. Sounds appropriate for young children (no scary or harsh sounds)
9. Fallback: application works perfectly without audio
10. Audio files stored in frontend/public/sounds/ directory

---

## Epic 5: Deployment & Production Readiness

**Goal:** Production deployment infrastructure, monitoring, and complete operational procedures.

**Deliverable:** System deployed to production with monitoring, backups, and parent-friendly operations documentation.

### Story 5.1: Systemd Service Configuration

As an operations team member,
I want systemd services configured for application lifecycle management,
so that the application runs reliably in production.

**Acceptance Criteria:**
1. Systemd service file created (youtube-viewer.service)
2. Service runs FastAPI application via uvicorn
3. Service starts on boot (enabled)
4. Service restarts on failure (automatic recovery)
5. Service runs as dedicated user (not root)
6. Environment variables loaded from /opt/youtube-viewer/.env
7. Working directory set correctly
8. Logging configured to journald
9. Service can be started/stopped/restarted via systemctl
10. Service status shows clear health information

### Story 5.2: Production Server Setup (Hetzner VPS)

As an operations team member,
I want the Hetzner VPS configured for production deployment,
so that the application runs securely and efficiently.

**Acceptance Criteria:**
1. Hetzner CX11 VPS provisioned (Falkenstein, Germany)
2. Ubuntu 22.04 LTS installed and updated
3. Firewall configured (UFW): allow SSH, HTTP, HTTPS; deny all else
4. SSH hardened (key-only auth, root login disabled)
5. Python 3.11.7 and uv installed system-wide
6. Node.js 20.x installed for frontend builds
7. Nginx installed and configured as reverse proxy
8. SSL certificate provisioned (Let's Encrypt via certbot)
9. Application directory structure created (/opt/youtube-viewer/)
10. Database directory with proper permissions

### Story 5.3: Deployment Scripts & Automation

As an operations team member,
I want automated deployment scripts,
so that updates can be deployed safely and consistently.

**Acceptance Criteria:**
1. deploy.sh script created for deployment automation
2. Script pulls latest code from repository
3. Script runs database migrations if needed
4. Script installs/updates backend dependencies (uv sync)
5. Script builds frontend (npm run build)
6. Script restarts systemd service
7. Script includes rollback procedure if deployment fails
8. Script includes health check after deployment
9. Script logs all actions with timestamps
10. Script executable by designated user (not root)

### Story 5.4: Monitoring & Maintenance Setup

As an operations team member,
I want monitoring and maintenance procedures,
so that I can ensure system health and respond to issues.

**Acceptance Criteria:**
1. Health check endpoint (/health) returns detailed status
2. Systemd service includes periodic health checks
3. Log rotation configured (logrotate for application logs)
4. Backup script created (scripts/backup.sh) for database
5. Backup timer configured (daily backups at 2 AM)
6. Backup retention policy (keep last 7 days)
7. Restore script created (scripts/restore.sh) with verification
8. Monitoring dashboard showing: uptime, API quota usage, session status
9. Alert thresholds defined (optional: email alerts for failures)
10. Weekly maintenance tasks documented (manual or automated)

### Story 5.5: Parent Operations Guide

As a parent operating the application,
I want a simplified operations guide in Norwegian,
so that I can maintain and troubleshoot the system independently.

**Acceptance Criteria:**
1. Operations guide created (docs/operations-guide-no.md) in Norwegian
2. Guide includes step-by-step deployment procedure
3. Guide includes backup and restore procedures
4. Guide includes log viewing instructions (journalctl commands)
5. Guide includes common troubleshooting scenarios with solutions
6. Guide includes weekly/monthly maintenance checklist
7. Guide written in clear, non-technical Norwegian
8. Guide includes screenshots or command examples
9. Guide covers: starting/stopping service, viewing logs, restoring from backup
10. Guide accessible from admin interface (link to documentation)

---

## Implementation Notes

**Epic Restructure Rationale:**
- Resolves circular dependency (Epic 1 can now be completed independently)
- Adds missing foundational infrastructure (testing, frontend, design system)
- Proper sequencing of dependencies (API setup before usage)
- Clear deployment path with dedicated Epic 5

**Development Sequence:**
1. Complete Epic 1 → Delivers foundation + content management capability
2. Complete Epic 2 → Delivers functional child viewing experience
3. Complete Epic 3 → Delivers complete parent management
4. Complete Epic 4 → Delivers full MVP with time limits and enhancements
5. Complete Epic 5 → Delivers production-ready deployment

**Total Stories:** 19 (8+3+3+5+5)  
**Estimated Effort:** Epic 1: 2-3 weeks | Epic 2: 1 week | Epic 3: 1 week | Epic 4: 1-2 weeks | Epic 5: 1 week

## Checklist Results Report

### Executive Summary

- **Overall PRD Completeness:** 87%
- **MVP Scope Appropriateness:** Just Right
- **Readiness for Architecture Phase:** Ready
- **Most Critical Gaps:** Non-functional requirements (backup/recovery, monitoring), operational requirements

### Category Analysis

| Category                         | Status  | Critical Issues |
| -------------------------------- | ------- | --------------- |
| 1. Problem Definition & Context  | PASS    | None critical   |
| 2. MVP Scope Definition          | PASS    | None critical   |
| 3. User Experience Requirements  | PASS    | None critical   |
| 4. Functional Requirements       | PASS    | None critical   |
| 5. Non-Functional Requirements   | PARTIAL | Backup/recovery, monitoring not defined |
| 6. Epic & Story Structure        | PASS    | None critical   |
| 7. Technical Guidance            | PASS    | None critical   |
| 8. Cross-Functional Requirements | PARTIAL | Data retention, monitoring gaps |
| 9. Clarity & Communication       | PASS    | Could use diagrams |

### Key Findings

**Strengths:**
- Clear problem definition with specific target users
- Well-structured epics delivering incremental value
- Comprehensive functional requirements with testable acceptance criteria
- Technical approach optimized for simplicity (RSS feeds, minimal dependencies)
- Strong focus on child safety and user experience

**Areas for Improvement:**
- Add backup/recovery strategy for SQLite database
- Define monitoring and alerting approach
- Specify data retention policies for watch history
- Consider adding architecture diagrams
- Document deployment process more explicitly

### MVP Validation

The MVP scope is appropriately sized for initial deployment:
- Core viewing experience can be deployed after Epic 1
- Parent controls add essential management without blocking functionality
- Enhancement features in Epic 3 can be iteratively added
- Technical choices (RSS feeds) minimize complexity and API dependencies

### Technical Readiness Assessment

The PRD provides sufficient technical guidance for architecture phase:
- Clear technology stack decisions (FastAPI, vanilla JS, SQLite)
- Integration approach well-defined (RSS for channels, API for playlists)
- Deployment target specified (Hetzner VPS)
- Security considerations addressed (password protection, no indexing)

## Next Steps

### UX Expert Prompt

Please review the Safe YouTube Viewer for Kids PRD and create detailed UI/UX specifications focusing on the child-friendly visual interface, colorful grid layout with yellow accents, and the friendly mascot character for transitions. Ensure all interactions are optimized for non-readers ages 2-6.

### Architect Prompt

Please create the technical architecture for the Safe YouTube Viewer for Kids application using the PRD as input. Focus on the FastAPI/vanilla JS stack with RSS feed integration for channels and YouTube API for playlists, SQLite storage, and simple deployment to Hetzner VPS. Emphasize simplicity and minimal dependencies.