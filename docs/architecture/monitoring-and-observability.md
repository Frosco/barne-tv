# Monitoring and Observability

This section defines monitoring strategy appropriate for a **single-family self-hosted deployment**. Unlike enterprise systems, this architecture prioritizes simplicity over comprehensive monitoring infrastructure.

## Monitoring Philosophy

**Approach:** Manual monitoring with simple automated checks

**Rationale:**
- Single-family deployment has predictable usage patterns
- No 24/7 uptime requirements
- Parent can perform weekly maintenance checks
- Cost-effective: no third-party monitoring services needed
- Appropriate for the scale: ~10-20 video plays per day

**When to upgrade:** If deploying for multiple families or community use, consider adding automated monitoring tools (Prometheus, Grafana, Sentry).

## Monitoring Stack

### Application Monitoring

**Logging:**
- **Tool:** Python `logging` module with file handler
- **Location:** `/var/log/youtube-viewer/app.log` (production)
- **Rotation:** Daily via logrotate, keep 7 days
- **Format:** Timestamp, level, message, context

**System Monitoring:**
- **Tool:** systemd status and journalctl
- **Checks:** Service health, restart count, resource usage
- **Frequency:** Manual weekly checks

**Error Tracking:**
- **Tool:** Application logs with ERROR level
- **No third-party service** (Sentry, Rollbar not needed for family deployment)
- **Review:** Parent checks logs weekly

**Performance Monitoring:**
- **Tool:** Application timing logs for critical operations
- **Metrics:** API call duration, database query time, page generation
- **Storage:** Logged to application log file
- **Review:** Manual observation of response times

### Infrastructure Monitoring

**Server Health:**
- **CPU/Memory:** Monitor via `top`, `htop`, or `systemctl status`
- **Disk Space:** Weekly check with `df -h`
- **Network:** Basic connectivity checks (ping, curl)

**Database Health:**
- **Size Monitoring:** Track `app.db` file size growth
- **Integrity:** Monthly `PRAGMA integrity_check`
- **Backup Verification:** Automated backup success logs

**Web Server (Nginx):**
- **Access Logs:** `/var/log/nginx/access.log`
- **Error Logs:** `/var/log/nginx/error.log`
- **Status:** `systemctl status nginx`

## Key Metrics

### Application Health Metrics

**Service Status:**
- FastAPI application running (systemd)
- Nginx reverse proxy running
- Database accessible and not locked

**Request Metrics:**
- Total requests per day (from logs)
- Failed requests (4xx/5xx errors)
- Average response time for key endpoints

**API Quota Usage:**
- YouTube API quota consumed (logged daily)
- Quota remaining (warn if <20%)
- Failed API calls due to quota exceeded

### Performance Metrics

**Response Time Targets:**
| Endpoint | Target | Acceptable | Action if Exceeded |
|----------|--------|------------|-------------------|
| GET /api/videos | <500ms | <1s | Check database size |
| POST /api/watch | <200ms | <500ms | Check write contention |
| GET / (child home) | <2s | <3s | Optimize queries |
| Admin pages | <1s | <2s | Acceptable |

**Resource Usage Targets:**
- **CPU:** <25% average, <75% peak
- **Memory:** <500MB RSS for FastAPI process
- **Disk:** <1GB total for database and logs
- **Network:** <100MB/day (mostly YouTube API metadata)

### Safety & Security Metrics

**Child Safety:**
- Time limit enforcement success rate (should be 100%)
- Banned video block count (should be 0 playbacks)
- Daily watch time per day
- Videos in rotation (aim for 30-50 active videos)

**Security Events:**
- Failed admin login attempts (should be rare)
- Rate limit hits (should be 0)
- Suspicious request patterns (404s, unusual paths)
- SSL certificate expiry (90-day warning)

### Content Health Metrics

**Content Freshness:**
- Days since last source refresh
- Failed refresh attempts
- Videos with stale metadata (>30 days old)
- Unavailable video count (removed by uploader)

**Channel Health:**
- Active channels/playlists count
- Videos per channel
- Last successful fetch per channel

## Monitoring Implementation

### Application Logging Configuration

**Python logging setup (backend/main.py):**
```python
import logging
from logging.handlers import RotatingFileHandler
import os

# Configure logging
log_file = os.getenv('LOG_FILE', '/var/log/youtube-viewer/app.log')
log_level = os.getenv('LOG_LEVEL', 'INFO')

# Create logs directory if needed
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# Configure handler
handler = RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

# Configure root logger
logging.basicConfig(
    level=getattr(logging, log_level),
    handlers=[handler]
)

logger = logging.getLogger("youtube-viewer")
```

**Structured logging for key events:**
```python
# Log security events
@app.middleware("http")
async def security_logging(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Log failed authentication
    if request.url.path == "/admin/login" and response.status_code == 401:
        logger.warning(
            "Failed admin login attempt",
            extra={
                "ip": request.client.host,
                "user_agent": request.headers.get("user-agent")
            }
        )
    
    # Log slow requests
    if duration > 1.0:
        logger.warning(
            f"Slow request: {request.method} {request.url.path} took {duration:.2f}s"
        )
    
    return response

# Log API quota usage
def log_youtube_api_call(quota_cost: int):
    logger.info(
        f"YouTube API call",
        extra={"quota_cost": quota_cost, "endpoint": "videos.list"}
    )

# Log time limit events
def log_time_limit_event(event_type: str, minutes_remaining: int):
    logger.info(
        f"Time limit event: {event_type}",
        extra={"minutes_remaining": minutes_remaining}
    )
```

### Log Rotation Configuration

**File: `/etc/logrotate.d/youtube-viewer`**
```bash
/var/log/youtube-viewer/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 youtube-viewer youtube-viewer
    sharedscripts
    postrotate
        systemctl reload youtube-viewer
    endscript
}
```

### System Metrics Collection

**Manual monitoring script: `scripts/check-health.sh`**
```bash
#!/bin/bash
# Quick health check script for weekly manual review

echo "=== Safe YouTube Viewer Health Check ==="
echo "Date: $(date)"
echo ""

# Service status
echo "--- Service Status ---"
systemctl status youtube-viewer --no-pager | grep "Active:"
systemctl status nginx --no-pager | grep "Active:"
echo ""

# Resource usage
echo "--- Resource Usage ---"
echo "CPU/Memory:"
ps aux | grep "backend.main" | grep -v grep
echo ""
echo "Disk Space:"
df -h /opt/youtube-viewer
echo ""

# Database status
echo "--- Database ---"
ls -lh /opt/youtube-viewer/data/app.db
echo ""

# Recent errors
echo "--- Recent Errors (last 24h) ---"
journalctl -u youtube-viewer --since "24 hours ago" | grep ERROR | tail -5
echo ""

# YouTube API quota
echo "--- API Quota Usage ---"
grep "YouTube API" /var/log/youtube-viewer/app.log | tail -10
echo ""

# Backup status
echo "--- Backup Status ---"
ls -lht /opt/youtube-viewer/backups/ | head -5
echo ""

echo "=== Health Check Complete ==="
```

**Run weekly:**
```bash
chmod +x scripts/check-health.sh
./scripts/check-health.sh
```

## Alerting Strategy

### Manual Alerting (Default)

**Weekly Parent Checklist:**
- [ ] Run health check script
- [ ] Review error logs for issues
- [ ] Check disk space >20% free
- [ ] Verify backup ran this week
- [ ] Check SSL certificate >30 days valid
- [ ] Review child's watch time patterns

**Monthly Parent Checklist:**
- [ ] Test backup restoration
- [ ] Review YouTube API quota usage trends
- [ ] Check for system updates (apt update)
- [ ] Verify all sources refreshing successfully
- [ ] Review banned video list relevance

### Optional Automated Alerts

**Email alerts for critical events (optional):**

**Setup with cron and mail:**
```bash
# Install mail utilities
apt install mailutils

# Add to crontab
crontab -e

# Daily backup failure alert
0 3 * * * /opt/youtube-viewer/scripts/backup.sh || echo "Backup failed!" | mail -s "YouTube Viewer Backup Failed" parent@example.com

# Weekly health check email
0 9 * * 0 /opt/youtube-viewer/scripts/check-health.sh | mail -s "YouTube Viewer Weekly Health Check" parent@example.com

# Disk space alert (if <10% free)
0 * * * * df -h /opt/youtube-viewer | awk '$5 > 90 {print}' | mail -s "YouTube Viewer Disk Space Low" parent@example.com
```

### Critical Event Handling

**Automated responses to critical events:**

**Service failure → automatic restart:**
```ini
# In /etc/systemd/system/youtube-viewer.service
[Service]
Restart=on-failure
RestartSec=10
```

**Database corruption → restore from backup:**
```bash
# Manual process in scripts/restore.sh
# Parent runs if database errors detected
```

**SSL expiration → Certbot auto-renewal:**
```bash
# Certbot systemd timer handles renewal
systemctl list-timers | grep certbot
```

## Performance Monitoring

### Response Time Logging

**Log slow operations (>1 second):**
```python
import time
import functools

def log_performance(operation_name: str):
    """Decorator to log operation performance"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            if duration > 1.0:
                logger.warning(
                    f"Slow operation: {operation_name} took {duration:.2f}s"
                )
            else:
                logger.debug(
                    f"Operation: {operation_name} took {duration:.2f}s"
                )
            
            return result
        return wrapper
    return decorator

# Usage:
@log_performance("video_grid_generation")
def get_videos_for_grid(count: int):
    # ... implementation
    pass
```

### Database Query Monitoring

**Log slow queries (>100ms):**
```python
def execute_with_timing(conn, query: str, params: tuple = ()):
    """Execute query with performance logging"""
    start_time = time.time()
    result = conn.execute(query, params).fetchall()
    duration = time.time() - start_time
    
    if duration > 0.1:  # 100ms threshold
        logger.warning(
            f"Slow query: {duration:.3f}s",
            extra={"query": query[:100]}  # Log first 100 chars
        )
    
    return result
```

### Frontend Performance

**Browser performance API:**
```javascript
// Log page load times
window.addEventListener('load', () => {
  const perfData = performance.getEntriesByType('navigation')[0];
  
  if (perfData.loadEventEnd - perfData.fetchStart > 2000) {
    console.warn('Slow page load:', {
      total: perfData.loadEventEnd - perfData.fetchStart,
      dns: perfData.domainLookupEnd - perfData.domainLookupStart,
      request: perfData.responseEnd - perfData.requestStart,
      dom: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart
    });
  }
});
```

## Operational Dashboards

### Command-Line Dashboard

**Quick status view: `scripts/dashboard.sh`**
```bash
#!/bin/bash
# Simple dashboard for current system status

clear
echo "╔════════════════════════════════════════════════════╗"
echo "║   Safe YouTube Viewer - System Dashboard          ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Service status
echo "📊 Services:"
systemctl is-active youtube-viewer >/dev/null && echo "  ✅ Application: Running" || echo "  ❌ Application: Stopped"
systemctl is-active nginx >/dev/null && echo "  ✅ Nginx: Running" || echo "  ❌ Nginx: Stopped"
echo ""

# Resource usage
echo "💻 Resources:"
echo "  CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "  Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "  Disk: $(df -h /opt/youtube-viewer | awk 'NR==2 {print $3 "/" $2 " (" $5 " used)"}')"
echo ""

# Today's usage
echo "📺 Today's Activity:"
TODAY=$(date +%Y-%m-%d)
WATCH_COUNT=$(sqlite3 /opt/youtube-viewer/data/app.db "SELECT COUNT(*) FROM watch_history WHERE DATE(watched_at) = '$TODAY'")
WATCH_TIME=$(sqlite3 /opt/youtube-viewer/data/app.db "SELECT COALESCE(SUM(duration_seconds), 0) FROM watch_history WHERE DATE(watched_at) = '$TODAY'")
echo "  Videos watched: $WATCH_COUNT"
echo "  Total time: $((WATCH_TIME / 60)) minutes"
echo ""

# Recent errors
echo "⚠️  Recent Errors (last hour):"
ERROR_COUNT=$(journalctl -u youtube-viewer --since "1 hour ago" | grep ERROR | wc -l)
if [ $ERROR_COUNT -eq 0 ]; then
    echo "  ✅ No errors"
else
    echo "  ⚠️  $ERROR_COUNT errors (check logs)"
fi
echo ""

echo "Last updated: $(date '+%Y-%m-%d %H:%M:%S')"
```

**Run anytime:**
```bash
chmod +x scripts/dashboard.sh
./scripts/dashboard.sh
```

## Troubleshooting & Diagnostics

### Log Analysis Commands

**View recent errors:**
```bash
# Application errors
journalctl -u youtube-viewer --since "1 hour ago" | grep ERROR

# All logs for today
journalctl -u youtube-viewer --since today

# Follow logs in real-time
journalctl -u youtube-viewer -f

# Nginx errors
tail -f /var/log/nginx/error.log
```

**Search for specific events:**
```bash
# Failed login attempts
grep "Failed admin login" /var/log/youtube-viewer/app.log

# Slow requests
grep "Slow request" /var/log/youtube-viewer/app.log

# API quota usage
grep "YouTube API" /var/log/youtube-viewer/app.log | tail -20
```

### Performance Diagnostics

**Database performance:**
```bash
# Check database size
ls -lh /opt/youtube-viewer/data/app.db

# Run integrity check
sqlite3 /opt/youtube-viewer/data/app.db "PRAGMA integrity_check;"

# Analyze query performance
sqlite3 /opt/youtube-viewer/data/app.db "EXPLAIN QUERY PLAN SELECT * FROM videos WHERE eligible = 1 ORDER BY RANDOM() LIMIT 9;"
```

**System performance:**
```bash
# Check I/O wait
iostat -x 1 5

# Check memory pressure
free -h

# Check process resource usage
top -p $(pgrep -f "backend.main")
```

## Monitoring Best Practices

### For Parents (Operators)

**Weekly Routine:**
1. Run health check script (2 minutes)
2. Review error logs for patterns (3 minutes)
3. Check disk space and backups (1 minute)
4. Observe child's usage patterns (informal)

**Monthly Routine:**
1. Test backup restoration (10 minutes)
2. Review all logs for trends (10 minutes)
3. Check for security updates (5 minutes)
4. Review content relevance (20 minutes)

**Quarterly Routine:**
1. Full system review and optimization
2. Update documentation if workflow changed
3. Consider adding/removing content sources
4. Review time limits effectiveness

### For Developers

**During Development:**
- Monitor logs for new errors after changes
- Profile slow endpoints before deploying
- Check database query efficiency
- Test under realistic load (10-20 concurrent requests)

**Before Deployment:**
- Review all ERROR logs from testing
- Verify no performance regressions
- Check test coverage hasn't decreased
- Ensure all migrations tested

## Monitoring Tool Integration (Optional)

**If scaling to multiple families, consider:**

**Prometheus + Grafana:**
- Metrics collection and visualization
- Custom dashboards for system health
- Alert manager for automated notifications

**Sentry:**
- Error tracking with context
- Performance monitoring
- Release tracking

**Uptime Kuma:**
- Simple self-hosted uptime monitoring
- Status page for family members
- Email/push notifications

**Log aggregation:**
- Loki + Grafana for log visualization
- Simple to self-host alongside the application

**Note:** For the current single-family deployment, the manual monitoring approach documented above is sufficient and appropriate. Automated monitoring tools should only be added if the application scales to serve multiple families or requires higher availability guarantees.

---

