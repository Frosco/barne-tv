# Tech Stack

This is the DEFINITIVE technology selection for the entire project. All development must use these exact versions.

## Cloud Infrastructure

**Provider:** Self-Hosted Hetzner VPS (Falkenstein, Germany)

**Server Specifications:**
- **Instance Type:** CX11 Cloud Server
- **vCPU:** 1 dedicated vCPU
- **RAM:** 2 GB
- **Storage:** 20 GB SSD
- **Bandwidth:** 20 TB/month included
- **Cost:** €4.51/month (€54/year)

**Backup Infrastructure:**
- **Local Backups:** On-server daily backups (7-day rotation)
- **Off-Site:** Manual weekly download via admin interface
- **Backup Storage:** ~7MB for 7 days of SQLite backups

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|----------|-----------|---------|---------|-----------|
| **Backend Language** | Python | 3.11.7 | Primary development language | Stable, excellent library ecosystem, type hints, matches PRD requirement |
| **Backend Framework** | FastAPI | 0.109.0 | Web application framework | Modern, automatic threading for sync routes, excellent performance |
| **Package Manager** | uv | 0.1.11 | Python dependency management | Fast, modern alternative to pip as specified in PRD |
| **ASGI Server** | Uvicorn | 0.27.0 | Python application server | Standard for FastAPI, handles threading automatically |
| **HTTP Client** | requests | 2.31.0 | YouTube API requests | Mature, synchronous, simple to use |
| **YouTube API Client** | google-api-python-client | 2.113.0 | YouTube Data API v3 | Official Google client, naturally synchronous |
| **Template Engine** | Jinja2 | 3.1.3 | Server-side HTML rendering | Included with FastAPI, simple syntax, no build step needed |
| **Frontend Build Tool** | Vite | 5.0.11 | Dev server & production bundling | Zero-config, instant start, optimizes assets |
| **Frontend Language** | Vanilla JavaScript | ES2020+ | Client-side interactivity | No framework overhead, ES6 modules via Vite |
| **CSS Approach** | Pure CSS | CSS3 | Styling | No build step needed, custom properties for theming |
| **Database** | SQLite | 3.45.0 | Data persistence | Zero-config, file-based, perfect for single-instance |
| **Database Driver** | sqlite3 | Built-in | Synchronous SQLite access | Python standard library, simple and fast |
| **Web Server** | Nginx | 1.24.0 | Reverse proxy & static files | Industry standard, handles SSL, static assets |
| **Process Manager** | systemd | System default | Service supervision | Built into Linux, automatic restarts |
| **Password Hashing** | passlib[bcrypt] | 1.7.4 | Secure password storage | Industry standard, bcrypt algorithm |
| **SSL Certificates** | Let's Encrypt (Certbot) | 2.8.0 | HTTPS encryption | Free SSL, automatic renewal |
| **Frontend Testing** | Vitest | 1.1.0 | Frontend unit tests | Vite-native, fast, better DX than Jest |
| **DOM Testing** | happy-dom | 12.10.3 | Lightweight DOM for tests | 2x faster than jsdom |
| **Test Mocking** | pytest-mock | 3.12.0 | Mock external dependencies | Clean pytest integration |
| **Coverage Tool** | pytest-cov | 4.1.0 | Code coverage measurement | Standard pytest coverage plugin |
| **E2E Testing** | Playwright | 1.40.0 | Critical user journeys | Cross-browser, reliable, visual testing |
| **Performance Testing** | pytest-benchmark | 4.0.0 | Backend performance tests | Accurate benchmarking with statistics |
| **Testing Framework** | pytest | 8.0.0 | Unit & integration tests | Standard Python testing |

## Python Requirements (pyproject.toml)

```toml
[project]
name = "safe-youtube-viewer"
version = "1.0.0"
requires-python = ">=3.11,<3.12"

dependencies = [
    "fastapi==0.109.0",
    "uvicorn[standard]==0.27.0",
    "jinja2==3.1.3",
    "google-api-python-client==2.113.0",
    "requests==2.31.0",
    "passlib[bcrypt]==1.7.4",
    "python-multipart==0.0.6",
    "isodate==0.6.1",
]

[project.optional-dependencies]
dev = [
    "pytest==8.0.0",
    "pytest-mock==3.12.0",
    "pytest-cov==4.1.0",
    "pytest-benchmark==4.0.0",
    "responses==0.24.1",
    "black==24.1.0",
    "ruff==0.1.14",
]
```

## Frontend Package (package.json)

```json
{
  "name": "safe-youtube-viewer-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "lint": "eslint frontend/src/**/*.js",
    "lint:fix": "eslint frontend/src/**/*.js --fix"
  },
  "devDependencies": {
    "vite": "^5.0.11",
    "vitest": "^1.1.0",
    "happy-dom": "^12.10.3",
    "@playwright/test": "^1.40.0",
    "eslint": "^8.56.0",
    "prettier": "^3.1.1"
  }
}
```

## System Dependencies (apt packages)

```bash
# Ubuntu 22.04 LTS (Jammy)
nginx
python3.11
python3.11-dev
sqlite3
certbot
python3-certbot-nginx
nodejs (v20 LTS)
```

---

