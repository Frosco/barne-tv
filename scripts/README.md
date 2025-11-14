# Deployment Scripts Documentation

This directory contains automation scripts for deploying and managing the Safe YouTube Viewer for Kids application.

## Scripts

### deploy.sh

Automated deployment script with quality gates, testing validation, and automatic rollback on failure.

**Purpose:** Safely deploy application updates to production with comprehensive quality checks and automatic rollback if any step fails.

## Prerequisites

Before running the deployment script, ensure the following requirements are met:

### 1. User Permissions

- User must be a member of the `youtube-viewer` group
- User must have sudo permissions for systemctl commands
- Verify with: `groups` (should include `youtube-viewer`)

### 2. Environment Setup

- Environment file must exist: `/opt/youtube-viewer/.env`
- Required environment variables:
  - `DATABASE_PATH` - Path to SQLite database
  - `YOUTUBE_API_KEY` - YouTube Data API v3 key
  - `ALLOWED_HOSTS` - Comma-separated list of allowed hostnames
  - `DEBUG` - Debug mode flag (true/false)
  - `LOG_LEVEL` - Logging level (INFO, DEBUG, etc.)
  - `LOG_FILE` - Path to application log file

### 3. Git Repository

- Git repository must be cloned at `/opt/youtube-viewer/app/`
- Git remote must be configured (usually `origin`)
- User must have git pull access to the repository
- Working directory must be clean (no uncommitted changes)

### 4. System Dependencies

- **uv** - Python package manager (for backend dependencies)
- **npm** - Node package manager (for frontend dependencies)
- **sqlite3** - SQLite command-line tool (for WAL checkpoint)
- **curl** - For health check verification
- **python3** - Python 3 interpreter (for JSON parsing in health checks)
- **bc** (optional) - Basic calculator (for coverage percentage comparison, fallback to awk if not available)

Verify installations:
```bash
uv --version
npm --version
sqlite3 --version
curl --version
bc --version
```

### 5. System Services

- Systemd service must be installed: `youtube-viewer.service`
- Service must be enabled: `systemctl is-enabled youtube-viewer.service`
- User must have sudo permissions to restart the service

## Usage

### Basic Deployment

```bash
# Navigate to application directory
cd /opt/youtube-viewer/app

# Run deployment script
./scripts/deploy.sh
```

### Monitoring Deployment

The script logs all actions to `/opt/youtube-viewer/logs/deployments.log`. Monitor deployment progress:

```bash
# Watch deployment log in real-time
tail -f /opt/youtube-viewer/logs/deployments.log

# View last deployment
tail -n 100 /opt/youtube-viewer/logs/deployments.log
```

## Deployment Process

The script performs the following steps in order:

### 1. Environment Validation
- Checks that `.env` file exists
- Validates all required environment variables are present
- **Blocker:** Deployment fails if any variable is missing

### 2. Code Update
- Stores current git commit SHA for rollback
- Pulls latest code from `main` branch
- Logs commit SHAs (previous and new)
- **Blocker:** Deployment fails if git pull fails

### 3. Database Migrations
- Checks for migration script (`backend/db/migrate.py`)
- Runs migrations if script exists
- Logs "No migrations needed" if script doesn't exist
- **Blocker:** Deployment fails if migrations fail

### 4. Backend Dependencies
- Installs/updates Python packages: `uv sync --extra dev`
- **Blocker:** Deployment fails if dependency installation fails

### 5. Backend Quality Checks
- **Black formatter check:** Verifies code is formatted correctly
- **Ruff linter:** Checks for code quality issues
- **Mypy type checker:** Verifies type annotations
- **Blocker:** Deployment fails if any quality check fails

### 6. TIER 1 Safety Tests (CRITICAL)
- Runs child safety tests: `pytest -m tier1 -v`
- Tests 6 critical safety rules (banned videos, time limits, UTC times, etc.)
- **DEPLOYMENT BLOCKER:** ANY failure blocks deployment immediately
- This is the most critical quality gate

### 7. Backend Test Coverage
- Runs full test suite with coverage: `pytest --cov=backend`
- Logs coverage percentage
- **Warning only:** Coverage below 85% logs warning but doesn't block
- **Blocker:** Deployment fails if tests fail

### 8. Architectural Constraint Check
- Verifies no `async def` or `await` in backend code
- Ensures synchronous-only architecture is maintained
- **Blocker:** Deployment fails if async/await detected

### 9. Frontend Build
- Installs/updates npm dependencies: `npm install`
- Builds production assets: `npm run build`
- Verifies output in `static/` directory
- **Blocker:** Deployment fails if build fails

### 10. Frontend Quality Checks
- **ESLint:** JavaScript linting
- **Prettier:** Code formatting check
- **Blocker:** Deployment fails if any check fails

### 11. Frontend Tests
- Runs Vitest unit tests: `npm test`
- **Blocker:** Deployment fails if tests fail

### 12. Database Checkpoint
- Performs SQLite WAL checkpoint: `PRAGMA wal_checkpoint(FULL)`
- Ensures all WAL changes are persisted to main database
- **Warning only:** Checkpoint failure logs warning but doesn't block

### 13. Service Restart
- Restarts systemd service: `systemctl restart youtube-viewer.service`
- Waits 5 seconds for service to start
- Verifies service is active
- **Blocker:** Deployment fails if service doesn't start

### 14. Health Check Verification
- Checks health endpoint: `curl -f http://localhost:8000/health`
- Verifies HTTP 200 status code
- Verifies JSON response: `status: "ok"` and `database: "connected"`
- **Blocker:** Deployment fails if health check fails
- Triggers rollback if health check fails

## Rollback Procedure

If ANY deployment step fails, the script automatically performs a rollback:

### Automatic Rollback Steps

1. **Log failure:** Records which step failed and why
2. **Restore code:** `git reset --hard <previous_commit>`
3. **Rebuild frontend:** `npm run build` (static/ is gitignored)
4. **Restart service:** `systemctl restart youtube-viewer.service`
5. **Wait for ready:** 5 second delay
6. **Verify health:** Checks health endpoint works
7. **Log completion:** Records rollback success
8. **Exit with error:** Returns exit code 1

### Manual Recovery

If rollback fails (rare), perform manual recovery:

```bash
# Check service status
sudo systemctl status youtube-viewer.service

# View service logs
sudo journalctl -u youtube-viewer.service -n 50

# Check application logs
tail -n 100 /opt/youtube-viewer/logs/app.log

# Check deployment logs
tail -n 100 /opt/youtube-viewer/logs/deployments.log

# Manual rollback to specific commit
cd /opt/youtube-viewer/app
git reset --hard <commit_sha>
cd frontend && npm run build && cd ..
sudo systemctl restart youtube-viewer.service

# Verify health
curl http://localhost:8000/health
```

## Exit Codes

- **0** - Deployment successful (all steps passed)
- **1** - Deployment failed (see logs for details)

## Testing Procedures

### Test Scenario 1: Successful Deployment

**Prerequisites:**
- All code quality checks pass locally
- All tests pass locally
- No uncommitted changes

**Steps:**
1. Run `./scripts/deploy.sh`
2. Monitor deployment log: `tail -f /opt/youtube-viewer/logs/deployments.log`
3. Verify all steps complete successfully
4. Verify exit code is 0: `echo $?`
5. Verify service is running: `systemctl status youtube-viewer.service`
6. Verify health endpoint: `curl http://localhost:8000/health`

**Expected Result:**
- Deployment completes without errors
- All quality checks pass
- Service restarts successfully
- Health check returns `{"status":"ok","database":"connected"}`
- Exit code: 0

---

### Test Scenario 2: Rollback on TIER 1 Test Failure

**Prerequisites:**
- Introduce a failing TIER 1 test (temporarily break a safety rule)

**Steps:**
1. Commit and push code with failing TIER 1 test
2. Run `./scripts/deploy.sh`
3. Monitor for TIER 1 test failure
4. Verify rollback is triggered automatically
5. Verify service is running previous version

**Expected Result:**
- Deployment fails at TIER 1 test step
- Error logged: "TIER 1 SAFETY TESTS FAILED - BLOCKING DEPLOYMENT"
- Rollback procedure executes automatically
- Code restored to previous commit
- Service restarted with previous version
- Health check passes after rollback
- Exit code: 1

---

### Test Scenario 3: Rollback on Health Check Failure

**Prerequisites:**
- Introduce code that breaks the health endpoint (e.g., database connection issue)

**Steps:**
1. Commit and push code that breaks health endpoint
2. Run `./scripts/deploy.sh`
3. Monitor for health check failure after service restart
4. Verify rollback is triggered automatically

**Expected Result:**
- Deployment completes quality checks and tests
- Service restarts successfully
- Health check fails
- Error logged: "Health check failed"
- Rollback procedure executes automatically
- Previous version restored and health check passes
- Exit code: 1

---

### Test Scenario 4: Rollback on Quality Check Failure

**Prerequisites:**
- Introduce linting error (e.g., unused import, formatting issue)

**Steps:**
1. Commit and push code with linting error
2. Run `./scripts/deploy.sh`
3. Monitor for quality check failure
4. Verify deployment is blocked

**Expected Result:**
- Deployment fails at quality check step (black/ruff/mypy or ESLint)
- Error logged with specific quality check that failed
- Rollback triggered automatically
- No service restart occurred (failed before that step)
- Exit code: 1

---

### Test Scenario 5: Environment Validation Failure

**Prerequisites:**
- Temporarily rename or remove a required environment variable

**Steps:**
1. Edit `/opt/youtube-viewer/.env` and comment out `YOUTUBE_API_KEY`
2. Run `./scripts/deploy.sh`
3. Verify deployment fails immediately

**Expected Result:**
- Deployment fails at environment validation step
- Error logged: "Missing required environment variables: YOUTUBE_API_KEY"
- No git pull or other operations performed
- Exit code: 1

---

## Deployment Log Examples

### Successful Deployment Log

```
[2025-11-12T10:30:00Z] [INFO] ==========================================
[2025-11-12T10:30:00Z] [INFO] Starting Deployment
[2025-11-12T10:30:00Z] [INFO] ==========================================
[2025-11-12T10:30:00Z] [INFO] Timestamp: 2025-11-12T10:30:00Z
[2025-11-12T10:30:00Z] [INFO] User: nilsadmin
[2025-11-12T10:30:00Z] [INFO] Working Directory: /opt/youtube-viewer/app
[2025-11-12T10:30:00Z] [INFO] Validating environment variables...
[2025-11-12T10:30:00Z] [INFO] Environment validation passed - all required variables present
[2025-11-12T10:30:00Z] [INFO] Pulling latest code from repository...
[2025-11-12T10:30:01Z] [INFO] Current commit: a442e0a
[2025-11-12T10:30:02Z] [INFO] Successfully pulled latest code
[2025-11-12T10:30:02Z] [INFO] New commit: b36a649
[2025-11-12T10:30:02Z] [INFO] Deploying changes from a442e0a to b36a649
...
[2025-11-12T10:35:00Z] [INFO] Health check passed: application is healthy and database is connected
[2025-11-12T10:35:00Z] [INFO] ==========================================
[2025-11-12T10:35:00Z] [INFO] Deployment Complete
[2025-11-12T10:35:00Z] [INFO] ==========================================
```

### Failed Deployment with Rollback Log

```
[2025-11-12T10:30:00Z] [INFO] Starting Deployment
...
[2025-11-12T10:32:15Z] [INFO] Running TIER 1 Safety Tests (CRITICAL)
[2025-11-12T10:32:20Z] [ERROR] TIER 1 SAFETY TESTS FAILED - BLOCKING DEPLOYMENT
[2025-11-12T10:32:20Z] [ERROR] This is a critical failure - any TIER 1 test failure blocks deployment
[2025-11-12T10:32:20Z] [ERROR] Command failed with exit code 1 at line 348
[2025-11-12T10:32:20Z] [ERROR] DEPLOYMENT FAILED - Initiating rollback procedure
[2025-11-12T10:32:20Z] [INFO] ==========================================
[2025-11-12T10:32:20Z] [INFO] Starting Rollback Procedure
[2025-11-12T10:32:20Z] [INFO] ==========================================
[2025-11-12T10:32:20Z] [INFO] Rolling back to commit: a442e0a
[2025-11-12T10:32:20Z] [INFO] Restoring previous code...
[2025-11-12T10:32:21Z] [INFO] Code restored to commit a442e0a
[2025-11-12T10:32:21Z] [INFO] Rebuilding frontend...
[2025-11-12T10:32:25Z] [INFO] Frontend rebuilt successfully
[2025-11-12T10:32:25Z] [INFO] Restarting service...
[2025-11-12T10:32:26Z] [INFO] Service restarted
[2025-11-12T10:32:26Z] [INFO] Waiting for service to be ready...
[2025-11-12T10:32:31Z] [INFO] Verifying health endpoint...
[2025-11-12T10:32:31Z] [INFO] Health check passed after rollback
[2025-11-12T10:32:31Z] [INFO] Successfully rolled back to commit a442e0a
[2025-11-12T10:32:31Z] [INFO] ==========================================
[2025-11-12T10:32:31Z] [INFO] Rollback Complete
[2025-11-12T10:32:31Z] [INFO] ==========================================
```

## Troubleshooting

### Issue: Git pull fails

**Symptoms:** Deployment fails at "Pulling latest code" step

**Causes:**
- Git remote not configured
- No network connectivity
- Authentication issues
- Local changes conflict with remote

**Solutions:**
```bash
# Check git remote
git remote -v

# Check git status
git status

# Fetch latest changes
git fetch origin

# Reset local changes if needed (careful!)
git reset --hard origin/main
```

---

### Issue: TIER 1 tests fail

**Symptoms:** Deployment fails at "Running TIER 1 Safety Tests" step

**Causes:**
- Child safety rule violation in new code
- Test environment issue
- Database connectivity problem

**Solutions:**
1. Review test output in deployment log
2. Run tests locally: `uv run pytest -m tier1 -v`
3. Fix failing tests before deploying
4. Never bypass TIER 1 tests

---

### Issue: Health check fails after deployment

**Symptoms:** Service starts but health endpoint returns errors

**Causes:**
- Database connection issues
- Environment variable misconfiguration
- Port binding conflict
- Application startup error

**Solutions:**
```bash
# Check service logs
sudo journalctl -u youtube-viewer.service -n 50

# Check application logs
tail -n 100 /opt/youtube-viewer/logs/app.log

# Check database file permissions
ls -l /opt/youtube-viewer/data/app.db

# Test database connectivity
sqlite3 /opt/youtube-viewer/data/app.db "SELECT 1;"

# Check port binding
sudo lsof -i :8000
```

---

### Issue: Rollback fails

**Symptoms:** Automatic rollback doesn't restore working state

**Causes:**
- Git repository corruption
- File permission issues
- Service won't start

**Solutions:**
```bash
# Manual rollback to last known good commit
cd /opt/youtube-viewer/app
git log --oneline -n 10  # Find good commit
git reset --hard <good_commit_sha>

# Rebuild frontend
cd frontend && npm run build && cd ..

# Restart service
sudo systemctl restart youtube-viewer.service

# Check health
curl http://localhost:8000/health
```

## Best Practices

### Before Deployment

1. **Run quality checks locally:**
   ```bash
   # Backend
   uv run black . --check
   uv run ruff check .
   uv run mypy backend/
   uv run pytest -m tier1 -v

   # Frontend
   cd frontend
   npm run lint
   npm run format -- --check
   npm test
   ```

2. **Test locally:** Verify application works on development machine

3. **Commit hygiene:** Use clear commit messages, small focused commits

4. **Review changes:** Understand what's being deployed

### During Deployment

1. **Monitor logs:** Watch deployment log in real-time
2. **Be available:** Stay available to respond to issues
3. **Don't interrupt:** Let script complete or fail on its own
4. **Document issues:** Note any warnings or anomalies

### After Deployment

1. **Verify functionality:** Test critical user paths
2. **Monitor logs:** Watch application logs for errors
3. **Check metrics:** Verify service is healthy
4. **Communicate:** Notify team of deployment completion

## Security Considerations

- **Script permissions:** 750 (owner+group execute, no world access)
- **Log permissions:** Deployment logs may contain sensitive information
- **Sudo usage:** Script requires sudo only for systemctl commands
- **Environment file:** Contains secrets, must be 600 permissions
- **Git access:** User must have read-only git access (pull only)

## Maintenance

### Regular Tasks

- **Review deployment logs:** Check for recurring warnings or issues
- **Update dependencies:** Keep uv and npm dependencies current
- **Monitor disk space:** Ensure `/opt/youtube-viewer/logs/` has space
- **Rotate logs:** Consider implementing log rotation for `deployments.log`

### Log Rotation

```bash
# Example logrotate config for /etc/logrotate.d/youtube-viewer-deploy
/opt/youtube-viewer/logs/deployments.log {
    weekly
    rotate 12
    compress
    delaycompress
    missingok
    notifempty
    create 640 youtube-viewer youtube-viewer
}
```

## Support

For issues with the deployment script:

1. Check deployment logs: `/opt/youtube-viewer/logs/deployments.log`
2. Check service logs: `sudo journalctl -u youtube-viewer.service`
3. Check application logs: `/opt/youtube-viewer/logs/app.log`
4. Consult troubleshooting section above
5. Contact development team with log excerpts

## Related Documentation

- **Architecture:** `docs/architecture/infrastructure-and-deployment.md`
- **Epic 5:** `docs/prd/epic-5-deployment-production-readiness.md`
- **Story 5.3:** `docs/stories/5.3.deployment-scripts-automation.md`
- **Story 5.4:** `docs/stories/5.4.monitoring-maintenance-setup.md`
- **Service Setup:** `scripts/systemd/youtube-viewer.service`
- **Server Verification:** `scripts/verify-server-setup.sh` (Story 5.1)
- **Service Verification:** `scripts/verify-service.sh` (Story 5.2)

---

# Monitoring & Maintenance Scripts (Story 5.4)

This section documents the monitoring, backup, and maintenance scripts for operational management of the Safe YouTube Viewer application.

## Scripts Overview

### backup.sh

Automated database backup with WAL checkpoint and retention policy.

**Purpose:** Create timestamped database backups with secure permissions and automatic cleanup of old backups.

**Usage:**
```bash
./scripts/backup.sh
```

**Features:**
- Runs SQLite WAL checkpoint before backup (ensures consistency)
- Generates filename: `app-YYYYMMDD-HHMMSS.db`
- Sets secure permissions: 600 (read/write owner only)
- Automatic retention: Deletes backups older than 7 days
- Logs all operations to `/var/log/youtube-viewer/backups.log`

**Environment Variables:**
- `DB_PATH` - Database file path (default: `/opt/youtube-viewer/data/app.db`)
- `BACKUP_DIR` - Backup directory (default: `/opt/youtube-viewer/backups`)
- `LOG_FILE` - Backup log file (default: `/var/log/youtube-viewer/backups.log`)

**Exit Codes:**
- 0: Backup successful
- 1: Backup failed (database not found, copy failed, etc.)

**Scheduled Execution:** Runs automatically via systemd timer (daily at 2 AM UTC)

---

### restore.sh

Database restore with integrity verification and automatic rollback on failure.

**Purpose:** Safely restore database from backup with comprehensive verification and safety mechanisms.

**Usage:**
```bash
# Must run as root (requires systemctl)
sudo ./scripts/restore.sh <backup-filename>

# Example
sudo ./scripts/restore.sh app-20251112-020000.db
```

**Safety Features:**
- Creates safety backup before restore (app.db.before-restore)
- Runs database integrity check after restore
- Automatic rollback if integrity check fails
- Verifies service health after restart
- Comprehensive logging of all operations

**Restore Process:**
1. Validates backup file exists
2. Stops youtube-viewer.service
3. Creates safety backup of current database
4. Copies backup to active database location
5. Sets secure permissions (600) and ownership
6. Runs SQLite integrity check
7. Rolls back if integrity check fails
8. Restarts service if integrity check passes
9. Waits 5 seconds for service initialization
10. Verifies health endpoint responds correctly

**Exit Codes:**
- 0: Restore successful
- 1: Restore failed (file not found, integrity check failed, service won't start, etc.)

**List Available Backups:**
```bash
ls -1t /opt/youtube-viewer/backups/app-*.db
```

---

### check-health.sh

Comprehensive health check script with Norwegian output for weekly maintenance.

**Purpose:** Perform weekly manual health checks covering all critical system components.

**Usage:**
```bash
./scripts/check-health.sh
```

**Health Checks Performed:**

1. **Service Status (Tjeneste Status)**
   - youtube-viewer.service running/stopped
   - nginx.service running/stopped
   - Alert if either service is down

2. **Disk Space (Diskplass)**
   - Shows usage and available space
   - Warns if >80% used (<20% free)
   - Recommends action if threshold exceeded

3. **Recent Errors (Siste Feil)**
   - Counts ERROR entries in last 24 hours (from journalctl)
   - Shows last 5 error messages if any found
   - Alerts on database errors

4. **Database Status (Database Status)**
   - Shows database file size
   - Runs SQLite quick integrity check
   - Warns if integrity check fails

5. **Backup Status (Backup Status)**
   - Shows most recent backup timestamp
   - Warns if last backup >48 hours old
   - Shows total number of backups

**Output:** Norwegian language for parent readability

**Alert Thresholds (Story 5.4 AC 23):**
- Service down: youtube-viewer or nginx not running
- Disk space <20%: High usage warning
- Database errors: Any ERROR entries in last 24 hours

**Weekly Maintenance:** Run as part of weekly maintenance checklist

---

### dashboard.sh

Real-time system dashboard with Norwegian output.

**Purpose:** Display quick overview of system status for at-a-glance monitoring.

**Usage:**
```bash
./scripts/dashboard.sh
```

**Dashboard Sections:**

1. **Services (Tjenester)**
   - ✅ Application: Running / ❌ Stopped
   - ✅ Nginx: Running / ❌ Stopped

2. **Resources (Ressurser)**
   - CPU usage or load average
   - Memory usage (used / total)
   - Disk usage (used / total / percent)

3. **Today's Activity (I dag aktivitet)**
   - Number of videos watched today (UTC)
   - Total watch time in minutes
   - Time remaining vs daily limit

4. **Recent Errors (Siste feil)**
   - Count of ERROR entries in last hour
   - Shows last 3 error messages if any

**Output:** Norwegian language with emoji indicators

**Use Case:** Quick status check, can be run anytime

---

## Systemd Timer Configuration

### Automated Daily Backups

**Service Unit:** `scripts/systemd/youtube-viewer-backup.service`
**Timer Unit:** `scripts/systemd/youtube-viewer-backup.timer`

**Installation:**
```bash
# Copy service and timer to systemd directory
sudo cp scripts/systemd/youtube-viewer-backup.service /etc/systemd/system/
sudo cp scripts/systemd/youtube-viewer-backup.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start timer
sudo systemctl enable youtube-viewer-backup.timer
sudo systemctl start youtube-viewer-backup.timer
```

**Verification:**
```bash
# Check timer status
systemctl list-timers | grep youtube-viewer-backup

# View timer details
systemctl status youtube-viewer-backup.timer

# View backup service logs
journalctl -u youtube-viewer-backup.service -n 50
```

**Schedule:** Daily at 2:00 AM UTC (with 15-minute randomized delay)

**Manual Trigger:**
```bash
# Run backup manually (for testing)
sudo systemctl start youtube-viewer-backup.service

# Check backup completion
journalctl -u youtube-viewer-backup.service -n 20
```

---

## Application Logging

### JSON Structured Logging

**Configuration:** `backend/logging_config.py`

**Log File:** `/var/log/youtube-viewer/app.log`

**Format:** JSON with fields:
- `timestamp`: ISO 8601 UTC timestamp
- `level`: Log level (INFO, WARNING, ERROR, etc.)
- `message`: Log message
- `logger`: Logger name
- `module`: Module name
- `function`: Function name
- `line`: Line number

**Example Log Entry:**
```json
{
  "timestamp": "2025-11-13T14:30:00.123456+00:00",
  "level": "INFO",
  "message": "Health check passed",
  "logger": "backend.main",
  "module": "main",
  "function": "health_check",
  "line": 180
}
```

**Viewing Logs:**
```bash
# Tail application logs
tail -f /var/log/youtube-viewer/app.log

# View last 50 lines
tail -n 50 /var/log/youtube-viewer/app.log

# Parse JSON logs with jq
tail -n 100 /var/log/youtube-viewer/app.log | jq '.message'

# Filter by log level
tail -n 100 /var/log/youtube-viewer/app.log | jq 'select(.level=="ERROR")'
```

### Log Rotation

**Configuration File:** `scripts/logrotate-youtube-viewer`

**Installation:**
```bash
# Copy to logrotate directory
sudo cp scripts/logrotate-youtube-viewer /etc/logrotate.d/youtube-viewer
sudo chmod 644 /etc/logrotate.d/youtube-viewer
```

**Policy:**
- Rotate: Daily
- Retention: 7 days
- Compression: gzip (delayed by 1 day)
- Permissions: 640 youtube-viewer:youtube-viewer

**Testing:**
```bash
# Dry-run (test configuration)
sudo logrotate -d /etc/logrotate.d/youtube-viewer

# Force rotation (for testing)
sudo logrotate -f /etc/logrotate.d/youtube-viewer

# Verify rotated logs
ls -lh /var/log/youtube-viewer/
```

---

## Weekly Maintenance Checklist (Story 5.4 AC 24)

Perform these maintenance tasks weekly to ensure system health and identify issues early.

### Norwegian Checklist (For Parents)

**Ukentlig vedlikehold (Weekly Maintenance):**

1. ☐ **Kjør helsekontroll (Run health check)**
   ```bash
   cd /opt/youtube-viewer/app
   ./scripts/check-health.sh
   ```
   - Verifiser ingen advarsler (Verify no warnings)
   - Se gjennom resultater (Review results)

2. ☐ **Verifiser backup finnes (Verify backups exist)**
   ```bash
   ls -lht /opt/youtube-viewer/backups/ | head -8
   ```
   - Sjekk at siste backup er <48 timer (Check last backup is <48 hours)
   - Verifiser 7 dager med backups (Verify 7 days of backups)

3. ☐ **Sjekk diskplass (Check disk space)**
   ```bash
   df -h /opt/youtube-viewer
   ```
   - Sørg for >20% ledig (Ensure >20% free)
   - Hvis lav plass, se på backup-oppbevaring (If low, check backup retention)

4. ☐ **Se gjennom feillogger (Review error logs)**
   ```bash
   journalctl -u youtube-viewer.service --since "7 days ago" | grep ERROR
   ```
   - Sjekk om det er gjentatte feil (Check for repeated errors)
   - Undersøk uventede feilmeldinger (Investigate unexpected errors)

### Expected Outcomes

- **Health Check:** All checks pass with ✓ indicators, no red warnings
- **Backups:** 7 backup files present, newest <48 hours old
- **Disk Space:** <80% used (>20% free)
- **Error Logs:** No unexpected errors, only normal operational logs

### When to Take Action

Take immediate action if:
- Service is stopped (red ✗ in health check)
- Disk space >80% used (yellow/red warning)
- Database integrity check fails (red warning)
- Last backup >48 hours old (yellow/red warning)
- Repeated ERROR entries in logs (investigate cause)

**Action Steps:**
1. Document the issue (screenshot, log excerpt)
2. Check service status: `sudo systemctl status youtube-viewer.service`
3. Review recent changes (deployments, configuration)
4. If database issue: Consider restore from backup
5. If disk space issue: Check log sizes, backup retention
6. Consult troubleshooting section or deployment team

---

## Troubleshooting

### Backup Issues

**Issue:** Backup fails with "Database file not found"

**Solution:**
```bash
# Verify database exists
ls -l /opt/youtube-viewer/data/app.db

# Check environment variables
echo $DB_PATH

# Run backup with explicit path
DB_PATH=/opt/youtube-viewer/data/app.db ./scripts/backup.sh
```

---

**Issue:** Backup directory permission denied

**Solution:**
```bash
# Check backup directory permissions
ls -ld /opt/youtube-viewer/backups

# Fix ownership if needed
sudo chown youtube-viewer:youtube-viewer /opt/youtube-viewer/backups
sudo chmod 700 /opt/youtube-viewer/backups
```

---

**Issue:** Old backups not being deleted

**Solution:**
```bash
# Manually clean old backups (>7 days)
find /opt/youtube-viewer/backups/ -name "app-*.db" -mtime +7 -ls

# Delete old backups
find /opt/youtube-viewer/backups/ -name "app-*.db" -mtime +7 -delete
```

---

### Restore Issues

**Issue:** Restore fails with "Backup file not found"

**Solution:**
```bash
# List available backups
ls -1t /opt/youtube-viewer/backups/

# Use full filename including extension
sudo ./scripts/restore.sh app-20251112-020000.db
```

---

**Issue:** Restore fails integrity check

**Cause:** Backup file is corrupted

**Solution:**
```bash
# Try previous backup
sudo ./scripts/restore.sh app-20251111-020000.db

# If all backups fail, investigate database corruption cause
sqlite3 /opt/youtube-viewer/data/app.db "PRAGMA integrity_check;"
```

---

**Issue:** Service won't start after restore

**Solution:**
```bash
# Check service logs
sudo journalctl -u youtube-viewer.service -n 50

# Check database file permissions
ls -l /opt/youtube-viewer/data/app.db

# Should be: -rw------- youtube-viewer youtube-viewer
sudo chmod 600 /opt/youtube-viewer/data/app.db
sudo chown youtube-viewer:youtube-viewer /opt/youtube-viewer/data/app.db

# Restart service
sudo systemctl restart youtube-viewer.service
```

---

### Health Check Issues

**Issue:** Health check shows "journalctl not available"

**Cause:** User not in systemd-journal group

**Solution:**
```bash
# Add user to systemd-journal group
sudo usermod -aG systemd-journal $USER

# Logout and login for group membership to take effect
```

---

**Issue:** Health check shows disk space warning but plenty of space available

**Cause:** Checking wrong filesystem

**Solution:**
```bash
# Check which filesystem is being monitored
df -h /opt/youtube-viewer

# Ensure DATA_DIR points to correct location
DATA_DIR=/opt/youtube-viewer ./scripts/check-health.sh
```

---

### Dashboard Issues

**Issue:** Today's activity shows 0 videos despite actual viewing

**Cause:** UTC date mismatch

**Solution:**
```bash
# Check current UTC date
date -u +"%Y-%m-%d"

# Query watch_history manually
sqlite3 /opt/youtube-viewer/data/app.db \
  "SELECT COUNT(*) FROM watch_history WHERE DATE(watched_at) = DATE('now');"

# Verify watched_at timestamps are in UTC
sqlite3 /opt/youtube-viewer/data/app.db \
  "SELECT watched_at FROM watch_history ORDER BY watched_at DESC LIMIT 5;"
```

---

### Log Rotation Issues

**Issue:** Logs not rotating

**Solution:**
```bash
# Test logrotate configuration
sudo logrotate -d /etc/logrotate.d/youtube-viewer

# Check logrotate status
sudo cat /var/lib/logrotate/status | grep youtube-viewer

# Force rotation manually
sudo logrotate -f /etc/logrotate.d/youtube-viewer
```

---

**Issue:** Application stops logging after rotation

**Cause:** Application didn't reopen log file after rotation

**Solution:**
```bash
# Logrotate postrotate script should reload service
# Verify postrotate is configured in logrotate config

# Manually reload service
sudo systemctl reload youtube-viewer.service

# Or restart if reload doesn't work
sudo systemctl restart youtube-viewer.service
```

---

## Best Practices

### Backup Management

- **Verify backups:** Periodically test restore procedure (monthly)
- **Monitor backup timer:** Check timer status weekly
- **Backup before changes:** Manual backup before major updates
- **Off-site backups:** Consider copying backups off-server for disaster recovery

**Manual Pre-Deployment Backup:**
```bash
# Run backup before deployment
sudo systemctl start youtube-viewer-backup.service

# Verify backup completed
journalctl -u youtube-viewer-backup.service -n 20

# List backups
ls -lht /opt/youtube-viewer/backups/ | head -3
```

### Monitoring

- **Regular health checks:** Run check-health.sh weekly
- **Dashboard reviews:** Quick check via dashboard.sh daily or as needed
- **Log monitoring:** Review error logs weekly
- **Disk space:** Keep disk usage below 70% for safety margin

### Log Management

- **Structured logging:** JSON logs enable easy parsing and analysis
- **Log rotation:** Automatic rotation prevents disk space issues
- **Retention policy:** 7 days balances space and troubleshooting needs
- **Log analysis:** Use jq for parsing JSON logs efficiently

**Example Log Analysis:**
```bash
# Count errors by module
tail -n 1000 /var/log/youtube-viewer/app.log | \
  jq -r 'select(.level=="ERROR") | .module' | \
  sort | uniq -c | sort -rn

# Extract error messages
tail -n 1000 /var/log/youtube-viewer/app.log | \
  jq -r 'select(.level=="ERROR") | .message'

# Find logs from specific function
tail -n 1000 /var/log/youtube-viewer/app.log | \
  jq 'select(.function=="health_check")'
```

---

## Security Considerations

- **Script permissions:** All scripts are 750 (owner+group execute only)
- **Backup permissions:** 600 (owner read/write only) to protect database
- **Log permissions:** 640 (owner read/write, group read) for monitoring
- **Root requirements:** restore.sh requires root for systemctl operations
- **Backup directory:** 700 permissions prevent unauthorized access

---

## Related Files

**Scripts:**
- `scripts/backup.sh` - Database backup automation
- `scripts/restore.sh` - Database restore with verification
- `scripts/check-health.sh` - Weekly health checks
- `scripts/dashboard.sh` - Real-time system dashboard

**Systemd:**
- `scripts/systemd/youtube-viewer-backup.service` - Backup service unit
- `scripts/systemd/youtube-viewer-backup.timer` - Backup timer unit

**Configuration:**
- `scripts/logrotate-youtube-viewer` - Log rotation config
- `backend/logging_config.py` - JSON logging setup

**Logs:**
- `/var/log/youtube-viewer/app.log` - Application logs (JSON)
- `/var/log/youtube-viewer/backups.log` - Backup operation logs
- System logs via `journalctl -u youtube-viewer.service`

**Documentation:**
- `docs/stories/5.4.monitoring-maintenance-setup.md` - Story specification
- `docs/architecture/monitoring-and-observability.md` - Architecture details
