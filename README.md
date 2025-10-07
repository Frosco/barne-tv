# Safe YouTube Viewer for Kids

A web application designed for children ages 2-6 to safely watch YouTube videos from parent-approved channels and playlists. The application eliminates inappropriate content exposure through complete parental control while enabling independent video selection through a visual, child-friendly interface requiring no reading ability.

## Features

- **Parent-Controlled Content**: Only videos from approved YouTube channels/playlists
- **Daily Time Limits**: Configurable viewing time with gentle wind-down warnings
- **Child-Friendly Interface**: Visual grid with no reading required
- **Grace Video Option**: One more short video when time limit reached
- **Watch History**: Parent can review what was watched and manually replay videos
- **Banned Videos**: Parent can block specific videos from reappearing
- **Self-Hosted**: Complete control over your data and deployment

## Target Audience

- **Norwegian family** with children ages 2-6
- **Self-hosted** on Hetzner VPS or similar
- **Privacy-focused** with no third-party data sharing

## Prerequisites

Before installing, ensure you have:

- **Python 3.11.7** (exact version required)
- **uv 0.1.11** package manager
- **Node.js 20.x LTS** (for frontend in future stories)
- **SQLite 3.45.0+** (included with Python)
- **YouTube Data API v3 key** (from Google Cloud Console)

### Getting Python 3.11.7

```bash
# Using mise (recommended)
mise install python@3.11.7
mise use python@3.11.7

# Or using pyenv
pyenv install 3.11.7
pyenv local 3.11.7
```

### Getting uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
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

### 4. Initialize Database

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

## Running Locally

### Start Backend Server

```bash
# Start FastAPI server with auto-reload
uv run uvicorn backend.main:app --reload

# Server will start at http://localhost:8000
```

### Verify Health Check

```bash
# Test that server is running
curl http://localhost:8000/health

# Expected output: {"status":"ok"}
```

### Access Application

- **Child Interface**: http://localhost:8000/ (not yet implemented)
- **Admin Interface**: http://localhost:8000/admin (not yet implemented)
- **Health Check**: http://localhost:8000/health

## Running Tests

```bash
# Run all tests with verbose output
uv run pytest tests/backend/ -v

# Run tests with coverage report
uv run pytest tests/backend/ -v --cov=backend --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Development Workflow

### Code Formatting

```bash
# Format all Python files with Black
uv run black .

# Check formatting without making changes
uv run black --check .
```

### Linting

```bash
# Run Ruff linter
uv run ruff check .

# Auto-fix issues where possible
uv run ruff check --fix .
```

### Database Management

```bash
# Initialize/reset database
uv run python backend/db/init_db.py <new_password>

# Run maintenance tasks
uv run python backend/db/maintenance.py

# View database schema
sqlite3 data/app.db .schema
```

## Project Structure

```
barne-tv/
├── backend/                    # Python FastAPI application
│   ├── services/              # Business logic services
│   │   ├── viewing_session.py    # Video selection + daily limits
│   │   └── content_source.py     # YouTube fetching + source management
│   ├── db/                    # Database layer
│   │   ├── schema.sql            # Complete DDL
│   │   ├── init_db.py            # Database initialization
│   │   ├── queries.py            # SQL functions (sync)
│   │   └── maintenance.py        # Cleanup operations
│   ├── main.py                # FastAPI app entry point
│   ├── config.py              # Configuration management
│   ├── auth.py                # Session management
│   ├── exceptions.py          # Custom exception classes
│   └── routes.py              # API routes
├── frontend/                   # Vite + Vanilla JS (future)
├── static/                     # Built frontend assets (future)
├── tests/                      # Test files (future)
├── docs/                       # Documentation
├── .env                        # Environment variables (not in git)
├── .env.example                # Environment template
├── pyproject.toml              # Python dependencies
└── README.md                   # This file
```

## Technology Stack

**Backend:**
- Python 3.11.7
- FastAPI 0.109.0
- Uvicorn 0.27.0
- SQLite 3.45.0

**Dependencies:**
- google-api-python-client 2.113.0
- passlib[bcrypt] 1.7.4
- requests 2.31.0

**Development:**
- uv 0.1.11 (package manager)
- pytest 8.0.0 (testing)
- black 24.1.0 (formatting)
- ruff 0.1.14 (linting)

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `/opt/youtube-viewer/data/app.db` | SQLite database location |
| `YOUTUBE_API_KEY` | Required | YouTube Data API v3 key |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hostnames |
| `ENVIRONMENT` | `development` | `development` or `production` |

### Database Settings

Stored in `settings` table:
- `daily_limit_minutes`: Default 30
- `grid_size`: Default 9 videos
- `audio_enabled`: Default true
- `admin_password_hash`: Bcrypt hash

## Security

- **Password Security**: Admin passwords hashed with bcrypt
- **SQL Injection**: All queries use parameterized placeholders
- **Input Validation**: All parent inputs validated and sanitized
- **No Secrets in Git**: `.env` file excluded from version control

## Architecture

See detailed documentation in `docs/architecture/`:
- `architecture.md` - Complete system architecture
- `coding-standards.md` - Mandatory coding rules
- `database-schema.md` - Database design
- `tech-stack.md` - Technology decisions

## Roadmap

**Story 1.1: Foundation** (Current)
- ✅ Project structure
- ✅ Database schema
- ✅ FastAPI skeleton
- ✅ Health check endpoint

**Story 1.2: Testing Infrastructure** (Next)
- Test framework setup
- Safety rule tests
- CI/CD pipeline

**Story 1.3: Content Source Management**
- YouTube API integration
- Add/remove channels
- Fetch and cache videos

**Story 1.4+: Additional Features**
- Child video grid interface
- Video playback
- Time limit tracking
- Admin dashboard

## Contributing

This is a personal project for a Norwegian family. Not accepting external contributions at this time.

## License

See LICENSE file for details.

## Support

For issues or questions, see the documentation in `docs/` or create an issue in the repository.

---

**Built with Claude Code** | Version 1.0.0
