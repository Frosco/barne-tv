# Source Tree Structure

Based on your chosen monorepo structure with FastAPI backend and Vite frontend, here's the complete directory layout:

```
safe-youtube-viewer/
├── backend/                    # Python FastAPI application
│   ├── services/              # Business logic services
│   │   ├── __init__.py
│   │   ├── viewing_session.py    # Video selection + daily limits
│   │   └── content_source.py     # YouTube fetching + source management
│   ├── db/                    # Database layer
│   │   ├── __init__.py
│   │   ├── queries.py            # Direct SQL functions (sync)
│   │   ├── init_db.py            # Database initialization
│   │   ├── maintenance.py        # Cleanup operations
│   │   └── schema.sql            # DDL
│   ├── routes.py              # Single file with all routes
│   ├── auth.py                # Session management module
│   ├── main.py                # FastAPI app entry point
│   ├── config.py              # Configuration management
│   ├── exceptions.py          # Custom exception classes
│   ├── logging.conf           # Logging configuration
│   └── __init__.py
├── frontend/                   # Vite + Vanilla JS frontend
│   ├── src/                   # Source files (tests collocated)
│   │   ├── child/             # Child interface logic
│   │   │   ├── grid.js           # Video grid rendering
│   │   │   ├── grid.test.js      # Grid unit tests
│   │   │   ├── player.js         # YouTube IFrame integration
│   │   │   ├── player.test.js    # Player unit tests
│   │   │   ├── limit-tracker.js  # Time limit monitoring
│   │   │   └── limit-tracker.test.js  # Limit tracker tests
│   │   ├── admin/             # Admin interface logic
│   │   │   ├── channels.js       # Channel management
│   │   │   ├── channels.test.js  # Channels tests
│   │   │   ├── history.js        # Watch history view
│   │   │   ├── settings.js       # Settings management
│   │   │   └── settings.test.js  # Settings tests
│   │   ├── shared/            # Shared utilities
│   │   │   ├── api.js            # API client
│   │   │   ├── api.test.js       # API client tests
│   │   │   ├── state.js          # State management
│   │   │   └── state.test.js     # State tests
│   │   ├── child.js           # Child interface entry point
│   │   ├── admin.js           # Admin interface entry point
│   │   ├── main.css           # Global styles
│   │   └── sample.test.js     # Test infrastructure verification
│   ├── public/                # Static assets
│   │   ├── images/            # Mascot images, icons
│   │   │   ├── mascot-happy.svg
│   │   │   ├── mascot-wave.svg
│   │   │   ├── mascot-curious.svg
│   │   │   ├── mascot-shrug.svg
│   │   │   └── mascot-thinking.svg
│   │   └── sounds/            # Warning chimes
│   │       └── gentle-chime.mp3
│   ├── templates/             # Jinja2 templates
│   │   ├── base.html
│   │   ├── child/
│   │   │   ├── grid.html         # Video grid view
│   │   │   ├── grace.html        # Grace video selection
│   │   │   └── goodbye.html      # Goodbye screen
│   │   └── admin/
│   │       ├── login.html
│   │       ├── dashboard.html
│   │       ├── channels.html
│   │       ├── history.html
│   │       └── settings.html
│   ├── vite.config.js         # Vite configuration
│   ├── vitest.config.js       # Vitest configuration
│   ├── playwright.config.js   # Playwright configuration
│   ├── package.json           # Frontend dependencies
│   └── .eslintrc.json         # ESLint configuration
├── static/                     # Built frontend assets (generated, in .gitignore)
│   ├── assets/
│   └── dist/
├── scripts/                    # Deployment and maintenance
│   ├── setup-server.sh        # Initial server setup
│   ├── deploy.sh              # Deployment script
│   ├── backup.sh              # Database backup
│   ├── restore.sh             # Restore from backup
│   ├── logs.sh                # View logs
│   ├── refresh-all-sources.py # Weekly refresh script
│   └── systemd/               # Systemd service files
│       ├── youtube-viewer.service
│       ├── youtube-viewer-backup.service
│       ├── youtube-viewer-backup.timer
│       ├── youtube-viewer-refresh.service
│       └── youtube-viewer-refresh.timer
├── docs/                       # Documentation
│   ├── prd.md
│   ├── frontend-spec.md
│   └── architecture.md        # This document
├── tests/                      # Test files
│   ├── backend/               # Backend unit tests
│   │   ├── services/
│   │   │   ├── test_viewing_session.py
│   │   │   └── test_content_source.py
│   │   ├── db/
│   │   │   └── test_queries.py
│   │   ├── safety/            # TIER 1 safety tests
│   │   │   └── test_tier1_safety_rules.py
│   │   ├── security/          # Security tests
│   │   │   └── test_security.py
│   │   ├── test_routes.py
│   │   ├── test_auth.py
│   │   └── conftest.py        # Pytest fixtures
│   ├── integration/           # Integration tests
│   │   ├── test_api_integration.py
│   │   └── conftest.py
│   ├── e2e/                   # End-to-end tests
│   │   ├── specs/
│   │   │   ├── child-viewing-flow.spec.js
│   │   │   ├── time-limit-flow.spec.js
│   │   │   ├── grace-video-flow.spec.js
│   │   │   └── banned-video-safety.spec.js
│   │   └── fixtures/
│   │       └── test-data.json
│   ├── helpers/               # Test utilities
│   │   ├── database.py        # Database test helpers
│   │   └── e2e.py             # E2E test helpers
│   ├── fixtures/              # Test data
│   │   ├── sample_videos.json
│   │   ├── sample_channels.json
│   │   └── sample_history.json
│   └── mocks/                 # Mock objects
│       └── youtube_api_mock.py
├── .env.example                # Environment template
├── .gitignore
├── pyproject.toml              # Python project config (uv)
├── pytest.ini                 # Pytest configuration
├── README.md
└── nginx.conf                  # Nginx configuration template
```

**Rationale for this structure:**

1. **Backend Simplicity**: Single `routes.py` file (~400 lines) with section comments for organization - appropriate for this 15-20 endpoint API
2. **Service Layer**: Only two service files (`viewing_session.py` and `content_source.py`) - matches the simplified architecture
3. **Database Direct Access**: `db/queries.py` with synchronous SQL functions - no repository abstraction overhead
4. **Frontend Organization**: Vite build tool with separate entry points for child (`child.js`) and admin (`admin.js`) interfaces
5. **Template-First**: Jinja2 templates for SSR, then progressive enhancement with vanilla JS
6. **Static Assets**: Separated into `public/` (source) and `static/` (built output, gitignored)
7. **Testing Structure**: Three layers - unit (isolated), integration (cross-layer), e2e (browser)
8. **Systemd Services**: All service files in `scripts/systemd/` for deployment

**Key Decisions:**
- No `models/` directory - using dict-based data passing (Python dataclasses if needed)
- Auth logic in `auth.py` module, not a separate service
- Backend tests mirror source structure in `tests/backend/` directory
- **Frontend tests collocated** with source files in `frontend/src/` for vitest module resolution (vitest best practice)
- Additional integration and e2e test layers in `tests/integration/` and `tests/e2e/`
- `pyproject.toml` for Python dependencies (uv manages environment)
- Frontend dependencies in separate `package.json`
- `static/` directory is build output only (in .gitignore)

**Why this structure works for AI agents:**
- Clear separation of concerns (backend/frontend/static/docs/tests)
- Predictable file locations follow framework conventions
- Minimal nesting depth (max 3 levels in backend, 4 in frontend)
- Single-purpose files with clear naming
- No ambiguous directories like "utils" or "helpers"

**Integration points:**
- Backend serves templates from `frontend/templates/`
- Vite builds to `static/` directory which Nginx serves
- Backend and frontend share no code (separate runtimes)
- API communication via `/api/*` routes

**Deployment considerations:**
- Backend runs as systemd service
- Nginx serves static files and proxies API requests
- Database at `/opt/youtube-viewer/data/app.db`
- Logs at `/var/log/youtube-viewer/`

---

