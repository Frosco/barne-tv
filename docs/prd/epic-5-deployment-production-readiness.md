# Epic 5: Deployment & Production Readiness

**Goal:** Production deployment infrastructure, monitoring, and complete operational procedures.

**Deliverable:** System deployed to production with monitoring, backups, and parent-friendly operations documentation.

## Story 5.1: Production Server Setup (Hetzner VPS)

As an operations team member,
I want the Hetzner VPS configured for production deployment,
so that the application runs securely and efficiently.

**Acceptance Criteria:**
1. Hetzner CX23 Cloud Server provisioned (Falkenstein, Germany: 1 vCPU, 2GB RAM, 20GB SSD)
2. Ubuntu 22.04 LTS installed and updated
3. Firewall configured (UFW): `default deny incoming`, `default allow outgoing`, allow ports 22/80/443 only
4. UFW enabled and verify status shows active rules
5. SSH hardened (key-only auth, root login disabled, PasswordAuthentication no)
6. Python 3.11.7+ installed - verify with `python3.11 --version`
7. python3.11-dev installed (required for bcrypt compilation)
8. uv package manager installed system-wide
9. Node.js v22.11 LTS installed - verify with `node --version`
10. npm installed and functional
11. Nginx installed (1.28.0+) and configured as reverse proxy
12. Nginx security headers configured: X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy, X-Robots-Tag
13. Nginx CSP header configured to allow YouTube iframe embedding
14. Nginx configured to serve /static from `/opt/youtube-viewer/static` with cache headers (7 days)
15. robots.txt configured to block all crawlers (noindex, nofollow)
16. SSL certificate provisioned (Let's Encrypt via certbot)
17. Application directory structure created: `/opt/youtube-viewer/` with subdirectories: data/, backups/, logs/
18. Directory ownership: `youtube-viewer:youtube-viewer` for all application directories
19. Directory permissions: data/ (700), backups/ (700), logs/ (755)
20. Database file permissions configured: 600 (read/write owner only)
21. .env file created at `/opt/youtube-viewer/.env` with permissions 600
22. Required environment variables in .env: DATABASE_PATH, YOUTUBE_API_KEY, ALLOWED_HOSTS, DEBUG=false, LOG_LEVEL, LOG_FILE
23. Verify bcrypt installed and functional: `python3.11 -c "from passlib.hash import bcrypt; print('OK')"`
24. SQLite version 3.51.0 verified
25. System packages installed: nginx, python3.11, python3.11-dev, sqlite3, certbot, python3-certbot-nginx

## Story 5.2: Systemd Service Configuration

As an operations team member,
I want systemd services configured for application lifecycle management,
so that the application runs reliably in production.

**Acceptance Criteria:**
1. Systemd service file created (youtube-viewer.service)
2. Service runs FastAPI application via uvicorn with command: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
3. Service configured for synchronous-only operation (workers=1, no async)
4. Service starts on boot (enabled)
5. Service restarts on failure with policy: `Restart=on-failure` and `RestartSec=10`
6. Service runs as dedicated user `youtube-viewer:youtube-viewer` (not root)
7. Environment variables loaded via `EnvironmentFile=/opt/youtube-viewer/.env`
8. Working directory set to `/opt/youtube-viewer`
9. Security hardening configured: `NoNewPrivileges=true`, `PrivateTmp=true`
10. Filesystem protection configured: `ProtectSystem=strict`, `ProtectHome=true`
11. Read/write paths restricted: `ReadWritePaths=/opt/youtube-viewer/data /opt/youtube-viewer/logs`
12. Logging configured to journald
13. Service can be started/stopped/restarted via systemctl
14. Service status shows clear health information
15. Verify service cannot write outside allowed paths (security test)

## Story 5.3: Deployment Scripts & Automation

As an operations team member,
I want automated deployment scripts,
so that updates can be deployed safely and consistently.

**Acceptance Criteria:**
1. deploy.sh script created for deployment automation
2. Script pulls latest code from repository
3. Script validates environment variables present in .env (DATABASE_PATH, YOUTUBE_API_KEY, etc.)
4. Script runs database migrations if needed
5. Script installs/updates backend dependencies: `uv sync --extra dev`
6. Script runs backend code quality checks: `black .`, `ruff check .`, `mypy backend/`
7. Script runs TIER 1 safety tests: `pytest -m tier1 -v` (DEPLOYMENT BLOCKER - must pass 100%)
8. Script verifies backend coverage: `pytest --cov=backend --cov-report=term` (target: 85%+)
9. Script verifies no async/await in backend code (architectural constraint check)
10. Script builds frontend: `cd frontend && npm install && npm run build` (outputs to static/)
11. Script runs frontend code quality checks: `npm run lint`, `npm run format`
12. Script verifies frontend tests pass: `npm test`
13. Script performs WAL checkpoint: `sqlite3 data/app.db "PRAGMA wal_checkpoint(FULL)"`
14. Script restarts systemd service: `systemctl restart youtube-viewer.service`
15. Script waits for service to be fully ready (5-10 seconds)
16. Script checks health endpoint: `curl -f http://localhost:8000/health` (must return 200)
17. Script verifies health endpoint checks database connectivity
18. Script includes rollback procedure if deployment fails (restore previous code, restart service)
19. Script logs all actions with timestamps to deployment log
20. Script exits with non-zero code if any step fails
21. Script executable by designated user (not root, youtube-viewer group)
22. Script creates deployment log: `/opt/youtube-viewer/logs/deployments.log`

## Story 5.4: Monitoring & Maintenance Setup

As an operations team member,
I want monitoring and maintenance procedures,
so that I can ensure system health and respond to issues.

**Acceptance Criteria:**
1. Health check endpoint (/health) returns detailed status including database connectivity check
2. Health endpoint response format: `{"status":"ok","timestamp":"...","database":"connected"}`
3. Application logging configured for JSON structured format
4. Application logs written to: `/var/log/youtube-viewer/app.log`
5. Log file permissions: 640 youtube-viewer:youtube-viewer
6. Logrotate configured at `/etc/logrotate.d/youtube-viewer`
7. Log rotation policy: daily, compress, keep last 7 days
8. Verify logrotate can access and rotate log files
9. Backup script created (scripts/backup.sh) for database
10. Backup script runs WAL checkpoint before copying: `PRAGMA wal_checkpoint(FULL)`
11. Backup filename format: `app-YYYYMMDD-HHMMSS.db`
12. Backup file permissions: 600 youtube-viewer:youtube-viewer
13. Backup directory: `/opt/youtube-viewer/backups/`
14. Backup timer configured (systemd timer: youtube-viewer-backup.timer)
15. Backup schedule: daily at 2 AM UTC
16. Backup retention policy: keep last 7 days (automatic rotation)
17. Restore script created (scripts/restore.sh) with verification steps
18. Restore procedure includes: stop service, backup current DB, copy from backup, set permissions (600), integrity check
19. Restore verification: `PRAGMA integrity_check` returns OK before restart
20. Health check script created (scripts/check-health.sh) for weekly manual checks
21. Dashboard script created (scripts/dashboard.sh) showing: service status, disk space, recent errors, today's activity
22. Monitoring scripts output in Norwegian for parent readability
23. Alert thresholds defined for: service down, disk space <20%, database errors
24. Weekly maintenance checklist includes: run check-health.sh, verify backups exist, check disk space, review error logs

## Story 5.5: Parent Operations Guide

As a parent operating the application,
I want a simplified operations guide in Norwegian,
so that I can maintain and troubleshoot the system independently.

**Acceptance Criteria:**
1. Operations guide created at `docs/operations-guide-no.md` in Norwegian
2. Guide includes step-by-step deployment procedure with exact commands
3. Guide includes backup and restore procedures with verification steps
4. Guide documents restore verification: `PRAGMA integrity_check` must return OK
5. Guide includes log viewing instructions with journalctl commands explained in Norwegian
6. Guide documents session behavior: "Økter nullstilles ved omstart - du må logge inn på nytt"
7. Guide includes common troubleshooting scenarios with Norwegian solutions
8. Guide includes weekly maintenance checklist in Norwegian: sjekk helse, verifiser backup, sjekk diskplass, se feillogger
9. Guide includes monthly maintenance checklist in Norwegian: verifiser SSL-sertifikat, kjør restore-test, oppdater system
10. Guide written in clear, non-technical Norwegian (no technical jargon)
11. Guide includes screenshots or command examples for each procedure
12. Guide covers: starting/stopping service, viewing logs, restoring from backup, password reset
13. Guide documents bcrypt password reset procedure
14. Guide references monitoring scripts: check-health.sh, dashboard.sh with Norwegian explanations
15. Guide includes journalctl examples: `journalctl -u youtube-viewer.service -n 50` (vis siste 50 linjer)
16. Guide documents systemctl commands: start, stop, restart, status with Norwegian explanations
17. Guide includes troubleshooting section: "Tjenesten starter ikke", "Ingen videoer vises", "Kan ikke logge inn"
18. Guide accessible from admin interface (link to documentation)
19. Guide includes emergency contacts/procedures section
20. Guide formatted for easy printing (A4, readable font size)

---
