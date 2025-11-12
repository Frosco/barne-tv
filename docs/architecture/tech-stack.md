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
| **Backend Framework** | FastAPI | 0.118.0 | Web application framework | Modern, automatic threading for sync routes, excellent performance |
| **Package Manager** | uv | 0.1.11 | Python dependency management | Fast, modern alternative to pip as specified in PRD |
| **ASGI Server** | Uvicorn | 0.37.0 | Python application server | Standard for FastAPI, handles threading automatically |
| **HTTP Client** | requests | 2.32.5 | YouTube API requests | Mature, synchronous, simple to use |
| **YouTube API Client** | google-api-python-client | 2.184.0 | YouTube Data API v3 | Official Google client, naturally synchronous |
| **Template Engine** | Jinja2 | 3.1.6 | Server-side HTML rendering | Included with FastAPI, simple syntax, no build step needed |
| **Frontend Build Tool** | Vite | 7.1.9 | Dev server & production bundling | Zero-config, instant start, optimizes assets |
| **Frontend Language** | Vanilla JavaScript | ES2020+ | Client-side interactivity | No framework overhead, ES6 modules via Vite |
| **CSS Approach** | Pure CSS | CSS3 | Styling | No build step needed, custom properties for theming |
| **Database** | SQLite | 3.45.0 | Data persistence | Zero-config, file-based, perfect for single-instance |
| **Database Driver** | sqlite3 | Built-in | Synchronous SQLite access | Python standard library, simple and fast |
| **Web Server** | Nginx | 1.24.0 | Reverse proxy & static files | Industry standard, handles SSL, static assets |
| **Process Manager** | systemd | System default | Service supervision | Built into Linux, automatic restarts |
| **Password Hashing** | bcrypt | >=4.2.1 | Secure password storage | Modern Rust-based bcrypt implementation, faster and more secure |
| **SSL Certificates** | Let's Encrypt (Certbot) | 2.8.0 | HTTPS encryption | Free SSL, automatic renewal |
| **Frontend Testing** | Vitest | 3.2.4 | Frontend unit tests | Vite-native, fast, better DX than Jest |
| **DOM Testing** | happy-dom | 19.0.2 | Lightweight DOM for tests | 2x faster than jsdom |
| **Test Mocking** | pytest-mock | 3.15.1 | Mock external dependencies | Clean pytest integration |
| **Coverage Tool (Backend)** | pytest-cov | 7.0.0 | Backend code coverage | Standard pytest coverage plugin |
| **Coverage Tool (Frontend)** | @vitest/coverage-v8 | 3.2.4 | Frontend code coverage | Official Vitest coverage plugin |
| **E2E Testing** | Playwright | 1.40.0 | Critical user journeys | Cross-browser, reliable, visual testing |
| **Linter (Frontend)** | ESLint | 9.37.0 | Frontend code linting | Catch errors, enforce style |
| **Performance Testing** | pytest-benchmark | 5.1.0 | Backend performance tests | Accurate benchmarking with statistics |
| **Testing Framework** | pytest | 8.4.2 | Unit & integration tests | Standard Python testing |
| **HTTP Testing** | httpx | 0.27.0 | FastAPI TestClient dependency | Required by TestClient for API testing |

## Python Requirements (pyproject.toml)

```toml
[project]
name = "safe-youtube-viewer"
version = "1.0.0"
requires-python = ">=3.11,<3.12"

dependencies = [
    "fastapi==0.118.0",
    "uvicorn[standard]==0.37.0",
    "jinja2==3.1.6",
    "google-api-python-client==2.184.0",
    "requests==2.32.5",
    "bcrypt>=4.2.1",
    "python-multipart==0.0.20",
    "isodate==0.7.2",
]

[project.optional-dependencies]
dev = [
    "pytest==8.4.2",
    "pytest-mock==3.15.1",
    "pytest-cov==7.0.0",
    "pytest-benchmark==5.1.0",
    "responses==0.25.8",
    "httpx==0.27.0",
    "black==25.9.0",
    "ruff==0.14.0",
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
    "vite": "^7.1.9",
    "vitest": "^3.2.4",
    "happy-dom": "^19.0.2",
    "@vitest/coverage-v8": "^3.2.4",
    "@playwright/test": "^1.40.0",
    "eslint": "^9.37.0",
    "@eslint/js": "^9.37.0",
    "globals": "^16.4.0",
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

