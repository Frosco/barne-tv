#!/usr/bin/env bash
#
# Database Restore Script for Safe YouTube Viewer
#
# Story 5.4 AC 17-19: Database restore with integrity verification
#
# Usage:
#   sudo ./scripts/restore.sh <backup-filename>
#   Example: sudo ./scripts/restore.sh app-20251112-020000.db
#
# This script:
# 1. Validates backup file exists
# 2. Stops youtube-viewer.service
# 3. Backs up current database (safety backup)
# 4. Copies backup to active database location
# 5. Sets secure permissions and ownership
# 6. Runs database integrity check
# 7. Rolls back if integrity check fails
# 8. Restarts service and verifies health endpoint
#
# CRITICAL: Must run as root (uses systemctl, needs file permissions)
# Exit codes: 0=success, 1=failure

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# =============================================================================
# CONFIGURATION
# =============================================================================

# Database paths (production defaults, can be overridden)
DB_PATH="${DB_PATH:-/opt/youtube-viewer/data/app.db}"
BACKUP_DIR="${BACKUP_DIR:-/opt/youtube-viewer/backups}"
LOG_FILE="${LOG_FILE:-/var/log/youtube-viewer/backups.log}"
HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-http://localhost:8000/health}"

# =============================================================================
# LOGGING
# =============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() {
    log "INFO" "$@"
}

log_error() {
    log "ERROR" "$@"
}

# =============================================================================
# VALIDATION
# =============================================================================

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo "ERROR: This script must be run as root (uses systemctl and file permissions)"
    echo "Usage: sudo $0 <backup-filename>"
    exit 1
fi

# Check backup filename argument
if [[ $# -ne 1 ]]; then
    echo "ERROR: Missing backup filename argument"
    echo "Usage: sudo $0 <backup-filename>"
    echo "Example: sudo $0 app-20251112-020000.db"
    echo ""
    echo "Available backups:"
    ls -1t "${BACKUP_DIR}"/app-*.db 2>/dev/null | head -10 || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# =============================================================================
# MAIN RESTORE LOGIC
# =============================================================================

main() {
    log_info "=== Starting database restore ==="
    log_info "Backup file: ${BACKUP_FILE}"

    # Verify backup file exists (Story 5.4 AC 18)
    if [[ ! -f "${BACKUP_PATH}" ]]; then
        log_error "Backup file not found: ${BACKUP_PATH}"
        log_error "Available backups:"
        ls -1t "${BACKUP_DIR}"/app-*.db 2>/dev/null | head -10 || log_error "  No backups found"
        exit 1
    fi

    log_info "Backup file verified: ${BACKUP_PATH}"

    # Stop youtube-viewer service (Story 5.4 AC 18)
    log_info "Stopping youtube-viewer.service..."
    if ! systemctl stop youtube-viewer.service; then
        log_error "Failed to stop service"
        exit 1
    fi
    log_info "Service stopped successfully"

    # Backup current database before restoring (Story 5.4 AC 18)
    local safety_backup="${DB_PATH}.before-restore"
    log_info "Creating safety backup: ${safety_backup}"
    if ! cp "${DB_PATH}" "${safety_backup}"; then
        log_error "Failed to create safety backup"
        log_info "Restarting service..."
        systemctl start youtube-viewer.service
        exit 1
    fi
    log_info "Safety backup created successfully"

    # Copy from backup to active database (Story 5.4 AC 18)
    log_info "Restoring database from backup..."
    if ! cp "${BACKUP_PATH}" "${DB_PATH}"; then
        log_error "Failed to copy backup to ${DB_PATH}"
        log_info "Restoring safety backup..."
        cp "${safety_backup}" "${DB_PATH}"
        log_info "Restarting service..."
        systemctl start youtube-viewer.service
        exit 1
    fi
    log_info "Database file restored"

    # Set permissions: 600 (Story 5.4 AC 18)
    log_info "Setting database permissions to 600..."
    chmod 600 "${DB_PATH}"

    # Set ownership: youtube-viewer:youtube-viewer (Story 5.4 AC 18)
    log_info "Setting database ownership to youtube-viewer:youtube-viewer..."
    chown youtube-viewer:youtube-viewer "${DB_PATH}"

    # Run integrity check (Story 5.4 AC 19)
    log_info "Running database integrity check..."
    local integrity_result
    integrity_result=$(sqlite3 "${DB_PATH}" "PRAGMA integrity_check;" 2>&1)

    if [[ "${integrity_result}" != "ok" ]]; then
        log_error "Database integrity check FAILED: ${integrity_result}"
        log_error "Restoring safety backup..."

        # Restore the safety backup (Story 5.4 AC 19 - rollback on failure)
        if ! cp "${safety_backup}" "${DB_PATH}"; then
            log_error "CRITICAL: Failed to restore safety backup!"
            exit 1
        fi

        log_info "Safety backup restored successfully"
        log_info "Restarting service with original database..."
        systemctl start youtube-viewer.service

        log_error "Restore FAILED due to integrity check failure"
        exit 1
    fi

    log_info "Database integrity check PASSED: ${integrity_result}"

    # Restart service (Story 5.4 AC 18)
    log_info "Restarting youtube-viewer.service..."
    if ! systemctl start youtube-viewer.service; then
        log_error "Failed to start service"
        exit 1
    fi
    log_info "Service started successfully"

    # Wait for service to initialize (Story 5.4 AC 18)
    log_info "Waiting 5 seconds for service initialization..."
    sleep 5

    # Verify health endpoint (Story 5.4 AC 18)
    log_info "Verifying health endpoint..."
    local health_response
    local health_status

    health_response=$(curl -s -w "\n%{http_code}" "${HEALTH_ENDPOINT}" 2>&1 || true)
    health_status=$(echo "${health_response}" | tail -1)

    if [[ "${health_status}" != "200" ]]; then
        log_error "Health endpoint check FAILED (HTTP ${health_status})"
        log_error "Service may not be functioning correctly"
        log_error "Check service status: systemctl status youtube-viewer"
        exit 1
    fi

    # Parse JSON to check database field
    local health_body
    health_body=$(echo "${health_response}" | head -n-1)

    if echo "${health_body}" | grep -q '"database":"connected"' || echo "${health_body}" | grep -q '"database": "connected"'; then
        log_info "Health endpoint verification PASSED (database connected)"
    else
        log_error "Health endpoint check FAILED (database not connected)"
        log_error "Response: ${health_body}"
        exit 1
    fi

    # Success!
    log_info "=== Database restore completed successfully ==="
    log_info "Restored from: ${BACKUP_FILE}"
    log_info "Safety backup available at: ${safety_backup}"
    log_info "Service is running and healthy"

    exit 0
}

# =============================================================================
# SCRIPT ENTRY POINT
# =============================================================================

main "$@"
