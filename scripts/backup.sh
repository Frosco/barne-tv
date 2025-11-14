#!/usr/bin/env bash
#
# Database Backup Script for Safe YouTube Viewer
#
# Story 5.4 AC 9-13, 16: Automated database backup with WAL checkpoint and retention
#
# Usage:
#   ./scripts/backup.sh
#
# This script:
# 1. Runs WAL checkpoint to flush all pending writes
# 2. Creates timestamped backup of database
# 3. Sets secure permissions (600) on backup file
# 4. Deletes backups older than 7 days (retention policy)
# 5. Logs all operations to /var/log/youtube-viewer/backups.log
#
# Designed to run as: youtube-viewer user via systemd timer
# Exit codes: 0=success, 1=failure

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# =============================================================================
# CONFIGURATION
# =============================================================================

# Database paths (production defaults, can be overridden)
DB_PATH="${DB_PATH:-/opt/youtube-viewer/data/app.db}"
BACKUP_DIR="${BACKUP_DIR:-/opt/youtube-viewer/backups}"
LOG_FILE="${LOG_FILE:-/var/log/youtube-viewer/backups.log}"
RETENTION_DAYS=7

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
# MAIN BACKUP LOGIC
# =============================================================================

main() {
    log_info "Starting database backup..."

    # Verify database file exists
    if [[ ! -f "${DB_PATH}" ]]; then
        log_error "Database file not found: ${DB_PATH}"
        exit 1
    fi

    # Create backup directory if it doesn't exist
    if [[ ! -d "${BACKUP_DIR}" ]]; then
        log_info "Creating backup directory: ${BACKUP_DIR}"
        mkdir -p "${BACKUP_DIR}"
        chmod 700 "${BACKUP_DIR}"
    fi

    # Generate backup filename: app-YYYYMMDD-HHMMSS.db
    local timestamp
    timestamp=$(date -u +"%Y%m%d-%H%M%S")
    local backup_file="${BACKUP_DIR}/app-${timestamp}.db"

    log_info "Backup file: ${backup_file}"

    # Run WAL checkpoint to flush all pending writes (Story 5.4 AC 10)
    log_info "Running WAL checkpoint..."
    if ! sqlite3 "${DB_PATH}" "PRAGMA wal_checkpoint(FULL);" >> "${LOG_FILE}" 2>&1; then
        log_error "WAL checkpoint failed"
        exit 1
    fi
    log_info "WAL checkpoint completed successfully"

    # Copy database to backup location
    log_info "Copying database to backup..."
    if ! cp "${DB_PATH}" "${backup_file}"; then
        log_error "Failed to copy database to ${backup_file}"
        exit 1
    fi

    # Set secure permissions: 600 (read/write owner only) (Story 5.4 AC 12)
    log_info "Setting backup file permissions to 600..."
    chmod 600 "${backup_file}"

    # Set ownership if running as root (for systemd service)
    if [[ $EUID -eq 0 ]]; then
        chown youtube-viewer:youtube-viewer "${backup_file}"
        log_info "Set ownership to youtube-viewer:youtube-viewer"
    fi

    log_info "Backup created successfully: ${backup_file}"

    # Cleanup: Delete backups older than RETENTION_DAYS (Story 5.4 AC 16)
    log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."
    local deleted_count=0

    # Find and delete old backups, log each deletion
    while IFS= read -r old_backup; do
        if [[ -n "${old_backup}" ]]; then
            log_info "Deleting old backup: ${old_backup}"
            rm -f "${old_backup}"
            ((deleted_count++))
        fi
    done < <(find "${BACKUP_DIR}" -name "app-*.db" -type f -mtime +${RETENTION_DAYS} 2>/dev/null || true)

    if [[ ${deleted_count} -gt 0 ]]; then
        log_info "Deleted ${deleted_count} old backup(s)"
    else
        log_info "No old backups to delete"
    fi

    # Count remaining backups
    local backup_count
    backup_count=$(find "${BACKUP_DIR}" -name "app-*.db" -type f | wc -l)
    log_info "Total backups in directory: ${backup_count}"

    log_info "Backup completed successfully"
    exit 0
}

# =============================================================================
# SCRIPT ENTRY POINT
# =============================================================================

main "$@"
