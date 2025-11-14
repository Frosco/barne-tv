# Safe YouTube Viewer for Kids

A web application designed for children ages 2-6 to safely watch YouTube videos from parent-approved channels and playlists. The application eliminates inappropriate content exposure through complete parental control while enabling independent video selection through a visual, child-friendly interface requiring no reading ability.

## Features

- **Parent-Controlled Content**: Only videos from approved YouTube channels/playlists
- **Engagement-Based Video Selection**: Smart algorithm surfaces videos based on watch history
- **Daily Time Limits**: Configurable viewing time with gentle wind-down warnings
- **Child-Friendly Interface**: Visual grid with no reading required
- **Grace Video Option**: One more short video when time limit reached
- **Watch History**: Parent can review what was watched and manually replay videos
- **Banned Videos**: Parent can block specific videos from reappearing
- **API Quota Tracking**: Monitor YouTube API usage to stay within daily limits
- **Rate Limiting**: Protection against excessive API requests
- **Self-Hosted**: Complete control over your data and deployment
- **Production Ready**: Deployed on Hetzner VPS with systemd services and monitoring

## Target Audience

- **Norwegian family** with children ages 2-6
- **Self-hosted** on Hetzner VPS or similar
- **Privacy-focused** with no third-party data sharing

## Project Status

**Current Phase**: Foundation infrastructure complete, production deployed

### Key Architecture Decisions

- **All-synchronous backend** - No async/await (intentional for single-family deployment)
- **Single routes.py file** - All ~20 API endpoints in one file with section comments
- **Two service files** - `viewing_session.py` and `content_source.py` only
- **Direct SQL access** - Services call `queries.py` directly, no repository abstraction
- **Video duplicates allowed** - Same YouTube video can exist in multiple rows (simplifies cascade deletion)
- **Norwegian UI messages** - User-facing messages in Norwegian, code/logs in English
- **Rate limiting** - slowapi middleware protects against API abuse
- **Quota buffer** - Stop at 9,500 units (500 buffer below 10,000 daily limit)

## Prerequisites

Before installing, ensure you have:

- **Python 3.11** (>=3.11,<3.12 required)
- **uv** package manager (latest version)
- **Node.js 22.x LTS** (for frontend development)
- **SQLite 3.45.0+** (included with Python)
- **YouTube Data API v3 key** (from Google Cloud Console)

### Getting Python 3.11

```bash
# Using mise (recommended)
mise install python@3.11
mise use python@3.11

# Or using pyenv
pyenv install 3.11
pyenv local 3.11
```

### Getting uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Getting Node.js 22 LTS

```bash
# Using mise
mise use node@20

# Or using nvm
nvm install 22
nvm use 22
```

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/barne-tv.git
cd barne-tv
```

### 2. Configure Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit .env and configure:
# - DATABASE_PATH (use ./data/app.db for local development)
# - YOUTUBE_API_KEY (from Google Cloud Console)
# - ALLOWED_HOSTS (leave as localhost,127.0.0.1 for local)
nano .env
```

### 3. Install Python Dependencies

```bash
# Install all dependencies (production + development)
uv sync --extra dev
```

### 4. Install Frontend Dependencies

```bash
# Install Node.js dependencies
cd frontend && npm install && cd ..
```

### 5. Initialize Database

```bash
# Create database directory
mkdir -p data

# Initialize database with admin password
# Replace 'your_secure_password' with your actual password
uv run python backend/db/init_db.py your_secure_password
```

This will:
- Create SQLite database at configured path
- Create all tables, indexes, views, and triggers
- Set admin password (hashed with bcrypt)
- Insert default settings

## YouTube API Setup

**Required for video fetching functionality.**

The application uses YouTube Data API v3 to fetch videos from approved channels and playlists. You need to:

1. **Create a Google Cloud project**
2. **Enable YouTube Data API v3**
3. **Generate an API key with restrictions**
4. **Add the key to your `.env` file**

### Quick Setup

```bash
# 1. Get your API key from Google Cloud Console
# Visit: https://console.cloud.google.com/apis/credentials

# 2. Add to .env file
echo "YOUTUBE_API_KEY=your_api_key_here" >> .env

# 3. Test the API key (server will validate on startup)
uv run uvicorn backend.main:app --reload
```

### Detailed Setup Guide

📖 **See [docs/youtube-api-setup.md](docs/youtube-api-setup.md) for:**
- Step-by-step Google Cloud Console instructions
- API key security and restrictions
- Quota limits and monitoring (10,000 units/day)
- Troubleshooting common issues
- Best practices and security guidelines

### Quota Information

- **Daily Limit:** 10,000 quota units (resets midnight Pacific Time)
- **Buffer Threshold:** Application stops at 9,500 units (500 buffer)
- **Typical Usage:** ~66 channels with 50 videos each per day
- **Quota Tracking:** All API calls logged to `api_usage_log` table

### Monitoring Your Quota

```bash
# Check today's quota usage
sqlite3 data/app.db "SELECT SUM(quota_cost) FROM api_usage_log WHERE DATE(timestamp) = DATE('now');"

# See API call breakdown
sqlite3 data/app.db "
SELECT api_name, COUNT(*) as calls, SUM(quota_cost) as total_cost
FROM api_usage_log
WHERE DATE(timestamp) = DATE('now')
GROUP BY api_name;
"

# Check remaining quota (application stops at 9,500)
sqlite3 data/app.db "SELECT 9500 - COALESCE(SUM(quota_cost), 0) as remaining FROM api_usage_log WHERE DATE(timestamp) = DATE('now');"
```

## Running Locally

### Start Backend Server

```bash
# Start FastAPI server with auto-reload
uv run uvicorn backend.main:app --reload

# Server will start at http://localhost:8000
```

### Start Frontend Dev Server

```bash
# Start Vite dev server with hot module replacement
npm run dev

# Frontend runs at http://localhost:5173
```

### Verify Health Check

```bash
# Test that server is running
curl http://localhost:8000/health

# Expected output: {"status":"ok"}
```

### Access Application

- **Child Interface**: http://localhost:8000/ (in development)
- **Admin Interface**: http://localhost:8000/admin (implemented)
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs (FastAPI Swagger UI)

## Running Tests

### Backend Tests (pytest)

```bash
# Run all backend tests with verbose output
uv run pytest tests/backend/ -v

# Run tests with coverage report
uv run pytest tests/backend/ --cov=backend --cov-report=html

# Run TIER 1 safety tests only (must always pass)
uv run pytest -m tier1 -v

# Run security tests only
uv run pytest -m security -v

# Run performance benchmarks
uv run pytest -m performance -v

# Run specific test file
uv run pytest tests/backend/test_health.py -v

# Run integration tests
uv run pytest tests/integration/ -v

# View HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Frontend Tests (vitest)

```bash
# Run all frontend tests
npm test

# Run tests in watch mode (auto-rerun on changes)
npm test -- --watch

# Run tests with coverage report
npm run test:coverage

# View HTML coverage report
open frontend/coverage/index.html  # macOS
xdg-open frontend/coverage/index.html  # Linux
```

### End-to-End Tests (Playwright)

```bash
# Run E2E tests
npm run test:e2e

# Run E2E tests with UI
npm run test:e2e:ui
```

### Test Markers

The following pytest markers are configured:
- `tier1` - TIER 1 child safety tests (must always pass before deployment)
- `security` - Security-specific tests (SQL injection, password hashing, etc.)
- `performance` - Performance benchmark tests

Example: `pytest -m "tier1 or security" -v`

### Coverage Thresholds

- **Backend**: 85% overall, 100% for safety-critical code
- **Frontend**: 70% acceptable for UI components

### Test Organization

```
tests/
├── backend/
│   ├── conftest.py               # Shared fixtures
│   ├── test_health.py            # Health endpoint tests
│   ├── services/                 # Service layer tests
│   ├── db/                       # Database tests
│   ├── safety/                   # TIER 1 safety tests
│   └── security/                 # Security tests
├── integration/                  # Integration tests
│   ├── test_auth.py
│   ├── test_content_sources.py
│   └── test_viewing_session.py
└── e2e/                          # Playwright E2E tests (future)
```

## Development Workflow

### Code Formatting

```bash
# Backend - Format all Python files with Black
uv run black .

# Backend - Check formatting without making changes
uv run black --check .

# Frontend - Format JavaScript files
npm run format

# Frontend - Check formatting
npm run format:check
```

### Linting

```bash
# Backend - Run Ruff linter
uv run ruff check .

# Backend - Auto-fix issues where possible
uv run ruff check --fix .

# Frontend - Run ESLint
npm run lint

# Frontend - Auto-fix issues
npm run lint:fix
```

### Type Checking

```bash
# Backend - Run mypy type checker
uv run mypy backend/
```

### Database Management

```bash
# Initialize/reset database
uv run python backend/db/init_db.py <new_password>

# Run maintenance tasks (cleanup old data)
uv run python backend/db/maintenance.py

# View database schema
sqlite3 data/app.db .schema

# Seed test data (for development)
uv run python backend/db/seed_test_data.py
```

### Frontend Development

```bash
# Start Vite dev server with HMR
npm run dev

# Build for production (outputs to static/)
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
barne-tv/
├── backend/                       # Python FastAPI application
│   ├── services/                 # Business logic services
│   │   ├── viewing_session.py       # Video selection, daily limits, engagement algorithm
│   │   └── content_source.py        # YouTube API integration, channel/playlist fetching
│   ├── db/                       # Database layer
│   │   ├── schema.sql               # Complete DDL (tables, indexes, views, triggers)
│   │   ├── init_db.py               # Database initialization
│   │   ├── queries.py               # SQL query functions (synchronous)
│   │   ├── maintenance.py           # Cleanup operations
│   │   └── seed_test_data.py        # Test data utilities
│   ├── main.py                   # FastAPI app entry point
│   ├── config.py                 # Environment configuration
│   ├── auth.py                   # Session management (in-memory)
│   ├── exceptions.py             # Custom exception classes
│   ├── routes.py                 # All API routes (~20 endpoints)
│   ├── middleware.py             # Rate limiting middleware
│   └── logging_config.py         # Logging configuration
├── frontend/                      # Vite + Vanilla JavaScript
│   ├── src/
│   │   ├── child.js                 # Child interface entry point
│   │   ├── admin.js                 # Admin interface entry point
│   │   ├── main.css                 # Design system CSS (14-color palette)
│   │   ├── child/                   # Child interface modules (in development)
│   │   ├── admin/                   # Admin interface modules (in development)
│   │   ├── shared/                  # Shared utilities
│   │   └── *.test.js                # Tests collocated with source
│   ├── templates/                # Jinja2 templates
│   │   ├── base.html                # Base template
│   │   ├── child/                   # Child templates (in development)
│   │   └── admin/                   # Admin templates (implemented)
│   ├── public/
│   │   ├── images/                  # Static images
│   │   └── sounds/                  # Audio files
│   ├── vite.config.js            # Vite configuration
│   ├── vitest.config.js          # Vitest test configuration
│   ├── eslint.config.js          # ESLint flat config (v9)
│   ├── playwright.config.js      # Playwright E2E configuration
│   └── package.json              # Frontend dependencies
├── static/                        # Built frontend assets (output from vite build)
├── tests/                         # Test files
│   ├── backend/                     # Backend unit tests
│   │   ├── conftest.py                 # Pytest fixtures
│   │   ├── services/                   # Service tests
│   │   ├── db/                         # Database tests
│   │   ├── safety/                     # TIER 1 safety tests
│   │   └── security/                   # Security tests
│   ├── integration/                 # Integration tests
│   └── e2e/                         # Playwright E2E tests (future)
├── docs/                          # Documentation
│   ├── youtube-api-setup.md         # YouTube API detailed setup guide
│   ├── getting-started-no.md        # Norwegian setup guide
│   ├── operations-guide-no.md       # Norwegian operations guide for parents
│   └── front-end-spec.md            # Frontend specifications
├── .env                           # Environment variables (not in git)
├── .env.example                   # Environment template
├── pyproject.toml                 # Python dependencies
├── package.json                   # Frontend dependencies (root)
└── README.md                      # This file
```

## Technology Stack

### Backend

**Core:**
- Python 3.11 (>=3.11,<3.12)
- FastAPI 0.118.0
- Uvicorn 0.37.0 (with standard extras)
- SQLite 3.45.0 (built-in)

**Dependencies:**
- google-api-python-client 2.184.0 (YouTube API integration)
- bcrypt >=4.2.1 (modern Rust-based password hashing)
- requests 2.32.5 (HTTP client)
- isodate 0.7.2 (ISO 8601 duration parsing)
- Jinja2 3.1.6 (server-side templates)
- python-multipart 0.0.20 (form data handling)
- python-dotenv 1.1.1 (environment variable loading)
- slowapi 0.1.9 (rate limiting middleware)

**Development Tools:**
- uv (package manager)
- pytest 8.4.2 (testing framework)
- pytest-cov 7.0.0 (coverage reporting)
- pytest-mock 3.15.1 (mocking utilities)
- pytest-benchmark 5.1.0 (performance testing)
- responses 0.25.8 (HTTP mocking)
- httpx 0.27.0 (async HTTP client for tests)
- freezegun 1.5.1 (time mocking for tests)
- black 25.9.0 (code formatter)
- ruff 0.14.0 (fast linter)
- mypy 1.15.0 (static type checker)

### Frontend

**Core:**
- Node.js 20.x LTS
- Vite 7.1.9 (build tool + dev server with HMR)
- Vanilla JavaScript ES2020+ (NO frameworks, NO TypeScript by design)
- CSS3 with custom properties (14-color design system)

**Development Tools:**
- Vitest 3.2.4 (unit testing)
- happy-dom 19.0.2 (fast DOM environment for tests, 2x faster than jsdom)
- @vitest/coverage-v8 3.2.4 (coverage reporting)
- @playwright/test 1.40.0 (E2E testing)
- ESLint 9.37.0 (linting with flat config)
- @eslint/js 9.37.0 (ESLint recommended rules)
- globals 16.4.0 (global variables definition)
- Prettier 3.1.1 (code formatter)

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `/opt/youtube-viewer/data/app.db` | SQLite database location |
| `YOUTUBE_API_KEY` | Required | YouTube Data API v3 key |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hostnames |
| `ENVIRONMENT` | `development` | `development` or `production` |

### Database Settings

Stored in `settings` table (managed via admin interface):
- `daily_limit_minutes`: Default 30
- `grid_size`: Default 9 videos (range 4-15)
- `audio_enabled`: Default true
- `admin_password_hash`: Bcrypt hash (never displayed)

### Rate Limiting

Configured via slowapi middleware:
- Global rate limit: 100 requests per minute per IP
- YouTube API routes: 10 requests per minute per IP
- Admin routes: 20 requests per minute per IP

### Hardcoded Safety Values

These values are intentionally NOT configurable in the database to protect child safety:
- Warning thresholds: 10, 5, 2 minutes remaining
- Wind-down start: 10 minutes remaining
- Grace video max duration: 5 minutes

## Security

### Authentication & Authorization
- **Password Security**: Admin passwords hashed with bcrypt (Rust-based, modern)
- **Session Management**: In-memory session storage (acceptable for single-family use)
- **Protected Routes**: Admin routes require valid session token

### Data Protection
- **SQL Injection**: All queries use parameterized placeholders (NEVER string formatting)
- **Input Validation**: All parent inputs validated and sanitized
- **XSS Prevention**: Jinja2 auto-escaping enabled
- **No Secrets in Git**: `.env` file excluded from version control

### Child Safety (TIER 1 Requirements)
- **Always filter banned videos** from results
- **Exclude manual_play and grace_play** from daily limit calculations
- **UTC time for all operations** to ensure consistency
- **Video availability tracking** prevents showing unavailable content

### API Protection
- **Rate limiting** via slowapi middleware
- **Quota buffer** (500 units) prevents exceeding YouTube API limits
- **API key validation** on server startup
- **Request logging** for debugging and monitoring

## Production Deployment

The application is deployed on a Hetzner VPS with the following setup:

### Deployment Architecture
- **Server**: Hetzner Cloud VPS (CX11 or similar)
- **OS**: Ubuntu 22.04 LTS
- **Web Server**: Nginx (reverse proxy)
- **Process Manager**: systemd (manages backend service)
- **Database**: SQLite (file-based, backed up regularly)
- **SSL**: Let's Encrypt (certbot for HTTPS)

### Systemd Service

Backend runs as a systemd service:
```bash
# Check service status
sudo systemctl status youtube-viewer

# Restart service
sudo systemctl restart youtube-viewer

# View logs
sudo journalctl -u youtube-viewer -f
```

### Monitoring

- **Health Check**: http://your-domain.com/health
- **API Quota**: Monitor via `api_usage_log` table
- **Service Status**: systemd status and logs
- **Error Tracking**: Application logs to syslog

### Operations Guide

For non-technical parents, see Norwegian documentation:
- [docs/getting-started-no.md](docs/getting-started-no.md) - Initial setup
- [docs/operations-guide-no.md](docs/operations-guide-no.md) - Daily operations

## Architecture

### Key Architectural Principles

1. **All-synchronous backend** - No async/await (intentional for simplicity)
2. **Single routes.py file** - All endpoints in one place with clear sections
3. **Two service files only** - `viewing_session.py` and `content_source.py`
4. **Direct SQL access** - No ORM, no repository abstraction
5. **Norwegian user messages** - UI in Norwegian, code/logs in English
6. **Safety-first design** - TIER 1 tests must pass before any deployment

## Documentation

### For Developers
- `docs/front-end-spec.md` - Frontend component specifications
- `docs/youtube-api-setup.md` - Detailed YouTube API setup

### For Parents (Norwegian)
- `docs/getting-started-no.md` - Komme i gang guide
- `docs/operations-guide-no.md` - Daglig drift og vedlikehold

## Testing Strategy

### Test Layers

1. **Unit Tests** (`tests/backend/`, `frontend/src/*.test.js`)
   - Test individual functions and components
   - Mock external dependencies
   - Fast execution, high coverage

2. **Integration Tests** (`tests/integration/`)
   - Test service interactions
   - Use in-memory SQLite database
   - Test API endpoints end-to-end

3. **E2E Tests** (`tests/e2e/` - future)
   - Test complete user workflows
   - Use Playwright for browser automation
   - Test across multiple browsers

### Test Organization

Tests mirror source structure:
- `backend/services/viewing_session.py` → `tests/backend/services/test_viewing_session.py`
- `frontend/src/child.js` → `frontend/src/child.test.js` (collocated)

### Test Fixtures

Shared fixtures in `tests/backend/conftest.py`:
- `test_db` - In-memory SQLite database
- `test_client` - FastAPI test client
- `mock_youtube` - Mocked YouTube API responses

### Safety Testing

TIER 1 tests (must always pass):
- Banned video filtering
- Daily limit calculation (excludes manual_play and grace_play)
- Password hashing with bcrypt
- SQL injection prevention (parameterized queries)
- UTC time usage

## Common Development Tasks

### Add a New API Endpoint

1. Add route in `backend/routes.py` (keep in single file)
2. Add business logic in appropriate service (`viewing_session.py` or `content_source.py`)
3. Add SQL queries in `backend/db/queries.py`
4. Write unit tests in `tests/backend/`
5. Write integration test in `tests/integration/`
6. Update API documentation if needed

### Add a New Frontend Component

1. Create component in `frontend/src/child/` or `frontend/src/admin/`
2. Add collocated test file (`*.test.js`)
3. Import in entry point (`child.js` or `admin.js`)
4. Run `npm test` to verify
5. Test in browser with `npm run dev`

### Update Database Schema

1. Modify `backend/db/schema.sql`
2. Update `init_db.py` if needed
3. Write migration script for production
4. Update tests to use new schema
5. Document changes if needed

## Contributing

This is a personal project for a Norwegian family. Not accepting external contributions at this time.

## License

See LICENSE file for details.

## Support

For issues or questions, see the documentation in `docs/` or create an issue in the repository.

---

**Built with Claude Code** | Version 1.0.0 | Last Updated: 2025-11-15
