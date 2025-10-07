# Epic 5: Deployment & Production Readiness

**Goal:** Production deployment infrastructure, monitoring, and complete operational procedures.

**Deliverable:** System deployed to production with monitoring, backups, and parent-friendly operations documentation.

## Story 5.1: Systemd Service Configuration

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

## Story 5.2: Production Server Setup (Hetzner VPS)

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

## Story 5.3: Deployment Scripts & Automation

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

## Story 5.4: Monitoring & Maintenance Setup

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

## Story 5.5: Parent Operations Guide

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
