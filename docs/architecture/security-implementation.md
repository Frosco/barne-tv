# Security Implementation

## Overview

Security in this application operates on two levels: **child safety** (preventing inappropriate content exposure) and **system security** (protecting against attacks and unauthorized access). Given the self-hosted, single-family deployment model, security measures are pragmatic while maintaining strong protections where critical.

## Authentication & Authorization

### Admin Authentication

**Implementation: Session-based authentication with bcrypt password hashing**

```python
# backend/auth.py
from passlib.hash import bcrypt
from datetime import datetime, timezone, timedelta
import secrets

# In-memory session store (acceptable for single-instance deployment)
sessions = {}  # session_id -> {created_at, expires_at}

def hash_password(password: str) -> str:
    """Hash password using bcrypt with automatic salt generation."""
    return bcrypt.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.verify(password, hashed)

def create_session() -> str:
    """Create new admin session, expires in 24 hours."""
    session_id = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    sessions[session_id] = {
        'created_at': now,
        'expires_at': now + timedelta(hours=24)
    }
    return session_id

def validate_session(session_id: str) -> bool:
    """Validate session exists and hasn't expired."""
    if session_id not in sessions:
        return False
    
    session = sessions[session_id]
    if datetime.now(timezone.utc) > session['expires_at']:
        del sessions[session_id]
        return False
    
    return True

def require_auth(request: Request):
    """FastAPI dependency for protected routes."""
    session_id = request.cookies.get('session_id')
    if not session_id or not validate_session(session_id):
        raise HTTPException(status_code=401, detail="Unauthorized")
```

**Session Cookie Configuration:**
```python
# backend/routes.py
@app.post("/admin/login")
async def admin_login(request: Request, password: str):
    stored_hash = db.get_setting('admin_password_hash')
    
    if not verify_password(password, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    session_id = create_session()
    response = JSONResponse({"success": True, "redirect": "/admin/dashboard"})
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,      # Prevent JavaScript access
        secure=True,        # HTTPS only
        samesite="lax",     # CSRF protection
        max_age=86400       # 24 hours
    )
    return response
```

**Password Requirements:**
- Minimum 12 characters (enforced during initial setup)
- Bcrypt hashing with automatic salt
- Password stored in `settings` table as bcrypt hash
- No password reset mechanism (self-hosted, admin uses environment variable to reset)

### Child Interface Authorization

**No authentication by design** - child interface is completely open. Security is implemented through:
- Content filtering (banned videos, unavailable videos)
- Time limits (UTC-based, reset at midnight)
- No admin access without password

### Secret Rotation

**Admin Password Rotation:**
```bash
# 1. Generate new password hash
python3 << EOF
from passlib.hash import bcrypt
import json
new_hash = bcrypt.hash("new_password_here")
print(json.dumps(new_hash))  # Proper JSON encoding
EOF

# 2. Update database directly
sqlite3 /opt/youtube-viewer/data/app.db << EOF
UPDATE settings 
SET value = '"$2b$12$..."', 
    updated_at = datetime('now') 
WHERE key = 'admin_password_hash';
EOF

# 3. Restart application to clear sessions
sudo systemctl restart youtube-viewer
```

**YouTube API Key Rotation:**
1. Generate new key in Google Cloud Console
2. Update `/opt/youtube-viewer/.env`
3. Restart application: `sudo systemctl restart youtube-viewer`
4. Verify new key works before deleting old one

## Input Validation

### FastAPI Pydantic Models

All API inputs validated using Pydantic models with strict types:

```python
# backend/models/requests.py
from pydantic import BaseModel, Field, validator
from typing import Literal

class AddSourceRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=200)
    
    @validator('input')
    def validate_youtube_input(cls, v):
        """Ensure input is valid YouTube URL or ID."""
        v = v.strip()
        
        # Block obviously malicious inputs
        if any(char in v for char in ['<', '>', ';', '&', '|', '`', '$', '(', ')']):
            raise ValueError('Invalid characters in input')
        
        # Must be YouTube URL or reasonable ID format
        if not (
            'youtube.com' in v or 
            'youtu.be' in v or
            (len(v) >= 10 and len(v) <= 50 and v.replace('-', '').replace('_', '').isalnum())
        ):
            raise ValueError('Not a valid YouTube URL or ID')
        
        return v

class WatchVideoRequest(BaseModel):
    videoId: str = Field(..., min_length=11, max_length=11, regex=r'^[a-zA-Z0-9_-]{11}$')
    completed: bool
    durationWatchedSeconds: int = Field(..., ge=0, le=7200)  # Max 2 hours

class BanVideoRequest(BaseModel):
    videoId: str = Field(..., min_length=11, max_length=11, regex=r'^[a-zA-Z0-9_-]{11}$')

class UpdateSettingsRequest(BaseModel):
    daily_limit_minutes: int = Field(None, ge=5, le=180)  # 5 min to 3 hours
    grid_size: int = Field(None, ge=4, le=15)
    audio_enabled: bool = None
```

### SQL Injection Prevention

**All database operations use parameterized queries** - enforced by coding standards:

```python
# backend/db/queries.py

# ✅ CORRECT - Always use placeholders
def get_video_by_video_id(video_id: str) -> dict:
    query = "SELECT * FROM videos WHERE video_id = ?"
    with get_connection() as conn:
        return conn.execute(query, (video_id,)).fetchone()

# ❌ NEVER do this - string formatting forbidden
def bad_query(video_id: str):
    query = f"SELECT * FROM videos WHERE video_id = '{video_id}'"  # SQL injection risk!
```

### Frontend XSS Prevention

**XSS Prevention in Vanilla JavaScript:**
```javascript
// frontend/src/child/grid.js

// ❌ WRONG - XSS vulnerability
function createCard(video) {
  card.innerHTML = `<h3>${video.title}</h3>`;  // Dangerous if title contains HTML!
}

// ✅ CORRECT - Safe text insertion
function createCard(video) {
  const title = document.createElement('h3');
  title.textContent = video.title;  // Automatically escaped by browser
  card.appendChild(title);
}

// ✅ CORRECT - Safe attribute insertion
function createThumbnail(video) {
  const img = document.createElement('img');
  img.src = video.thumbnailUrl;  // Safe - browser validates URL
  img.alt = video.title;          // Safe - textContent used
  return img;
}
```

**Video ID Validation:**
```javascript
// frontend/src/shared/utils.js

/**
 * Validate YouTube video ID format
 * @param {string} videoId - Video ID to validate
 * @returns {boolean} - True if valid
 */
function isValidVideoId(videoId) {
  if (!videoId || typeof videoId !== 'string') return false;
  
  // YouTube video IDs are exactly 11 characters: alphanumeric, dash, underscore
  return /^[a-zA-Z0-9_-]{11}$/.test(videoId);
}

/**
 * Get video ID from URL params with validation
 * @returns {string|null} - Validated video ID or null
 */
function getVideoIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const videoId = params.get('videoId');
  
  if (!isValidVideoId(videoId)) {
    console.error('Invalid video ID format');
    return null;
  }
  
  return videoId;
}
```

**DOM Manipulation Safety:**
```javascript
// frontend/src/child/grid.js

// Always sanitize any data that could come from external sources
function renderGrid(videos) {
  const container = document.querySelector('[data-grid]');
  
  // Clear existing content safely
  container.textContent = '';
  
  videos.forEach(video => {
    // Validate video object structure
    if (!video || !video.videoId || !isValidVideoId(video.videoId)) {
      console.warn('Invalid video object, skipping');
      return;
    }
    
    const card = createVideoCard(video);
    container.appendChild(card);
  });
}
```

### Error Message Security

**Public API Errors (Child Interface):**
```python
# backend/routes.py

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Log full error internally
    logger.exception(f"Unexpected error: {exc}")
    
    # Generic message for child interface
    if not request.url.path.startswith('/admin'):
        return JSONResponse(
            status_code=500,
            content={"error": "Noe gikk galt"}  # "Something went wrong"
        )
    
    # Slightly more detail for admin (but still no sensitive data)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal error", "message": "En feil oppstod"}
    )

# ❌ NEVER expose:
# - Database connection strings
# - API keys or credentials
# - Internal file paths
# - Stack traces in production
# - SQL query details
```

**Admin API Errors (Parent Interface):**
```python
# More detail acceptable for admin, but still sanitized

@app.exception_handler(YouTubeAPIError)
async def youtube_api_handler(request: Request, exc: YouTubeAPIError):
    return JSONResponse(
        status_code=503,
        content={
            "error": "YouTube API Error",
            "message": exc.message,  # e.g., "YouTube API kvote overskredet"
            "details": exc.details   # Safe metadata only, never API keys
        }
    )
```

## Environment Variable Security

### YouTube API Key Protection

```python
# backend/config.py
import os
import logging

logger = logging.getLogger(__name__)

# Load critical environment variables
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
DATABASE_PATH = os.getenv('DATABASE_PATH', '/opt/youtube-viewer/data/app.db')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Validate required variables
if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY environment variable must be set")

# Log configuration (NEVER log the full API key)
logger.info(f"YouTube API initialized with key: {YOUTUBE_API_KEY[:8]}...")
logger.info(f"Database path: {DATABASE_PATH}")
logger.info(f"Allowed hosts: {ALLOWED_HOSTS}")
```

**Environment File Setup:**
```bash
# /opt/youtube-viewer/.env
# Permissions: 600 (read/write for owner only)

YOUTUBE_API_KEY=AIzaSyD...  # Full key here
DATABASE_PATH=/opt/youtube-viewer/data/app.db
ALLOWED_HOSTS=youtube-viewer.yourdomain.com

# Development environment (.env.local)
YOUTUBE_API_KEY=AIzaSyD...
DATABASE_PATH=./data/test.db
ALLOWED_HOSTS=localhost,127.0.0.1
```

**File Permissions:**
```bash
# Restrict environment file access
sudo chown youtube-viewer:youtube-viewer /opt/youtube-viewer/.env
sudo chmod 600 /opt/youtube-viewer/.env

# Verify permissions
ls -la /opt/youtube-viewer/.env
# Should show: -rw------- 1 youtube-viewer youtube-viewer
```

**Git Security:**
```gitignore
# .gitignore
.env
.env.local
.env.production
*.db
logs/*.log
backups/*.db
```

## HTTPS/TLS Configuration

### Nginx SSL Termination

```nginx
# /etc/nginx/sites-available/youtube-viewer
server {
    listen 80;
    server_name youtube-viewer.yourdomain.com;
    
    # Force HTTPS redirect
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name youtube-viewer.yourdomain.com;
    
    # SSL Certificate (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/youtube-viewer.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/youtube-viewer.yourdomain.com/privkey.pem;
    
    # Strong SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    
    # HSTS (31536000 seconds = 1 year)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Security Headers (see next section)
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static {
        alias /opt/youtube-viewer/static;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

**Certificate Management:**
- Let's Encrypt certificates via Certbot
- Automatic renewal via systemd timer
- 90-day validity with 30-day renewal window

```bash
# Certbot installation and setup
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d youtube-viewer.yourdomain.com

# Automatic renewal systemd timer (enabled by certbot)
sudo systemctl status certbot.timer

# Manual renewal test
sudo certbot renew --dry-run
```

## Security Headers

**Nginx security headers configuration:**

```nginx
# /etc/nginx/sites-available/youtube-viewer
# Add to server block for HTTPS

# Prevent clickjacking
add_header X-Frame-Options "SAMEORIGIN" always;

# Prevent MIME type sniffing
add_header X-Content-Type-Options "nosniff" always;

# Enable XSS protection (legacy browsers)
add_header X-XSS-Protection "1; mode=block" always;

# Content Security Policy (CSP) - Production
# NOTE: In development with Vite dev server, CSP may need to be relaxed
add_header Content-Security-Policy "
    default-src 'self';
    script-src 'self' https://www.youtube.com https://s.ytimg.com;
    style-src 'self' 'unsafe-inline';
    img-src 'self' https://i.ytimg.com data:;
    frame-src https://www.youtube.com;
    media-src 'self' https://www.youtube.com;
    connect-src 'self';
    font-src 'self';
    object-src 'none';
    base-uri 'self';
    form-action 'self';
    frame-ancestors 'self';
" always;

# Referrer Policy
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# Permissions Policy (formerly Feature Policy)
add_header Permissions-Policy "
    geolocation=(),
    microphone=(),
    camera=(),
    payment=(),
    usb=(),
    magnetometer=(),
    gyroscope=(),
    accelerometer=()
" always;

# Prevent search engine indexing (privacy + child safety)
add_header X-Robots-Tag "noindex, nofollow" always;
```

**Development CSP Note:**

If running Vite dev server locally (not for production), you may need to temporarily relax CSP:

```nginx
# Development location block (NOT for production)
location /dev {
    # More permissive CSP for Vite HMR
    add_header Content-Security-Policy "
        default-src 'self';
        script-src 'self' 'unsafe-eval';  # Vite needs eval
        style-src 'self' 'unsafe-inline';
        connect-src 'self' ws: wss:;      # WebSocket for HMR
    " always;
    
    proxy_pass http://127.0.0.1:5173;  # Vite dev server
}
```

**FastAPI Security Middleware:**

```python
# backend/main.py
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from backend.config import ALLOWED_HOSTS

app = FastAPI()

# Trusted host protection (environment-specific)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS  # From environment variable
)

# NOTE: CORS middleware not needed for this monolith architecture
# Frontend is served from same domain via Nginx, no cross-origin requests

# Custom security headers middleware (redundant with Nginx but defense in depth)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

## SEO and Crawler Prevention

**robots.txt** (served by Nginx):
```text
# /opt/youtube-viewer/static/robots.txt
User-agent: *
Disallow: /
```

**Nginx configuration to serve robots.txt:**
```nginx
location /robots.txt {
    alias /opt/youtube-viewer/static/robots.txt;
}
```

**Meta tags in all HTML templates:**
```html
<!-- frontend/templates/base.html -->
<!DOCTYPE html>
<html lang="no">
<head>
    <meta name="robots" content="noindex, nofollow">
    <meta name="googlebot" content="noindex, nofollow">
    <!-- rest of head -->
</head>
```

**Rationale:** Application should not be indexed by search engines for privacy and child safety reasons. This is a private family application, not a public service.

## Data Protection

### Database Security

**SQLite File Permissions:**
```bash
# Restrict database file access to application user only
sudo chown youtube-viewer:youtube-viewer /opt/youtube-viewer/data/app.db
sudo chmod 600 /opt/youtube-viewer/data/app.db

# Verify permissions
ls -la /opt/youtube-viewer/data/app.db
# Should show: -rw------- 1 youtube-viewer youtube-viewer
```

**Sensitive Data Handling:**

| Data Type | Storage | Protection |
|-----------|---------|------------|
| Admin Password | settings table | bcrypt hash (cost factor 12) |
| Session IDs | In-memory | 32-byte random tokens, 24-hour expiry |
| Watch History | watch_history table | No PII, denormalized video titles only |
| Video Metadata | videos table | Public YouTube data, no encryption needed |
| API Keys | Environment variables | File permissions 600, not in git |

**No encryption at rest** - Acceptable for this deployment because:
- Self-hosted single-family deployment
- No PII or sensitive user data stored
- Admin password is bcrypt hashed
- Physical security of server is under parent control
- If encryption at rest required, use LUKS full disk encryption at OS level

### Backup Security

```bash
# scripts/backup.sh
#!/bin/bash
# Database backups retain same permissions as source

BACKUP_DIR="/opt/youtube-viewer/backups"
DB_PATH="/opt/youtube-viewer/data/app.db"
BACKUP_FILE="$BACKUP_DIR/app-$(date +%Y%m%d-%H%M%S).db"

# Create backup
cp "$DB_PATH" "$BACKUP_FILE"
chmod 600 "$BACKUP_FILE"
chown youtube-viewer:youtube-viewer "$BACKUP_FILE"

# Rotate backups (keep 7 days)
find "$BACKUP_DIR" -name "app-*.db" -mtime +7 -delete

echo "Backup created: $BACKUP_FILE"
```

**Backup Directory Permissions:**
```bash
sudo mkdir -p /opt/youtube-viewer/backups
sudo chown youtube-viewer:youtube-viewer /opt/youtube-viewer/backups
sudo chmod 700 /opt/youtube-viewer/backups
```

**Offsite Backup (Optional):**

If parent wants offsite backups:
```bash
# Encrypt backup before downloading
gpg --symmetric --cipher-algo AES256 app-backup.db

# This creates app-backup.db.gpg which can be safely stored offsite
# Decrypt with: gpg --decrypt app-backup.db.gpg > app-backup.db
```

## API Security

### Rate Limiting

**Nginx rate limiting configuration:**

```nginx
# Define rate limit zones in http block
http {
    # Admin endpoints - stricter limits (prevent brute force)
    limit_req_zone $binary_remote_addr zone=admin:10m rate=10r/m;
    
    # Child endpoints - generous limits (normal usage)
    limit_req_zone $binary_remote_addr zone=child:10m rate=60r/m;
    
    # General API endpoints
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;
}

server {
    # Admin routes
    location /admin {
        limit_req zone=admin burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }
    
    # Child API routes
    location /api/videos {
        limit_req zone=child burst=10 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }
    
    # General API routes
    location /api {
        limit_req zone=api burst=15 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }
}
```

**Rate Limit Rationale:**

| Endpoint | Rate | Rationale |
|----------|------|-----------|
| `/admin/*` | 10 req/min | Prevents brute force password attacks. Admin actions are infrequent. |
| `/api/videos` | 60 req/min | Generous for child usage. Typical 30-min session: grid load (1) + watch logs (~5) + new grids (~5) = ~11 requests. 60/min allows for rapid clicking without blocking. |
| `/api/*` (other) | 30 req/min | Covers limit checks, video unavailable reports, etc. |

**Burst allows:** Temporary spikes (e.g., child clicks multiple videos quickly) without blocking.

### CSRF Protection

**SameSite cookie attribute prevents CSRF attacks:**
- Admin session cookie uses `SameSite=Lax`
- Protects against cross-site request forgery
- Works without additional CSRF tokens (acceptable for this simple deployment)

**Why this is sufficient:**
- Single-origin application (no cross-origin requests needed)
- Session cookie is HttpOnly (can't be read by JavaScript)
- Modern browsers enforce SameSite by default

**For future enhancements requiring CSRF tokens:**
```python
# If needed (currently not required)
from fastapi_csrf_protect import CsrfProtect

@app.post("/admin/sources")
async def add_source(request: Request, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    # ... rest of implementation
```

## Dependency Security

### Dependency Scanning

**Using pip-audit for Python dependencies:**

```bash
# Install pip-audit
pip install pip-audit

# Scan for vulnerabilities
pip-audit

# Can integrate into CI/CD
pip-audit --exit-code-on-vulnerability
```

**Manual scan command:**
```bash
# Run in project directory
cd /opt/youtube-viewer/app
uv run pip-audit
```

**Automated dependency updates:**
```yaml
# .github/dependabot.yml (if using GitHub)
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
```

### Pinning Dependencies

**All dependencies pinned to specific versions in pyproject.toml:**
```toml
[project]
dependencies = [
    "fastapi==0.109.0",                    # Exact version, not >=
    "uvicorn[standard]==0.27.0",
    "jinja2==3.1.3",
    "google-api-python-client==2.113.0",
    "passlib[bcrypt]==1.7.4",
    "requests==2.31.0",
    "python-multipart==0.0.6",
    "isodate==0.6.1",
]
```

**Update process:**
1. Check for security advisories monthly: `pip-audit`
2. Review changelogs for breaking changes
3. Test updates in development environment first
4. Update one dependency at a time
5. Run full test suite (pytest) before deploying
6. Document any issues or migration steps

### Known Vulnerabilities Policy

**Response to security advisories:**
- **Critical (CVSS 9.0-10.0):** Patch within 24 hours
- **High (CVSS 7.0-8.9):** Patch within 1 week
- **Medium (CVSS 4.0-6.9):** Patch within 1 month
- **Low (CVSS 0.1-3.9):** Patch during next planned update

**Security advisory sources:**
- GitHub Security Advisories
- pip-audit output
- Python security mailing lists
- Dependency project changelogs

## Infrastructure Security

### Server Hardening

**Basic server security checklist:**

```bash
# 1. Firewall configuration (UFW)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirects to HTTPS)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Verify firewall status
sudo ufw status verbose

# 2. Disable root SSH login
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# 3. Automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades

# 4. Fail2ban for SSH brute force protection
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Verify fail2ban is running
sudo fail2ban-client status sshd
```

### Application User Isolation

```bash
# Create dedicated application user (no login shell)
sudo useradd -r -s /bin/false youtube-viewer

# Application directory ownership
sudo chown -R youtube-viewer:youtube-viewer /opt/youtube-viewer
sudo chmod 755 /opt/youtube-viewer

# Systemd service runs as youtube-viewer user
# See scripts/systemd/youtube-viewer.service:
# User=youtube-viewer
# Group=youtube-viewer
# NoNewPrivileges=true
# PrivateTmp=true
```

**Systemd Security Hardening:**
```ini
# scripts/systemd/youtube-viewer.service
[Service]
User=youtube-viewer
Group=youtube-viewer

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/youtube-viewer/data /opt/youtube-viewer/logs
```

### Log Security

**Log file permissions and rotation:**

```bash
# Log directory permissions
sudo mkdir -p /opt/youtube-viewer/logs
sudo chown -R youtube-viewer:youtube-viewer /opt/youtube-viewer/logs
sudo chmod 755 /opt/youtube-viewer/logs

# Individual log files (restrictive)
sudo chmod 640 /opt/youtube-viewer/logs/*.log
```

**Logrotate configuration:**
```bash
# /etc/logrotate.d/youtube-viewer
/opt/youtube-viewer/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 youtube-viewer youtube-viewer
    sharedscripts
    postrotate
        systemctl reload youtube-viewer > /dev/null 2>&1 || true
    endscript
}
```

**Sensitive data in logs - What NOT to log:**
- ❌ Passwords (plain or hashed)
- ❌ Session IDs (full tokens)
- ❌ YouTube API keys
- ❌ SQL query parameters that might contain sensitive data
- ✅ Video IDs (public data)
- ✅ Video titles (public data)
- ✅ Error messages (sanitized)
- ✅ Request paths and methods
- ✅ Timestamps and IP addresses

**Logging configuration:**
```python
# backend/main.py
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/youtube-viewer/logs/app.log'),
    ]
)

logger = logging.getLogger("youtube-viewer")

# Sanitize sensitive data in logs
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Log request (safe info only)
    logger.info(f"{request.method} {request.url.path} from {request.client.host}")
    
    # Never log request body that might contain passwords
    if request.url.path != "/admin/login":
        # Safe to log for other endpoints
        pass
    
    response = await call_next(request)
    return response
```

## Security Monitoring

### Application Monitoring

**Security event logging:**

```python
# backend/main.py
import logging

logger = logging.getLogger("youtube-viewer")

# Log security-relevant events
@app.middleware("http")
async def log_security_events(request: Request, call_next):
    response = await call_next(request)
    
    # Log failed authentication attempts
    if request.url.path == "/admin/login" and response.status_code == 401:
        logger.warning(
            f"Failed login attempt from {request.client.host}",
            extra={"ip": request.client.host, "path": request.url.path}
        )
    
    # Log suspicious request patterns
    if response.status_code == 429:  # Rate limit hit
        logger.warning(
            f"Rate limit exceeded from {request.client.host}",
            extra={"ip": request.client.host, "path": request.url.path}
        )
    
    return response
```

### Security Monitoring Checklist

**Weekly Review:**
- [ ] Check `/opt/youtube-viewer/logs/app.log` for errors and warnings
- [ ] Review nginx access logs for unusual patterns:
  ```bash
  sudo tail -100 /var/log/nginx/access.log
  sudo tail -100 /var/log/nginx/error.log
  ```
- [ ] Check fail2ban status and banned IPs:
  ```bash
  sudo fail2ban-client status sshd
  sudo fail2ban-client status nginx-limit-req  # If configured
  ```
- [ ] Verify disk space isn't filling up:
  ```bash
  df -h
  ```

**Monthly Review:**
- [ ] Check for suspicious login attempts:
  ```bash
  sudo grep "Failed login" /opt/youtube-viewer/logs/app.log | tail -50
  ```
- [ ] Review fail2ban banned IPs and durations
- [ ] Run dependency security scan:
  ```bash
  cd /opt/youtube-viewer/app && uv run pip-audit
  ```
- [ ] Review SSL certificate expiry:
  ```bash
  sudo certbot certificates
  ```
- [ ] Check for OS security updates:
  ```bash
  sudo apt update && apt list --upgradable
  ```

**Quarterly:**
- [ ] Full dependency update review (test in dev first)
- [ ] Review and update firewall rules if needed
- [ ] Test backup restoration procedure
- [ ] Review application logs for patterns or recurring issues
- [ ] Check nginx log for unusual traffic patterns

**Commands for monitoring:**
```bash
# Check application status
sudo systemctl status youtube-viewer

# View recent application logs
sudo journalctl -u youtube-viewer -n 100

# Check nginx error logs
sudo tail -f /var/log/nginx/error.log

# View fail2ban log
sudo tail -f /var/log/fail2ban.log

# Check open connections
sudo netstat -tulpn | grep :8000
```

## Security Testing

Security testing is comprehensive and documented in the **Test Strategy** section. Key security tests include:

**TIER 1 Safety Tests (100% coverage required):**
- SQL injection prevention - `tests/backend/safety/test_tier1_safety_rules.py::test_rule6_*`
- XSS attempt blocking - `tests/backend/security/test_security.py::test_xss_prevention`
- Password hashing verification - `tests/backend/test_auth.py`
- Input validation - `tests/backend/services/test_content_source.py`

**Security Test Suite:**
```bash
# Run all security tests
cd /opt/youtube-viewer/app
uv run pytest tests/backend/security/ -v

# Run TIER 1 safety tests (must pass 100%)
uv run pytest tests/backend/safety/ -m tier1 -v

# Run with coverage
uv run pytest tests/backend/ --cov=backend --cov-report=html
```

**Security tests verify:**
- SQL injection attempts are blocked
- XSS payloads are sanitized
- Bcrypt password hashing works correctly
- Session validation works as expected
- Input validation catches malicious inputs
- Admin endpoints require authentication
- Rate limiting prevents abuse

**See Test Strategy section for:**
- Complete test organization
- Security test examples
- Coverage requirements
- CI/CD integration

## Incident Response

**Security incident procedure:**

1. **Detect:** Monitor logs for suspicious activity
   - Failed login attempts spike
   - Rate limit triggers
   - Unexpected errors
   - Database integrity issues

2. **Assess:** Determine severity and scope
   - Is this active exploitation or scanning?
   - Is data compromised?
   - Is availability affected?
   - Is this a false positive?

3. **Contain:**
   - Take application offline if critical:
     ```bash
     sudo systemctl stop youtube-viewer
     ```
   - Block malicious IPs at firewall level:
     ```bash
     sudo ufw deny from <attacker-ip>
     ```
   - Revoke compromised credentials

4. **Investigate:** Review logs to understand breach
   ```bash
   # Application logs
   sudo grep "ERROR\|WARNING" /opt/youtube-viewer/logs/app.log
   
   # Nginx logs
   sudo grep "<attacker-ip>" /var/log/nginx/access.log
   
   # System auth logs
   sudo grep "Failed password" /var/log/auth.log
   ```

5. **Remediate:**
   - Patch vulnerabilities
   - Reset admin password if compromised (see Secret Rotation section)
   - Clear all sessions:
     ```bash
     sudo systemctl restart youtube-viewer
     ```
   - Update firewall rules
   - Apply security patches

6. **Recover:**
   - Restore from backup if needed:
     ```bash
     sudo cp /opt/youtube-viewer/backups/app-20250107.db /opt/youtube-viewer/data/app.db
     sudo chown youtube-viewer:youtube-viewer /opt/youtube-viewer/data/app.db
     sudo chmod 600 /opt/youtube-viewer/data/app.db
     ```
   - Restart services:
     ```bash
     sudo systemctl start youtube-viewer
     ```
   - Verify functionality

7. **Document:** Record incident and response
   - What happened?
   - How was it detected?
   - What actions were taken?
   - What can prevent recurrence?
   - Create issue/document in `docs/incidents/`

**Emergency shutdown:**
```bash
# Stop application immediately
sudo systemctl stop youtube-viewer

# Block all HTTP/HTTPS traffic except SSH
sudo ufw deny 80/tcp
sudo ufw deny 443/tcp

# Application remains stopped until explicitly started
# SSH access maintained for investigation
```

**Recovery:**
```bash
# After remediation, restore service
sudo systemctl start youtube-viewer

# Re-enable ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Verify application health
curl -k https://youtube-viewer.yourdomain.com/health
```

### Detailed Rollback Procedure

**Complete rollback procedure with verification:**

```bash
# Rollback Procedure - Use when deployment causes issues

# 1. Stop the application service
sudo systemctl stop youtube-viewer

# 2. Identify backup to restore from
ls -lh /opt/youtube-viewer/backups/
# Choose appropriate backup (e.g., app-20250107-143000.db)

# 3. Backup current database (in case rollback fails)
sudo cp /opt/youtube-viewer/data/app.db /opt/youtube-viewer/data/app.db.failed-deploy

# 4. Restore from backup
sudo cp /opt/youtube-viewer/backups/app-20250107-143000.db /opt/youtube-viewer/data/app.db

# 5. Verify file permissions
sudo chown youtube-viewer:youtube-viewer /opt/youtube-viewer/data/app.db
sudo chmod 600 /opt/youtube-viewer/data/app.db
ls -la /opt/youtube-viewer/data/app.db
# Should show: -rw------- 1 youtube-viewer youtube-viewer

# 6. Verify database integrity
sqlite3 /opt/youtube-viewer/data/app.db "PRAGMA integrity_check;"
# Should return: ok

# 7. Restart application
sudo systemctl start youtube-viewer

# 8. Verify service is running
sudo systemctl status youtube-viewer
# Should show: active (running)

# 9. Check application health endpoint
curl https://youtube-viewer.yourdomain.com/health
# Should return: {"status":"ok","timestamp":"..."}

# 10. Test critical functionality
# - Navigate to home page: https://youtube-viewer.yourdomain.com
# - Verify video grid loads (9 videos)
# - Admin login: https://youtube-viewer.yourdomain.com/admin/login
# - Verify channels list loads

# 11. Review logs for errors
sudo journalctl -u youtube-viewer -n 50
sudo tail -50 /opt/youtube-viewer/logs/app.log

# 12. If rollback successful, document the issue
echo "$(date): Rolled back to backup app-20250107-143000.db due to [reason]" >> /opt/youtube-viewer/rollback-log.txt
```

**Common rollback scenarios:**

| Scenario | Action | Verification |
|----------|--------|-------------|
| Bad deployment | Restore previous backup | Test video playback |
| Database corruption | Restore yesterday's backup | PRAGMA integrity_check |
| Configuration error | Restore backup + fix config | Health check endpoint |
| Data loss | Restore most recent backup | Check video counts |

---

