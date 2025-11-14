#!/usr/bin/env bash
#
# Health Check Script for Safe YouTube Viewer
#
# Story 5.4 AC 20, 22, 23: Comprehensive health checks with Norwegian output
#
# Usage:
#   ./scripts/check-health.sh
#
# This script checks:
# 1. Service status (youtube-viewer, nginx)
# 2. Disk space (warns if <20% free)
# 3. Recent errors (last 24 hours from journalctl)
# 4. Database status (size, integrity)
# 5. Backup status (last backup timestamp)
#
# Alert thresholds (Story 5.4 AC 23):
# - Service down: youtube-viewer or nginx not running
# - Disk space <20%: High usage warning
# - Database errors: Any errors in last 24 hours
#
# Run weekly as part of maintenance checklist (Story 5.4 AC 24)

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

DB_PATH="${DB_PATH:-/opt/youtube-viewer/data/app.db}"
BACKUP_DIR="${BACKUP_DIR:-/opt/youtube-viewer/backups}"
DATA_DIR="${DATA_DIR:-/opt/youtube-viewer}"
DISK_WARNING_THRESHOLD=80  # Warn if >80% used (<20% free)

# Colors for output (optional, disabled if not terminal)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'  # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

print_header() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║   Safe YouTube Viewer - Helsekontroll                      ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

print_section() {
    echo ""
    echo "──────────────────────────────────────────────────────────"
    echo "  $1"
    echo "──────────────────────────────────────────────────────────"
}

# =============================================================================
# HEALTH CHECKS
# =============================================================================

check_service_status() {
    print_section "📊 Tjeneste Status"

    # Check youtube-viewer service
    if systemctl is-active --quiet youtube-viewer.service 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Applikasjon (youtube-viewer): Kjører"
    else
        echo -e "  ${RED}✗${NC} Applikasjon (youtube-viewer): Stoppet eller feilet"
        echo -e "    ${RED}⚠️  ADVARSEL: Tjeneste er nede${NC}"
    fi

    # Check nginx service
    if systemctl is-active --quiet nginx.service 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Webserver (nginx): Kjører"
    else
        echo -e "  ${RED}✗${NC} Webserver (nginx): Stoppet eller feilet"
        echo -e "    ${RED}⚠️  ADVARSEL: Webserver er nede${NC}"
    fi
}

check_disk_space() {
    print_section "💾 Diskplass"

    if [[ ! -d "${DATA_DIR}" ]]; then
        echo -e "  ${YELLOW}⚠${NC}  Data-katalog ikke funnet: ${DATA_DIR}"
        return
    fi

    # Get disk usage percentage for the data directory
    local usage_line
    usage_line=$(df -h "${DATA_DIR}" | tail -1)

    local filesystem used available percent mountpoint
    read -r filesystem used available percent mountpoint <<< "${usage_line}"

    # Remove % sign from percent
    local percent_num="${percent%\%}"

    echo "  Filsystem: ${filesystem}"
    echo "  Brukt: ${used} / Tilgjengelig: ${available}"
    echo "  Monteringspunkt: ${mountpoint}"

    # Check against threshold (Story 5.4 AC 23: warn if <20% free, i.e., >80% used)
    if [[ ${percent_num} -ge ${DISK_WARNING_THRESHOLD} ]]; then
        local free_percent=$((100 - percent_num))
        echo -e "  ${RED}⚠️  ADVARSEL: Diskplass lav (${free_percent}% ledig, mindre enn 20%)${NC}"
        echo -e "    Handling anbefalt: Sjekk backup-oppbevaring, loggfilstørrelser"
    else
        echo -e "  ${GREEN}✓${NC} Diskplass: ${percent} brukt (OK)"
    fi
}

check_recent_errors() {
    print_section "⚠️  Siste Feil (siste 24 timer)"

    # Count errors in last 24 hours
    local error_count=0

    if command -v journalctl >/dev/null 2>&1; then
        error_count=$(journalctl -u youtube-viewer.service --since "24 hours ago" --no-pager 2>/dev/null | grep -i ERROR | wc -l || echo 0)

        if [[ ${error_count} -eq 0 ]]; then
            echo -e "  ${GREEN}✓${NC} Ingen feil funnet"
        else
            echo -e "  ${YELLOW}⚠${NC}  ${error_count} feil funnet (Story 5.4 AC 23: Database error alert)"
            echo ""
            echo "  Siste 5 feilmeldinger:"
            journalctl -u youtube-viewer.service --since "24 hours ago" --no-pager 2>/dev/null | grep -i ERROR | tail -5 | sed 's/^/    /' || true
            echo ""
            echo -e "  ${YELLOW}Handling anbefalt: Se gjennom fullstendige logger${NC}"
            echo "    Kommando: journalctl -u youtube-viewer.service --since '24 hours ago' | grep ERROR"
        fi
    else
        echo "  ⚠️  journalctl ikke tilgjengelig (kan ikke sjekke feil)"
    fi
}

check_database_status() {
    print_section "🗄️  Database Status"

    if [[ ! -f "${DB_PATH}" ]]; then
        echo -e "  ${RED}✗${NC} Database ikke funnet: ${DB_PATH}"
        return
    fi

    # Database size
    local db_size
    db_size=$(du -h "${DB_PATH}" | cut -f1)
    echo "  Størrelse: ${db_size}"

    # Database integrity check (quick_check is faster than integrity_check)
    if command -v sqlite3 >/dev/null 2>&1; then
        echo -n "  Integritet: "
        local integrity_result
        integrity_result=$(sqlite3 "${DB_PATH}" "PRAGMA quick_check;" 2>&1 || echo "ERROR")

        if [[ "${integrity_result}" == "ok" ]]; then
            echo -e "${GREEN}✓${NC} OK"
        else
            echo -e "${RED}✗${NC} FEIL"
            echo -e "  ${RED}⚠️  ADVARSEL: Database integritet feil${NC}"
            echo "    Resultat: ${integrity_result}"
            echo -e "    ${RED}Handling anbefalt: Vurder gjenoppretting fra backup${NC}"
        fi
    else
        echo "  ⚠️  sqlite3 ikke tilgjengelig (kan ikke sjekke integritet)"
    fi

    # Check for WAL files
    if [[ -f "${DB_PATH}-wal" ]]; then
        local wal_size
        wal_size=$(du -h "${DB_PATH}-wal" | cut -f1)
        echo "  WAL-fil størrelse: ${wal_size}"
    fi
}

check_backup_status() {
    print_section "💾 Backup Status"

    if [[ ! -d "${BACKUP_DIR}" ]]; then
        echo -e "  ${YELLOW}⚠${NC}  Backup-katalog ikke funnet: ${BACKUP_DIR}"
        return
    fi

    # Find most recent backup
    local latest_backup
    latest_backup=$(ls -1t "${BACKUP_DIR}"/app-*.db 2>/dev/null | head -1 || echo "")

    if [[ -z "${latest_backup}" ]]; then
        echo -e "  ${YELLOW}⚠${NC}  Ingen backups funnet i ${BACKUP_DIR}"
        echo "    Handling anbefalt: Verifiser backup-timer er aktivert"
        echo "    Kommando: systemctl status youtube-viewer-backup.timer"
        return
    fi

    # Get backup timestamp
    local backup_name
    backup_name=$(basename "${latest_backup}")
    local backup_size
    backup_size=$(du -h "${latest_backup}" | cut -f1)

    # Get file modification time in seconds since epoch
    local backup_mtime
    backup_mtime=$(stat -c %Y "${latest_backup}" 2>/dev/null || stat -f %m "${latest_backup}" 2>/dev/null || echo 0)
    local current_time
    current_time=$(date +%s)
    local hours_ago=$(( (current_time - backup_mtime) / 3600 ))

    echo "  Siste backup: ${backup_name}"
    echo "  Størrelse: ${backup_size}"
    echo "  Alder: ${hours_ago} timer siden"

    # Warn if last backup is >48 hours old
    if [[ ${hours_ago} -gt 48 ]]; then
        echo -e "  ${RED}⚠️  ADVARSEL: Siste backup er over 48 timer gammel${NC}"
        echo "    Handling anbefalt: Sjekk backup-timer og tjeneste"
        echo "    Kommando: systemctl status youtube-viewer-backup.timer"
    else
        echo -e "  ${GREEN}✓${NC} Backup er oppdatert"
    fi

    # Count total backups
    local backup_count
    backup_count=$(ls -1 "${BACKUP_DIR}"/app-*.db 2>/dev/null | wc -l)
    echo "  Totalt antall backups: ${backup_count}"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    print_header

    check_service_status
    check_disk_space
    check_recent_errors
    check_database_status
    check_backup_status

    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  Helsekontroll fullført"
    echo "════════════════════════════════════════════════════════════"
    echo ""
}

main "$@"
