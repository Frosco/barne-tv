# Development Workflow

This section provides complete instructions for setting up and working with the Safe YouTube Viewer for Kids development environment.

## Local Development Setup

### Prerequisites

Before beginning development, ensure you have these tools installed:

| Tool | Version | Purpose | Installation |
|------|---------|---------|--------------|
| Python | 3.11+ | Backend runtime | `apt install python3.11` |
| uv | 0.1.0+ | Python package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 20+ | Frontend tooling | `apt install nodejs npm` |
| SQLite | 3.45+ | Database | Usually pre-installed on Linux |
| Git | 2.40+ | Version control | `apt install git` |

**System Requirements:**
- Linux (Ubuntu 22.04+ or Debian 12+ recommended)
- 2GB RAM minimum (4GB recommended)
- 2GB disk space for development environment

### Initial Setup

**Step 1: Clone Repository**
```bash
git clone https://github.com/your-username/safe-youtube-viewer.git
cd safe-youtube-viewer
```

**Step 2: Backend Setup**
```bash
# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# OR on Windows: .venv\Scripts\activate

# Install backend dependencies
uv pip install -e ".[dev]"

# Verify installation
python -c "import fastapi; print(f'FastAPI {fastapi.__version__} installed')"
```

**Step 3: Frontend Setup**
```bash
# Navigate to frontend directory
cd frontend

# Install frontend dependencies
npm install

# Verify installation
npm list --depth=0

# Return to project root
cd ..
```

**Step 4: Database Initialization**
```bash
# Create data directory
mkdir -p data

# Initialize database schema
python -m backend.db.init_db

# Verify database created
ls -lh data/app.db
```

**Step 5: Environment Configuration**
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env  # or vim, code, etc.
```

**Required `.env` contents:**
```bash
# Database
DATABASE_PATH=./data/app.db

# YouTube API
YOUTUBE_API_KEY=your_api_key_here_from_google_cloud

# Authentication (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
SESSION_SECRET_KEY=generate_random_32_byte_key_here

# Admin password (will be hashed on first run)
ADMIN_PASSWORD=choose_secure_password_here

# Development settings
ALLOWED_HOSTS=localhost,127.0.0.1
DEBUG=true
```

**Step 6: Get YouTube API Key**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project: "YouTube Viewer Dev"
3. Enable YouTube Data API v3
4. Create API key in Credentials
5. Restrict key to YouTube Data API v3
6. Copy key to `.env` file

**Step 7: Verify Setup**
```bash
# Run backend tests
pytest

# Run frontend tests
cd frontend && npm test

# Check for any missing dependencies
python -m backend.main --help
```

## Development Commands

### Backend Development

**Start Development Server:**
```bash
# From project root
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# With verbose logging
uvicorn backend.main:app --reload --log-level debug

# Access at: http://localhost:8000
# API docs at: http://localhost:8000/docs
```

**Run Backend Tests:**
```bash
# All tests
pytest

# Unit tests only
pytest tests/backend/

# Specific test file
pytest tests/backend/services/test_viewing_session.py

# With coverage
pytest --cov=backend --cov-report=html

# TIER 1 safety tests (must pass 100%)
pytest tests/backend/safety/ -v

# Watch mode (re-run on file changes)
pytest-watch
```

**Database Operations:**
```bash
# Reset database (WARNING: deletes all data)
rm data/app.db
python -m backend.db.init_db

# Run database maintenance
python -m backend.db.maintenance

# Backup database
cp data/app.db data/app.db.backup

# View database contents
sqlite3 data/app.db
# Then run SQL: SELECT * FROM videos;
```

**Code Quality:**
```bash
# Run linter
ruff check backend/

# Auto-fix linting issues
ruff check backend/ --fix

# Format code
ruff format backend/

# Type checking
mypy backend/
```

### Frontend Development

**Start Frontend Dev Server:**
```bash
# From project root
cd frontend

# Start Vite dev server (with HMR)
npm run dev

# Access at: http://localhost:5173
# Proxies /api requests to backend at localhost:8000
```

**Build Frontend:**
```bash
# Production build
npm run build

# Output goes to: ../static/
# Verify build: ls -lh ../static/

# Preview production build
npm run preview
```

**Run Frontend Tests:**
```bash
# Unit tests
npm test

# Watch mode
npm run test:watch

# Coverage report
npm run test:coverage

# Specific test file
npm test -- grid.test.js
```

**Frontend Code Quality:**
```bash
# Lint JavaScript
npm run lint

# Auto-fix linting issues
npm run lint:fix

# Format code with Prettier
npm run format

# Check formatting
npm run format:check
```

### End-to-End Tests

**Run E2E Tests:**
```bash
# Install Playwright browsers (first time only)
npx playwright install

# Run all E2E tests
npm run test:e2e

# Run specific test
npx playwright test tests/e2e/specs/child-viewing-flow.spec.js

# Run with UI mode (visual debugging)
npx playwright test --ui

# Generate test report
npx playwright show-report
```

**E2E Test Requirements:**
- Both backend and frontend servers must be running
- Database must be populated with test data
- Use test fixtures: `tests/e2e/fixtures/test-data.json`

### Integrated Development Workflow

**Recommended Development Process:**

**Terminal 1 - Backend:**
```bash
source .venv/bin/activate
uvicorn backend.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - Tests (as needed):**
```bash
# Watch backend tests
pytest-watch

# OR watch frontend tests
cd frontend && npm run test:watch
```

**Access Points:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Backend serves templates at: http://localhost:8000/

## Environment Configuration

### Development `.env` File

**Complete `.env.example` template:**
```bash
# =============================================================================
# Safe YouTube Viewer for Kids - Development Environment Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# Database Configuration
# -----------------------------------------------------------------------------
DATABASE_PATH=./data/app.db
# For production: /opt/youtube-viewer/data/app.db

# -----------------------------------------------------------------------------
# YouTube API Configuration
# -----------------------------------------------------------------------------
# Get your API key from: https://console.cloud.google.com
YOUTUBE_API_KEY=your_youtube_api_key_here

# API quota limits (10,000 units/day for free tier)
YOUTUBE_QUOTA_DAILY_LIMIT=10000

# -----------------------------------------------------------------------------
# Authentication & Security
# -----------------------------------------------------------------------------
# Session secret (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
SESSION_SECRET_KEY=your_random_32_byte_secret_here

# Admin password (will be hashed with bcrypt on first run)
ADMIN_PASSWORD=choose_secure_password_here

# Session timeout (seconds) - 30 minutes default
SESSION_TIMEOUT=1800

# -----------------------------------------------------------------------------
# Server Configuration
# -----------------------------------------------------------------------------
# Allowed hosts (comma-separated)
ALLOWED_HOSTS=localhost,127.0.0.1

# Debug mode (set to false in production)
DEBUG=true

# Backend port
PORT=8000

# Frontend dev server port
VITE_PORT=5173

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
LOG_LEVEL=INFO
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

LOG_FILE=./logs/app.log
# For production: /var/log/youtube-viewer/app.log

# -----------------------------------------------------------------------------
# Content Settings (Optional - has defaults)
# -----------------------------------------------------------------------------
# Default daily time limit (minutes)
DEFAULT_DAILY_LIMIT_MINUTES=30

# Warning threshold (minutes before limit)
WARNING_THRESHOLD_MINUTES=5

# Grace video duration limit (seconds)
GRACE_VIDEO_MAX_DURATION=300

# Video grid size (number of videos)
VIDEO_GRID_SIZE=9

# -----------------------------------------------------------------------------
# Feature Flags (Optional)
# -----------------------------------------------------------------------------
# Enable maintenance mode
MAINTENANCE_MODE=false

# Enable detailed error messages (disable in production)
SHOW_DETAILED_ERRORS=true
```

### Environment-Specific Configuration

**Development (`.env`):**
```bash
DEBUG=true
LOG_LEVEL=DEBUG
SHOW_DETAILED_ERRORS=true
DATABASE_PATH=./data/app.db
ALLOWED_HOSTS=localhost,127.0.0.1
```

**Production (`.env.production`):**
```bash
DEBUG=false
LOG_LEVEL=INFO
SHOW_DETAILED_ERRORS=false
DATABASE_PATH=/opt/youtube-viewer/data/app.db
ALLOWED_HOSTS=yourdomain.com
SESSION_TIMEOUT=1800
```

**Testing (`.env.test`):**
```bash
DEBUG=true
LOG_LEVEL=ERROR
DATABASE_PATH=:memory:  # In-memory database for tests
YOUTUBE_API_KEY=test_mock_key
```

## Hot Reload & Development Experience

### Backend Hot Reload

FastAPI with Uvicorn's `--reload` flag provides automatic reloading:

**Triggers reload:**
- Any `.py` file changes in `backend/`
- Changes to `pyproject.toml`
- Changes to `.env` file (requires manual restart)

**Does NOT reload:**
- Template changes (requires manual refresh in browser)
- Database schema changes (requires migration)

**Reload Speed:** ~1-2 seconds

### Frontend Hot Module Replacement (HMR)

Vite provides instant HMR:

**Instant updates (no page reload):**
- JavaScript changes in `frontend/src/`
- CSS changes in any `.css` file
- Component updates

**Requires page reload:**
- Changes to `vite.config.js`
- Changes to `package.json`
- New dependencies added

**HMR Speed:** <100ms

## Common Development Tasks

### Adding a New API Endpoint

```bash
# 1. Add route to backend/routes.py
@app.get("/api/new-endpoint")
def new_endpoint():
    return {"message": "Hello"}

# 2. Add service function if needed (backend/services/)
def new_service_function():
    # Business logic here
    pass

# 3. Add database query if needed (backend/db/queries.py)
def new_database_query(conn):
    # SQL query here
    pass

# 4. Write tests (tests/backend/test_routes.py)
def test_new_endpoint(client):
    response = client.get("/api/new-endpoint")
    assert response.status_code == 200

# 5. Update API documentation in architecture.md
```

### Adding a New Frontend Component

```bash
# 1. Create component file
touch frontend/src/child/new-component.js

# 2. Write component code
# export function initNewComponent() { ... }

# 3. Import in main entry point
# import { initNewComponent } from './child/new-component.js';

# 4. Add styles
# Create: frontend/src/child/new-component.css

# 5. Write tests
# Create: frontend/tests/child/new-component.test.js

# 6. Test in browser at localhost:5173
```

### Running Full Integration Test

```bash
# Terminal 1: Start backend
uvicorn backend.main:app --reload

# Terminal 2: Start frontend
cd frontend && npm run dev

# Terminal 3: Run integration tests
pytest tests/integration/

# Terminal 4: Run E2E tests
npm run test:e2e
```

## Troubleshooting

### Backend Issues

**Issue: `ModuleNotFoundError: No module named 'backend'`**
```bash
# Solution: Reinstall in editable mode
uv pip install -e .
```

**Issue: `Database locked` error**
```bash
# Solution: Close any sqlite3 sessions
# Kill process: lsof data/app.db
# Or restart backend server
```

**Issue: `Port 8000 already in use`**
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn backend.main:app --reload --port 8001
```

### Frontend Issues

**Issue: `npm install` fails**
```bash
# Solution: Clear cache and reinstall
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

**Issue: Vite dev server not proxying API**
```bash
# Solution: Check vite.config.js proxy settings
# Ensure backend is running on port 8000
# Try: curl http://localhost:8000/api/health
```

**Issue: Static assets not loading**
```bash
# Solution: Rebuild frontend
npm run build

# Check static/ directory exists
ls -lh ../static/
```

### Common Errors

**`YOUTUBE_API_KEY not found`**
```bash
# Check .env file exists and has correct key
cat .env | grep YOUTUBE_API_KEY

# Verify environment variable loaded
python -c "import os; print(os.getenv('YOUTUBE_API_KEY'))"
```

**`Admin authentication fails`**
```bash
# Reset admin password
python -c "from backend.auth import hash_password; print(hash_password('newpassword'))"
# Copy hash to .env: ADMIN_PASSWORD_HASH=<hash>
```

---

