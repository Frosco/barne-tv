#!/usr/bin/env bash
#
# Real-Time Dashboard Script for Safe YouTube Viewer
#
# Story 5.4 AC 21, 22: Real-time system status with Norwegian output
#
# Usage:
#   ./scripts/dashboard.sh
#
# Displays:
# 1. Service status (youtube-viewer, nginx)
# 2. Resource usage (CPU, memory, disk)
# 3. Today's activity (videos watched, total watch time)
# 4. Recent errors (last hour)
#
# Norwegian output for parent readability (Story 5.4 AC 22)

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

DB_PATH="${DB_PATH:-/opt/youtube-viewer/data/app.db}"
DATA_DIR="${DATA_DIR:-/opt/youtube-viewer}"

# Colors for output (optional, disabled if not terminal)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    NC='\033[0m'  # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    NC=''
fi

# =============================================================================
# HEADER
# =============================================================================

print_header() {
    clear
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║   YouTube Viewer - System Dashboard                        ║"
    echo "║   $(date +'%d.%m.%Y %H:%M:%S %Z')                                    ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

# =============================================================================
# DASHBOARD SECTIONS
# =============================================================================

show_service_status() {
    echo -e "${BLUE}📊 Tjenester:${NC}"

    # Check youtube-viewer service
    if systemctl is-active --quiet youtube-viewer.service 2>/dev/null; then
        echo -e "  ${GREEN}✅${NC} Applikasjon: Kjører"
    else
        echo -e "  ${RED}❌${NC} Applikasjon: Stoppet"
    fi

    # Check nginx service
    if systemctl is-active --quiet nginx.service 2>/dev/null; then
        echo -e "  ${GREEN}✅${NC} Nginx: Kjører"
    else
        echo -e "  ${RED}❌${NC} Nginx: Stoppet"
    fi

    echo ""
}

show_resource_usage() {
    echo -e "${BLUE}💻 Ressurser:${NC}"

    # CPU usage (5-second average)
    local cpu_usage
    if command -v mpstat >/dev/null 2>&1; then
        cpu_usage=$(mpstat 1 1 | awk '/Average/ {print 100 - $NF}' | cut -d'.' -f1)
        echo "  CPU: ${cpu_usage}%"
    elif [[ -f /proc/loadavg ]]; then
        local load_avg
        load_avg=$(cat /proc/loadavg | cut -d' ' -f1)
        echo "  Load Average (1m): ${load_avg}"
    fi

    # Memory usage
    if command -v free >/dev/null 2>&1; then
        local mem_info
        mem_info=$(free -h | awk '/^Mem:/ {print $3 " / " $2}')
        echo "  Minne: ${mem_info}"
    fi

    # Disk usage
    if [[ -d "${DATA_DIR}" ]]; then
        local disk_info
        disk_info=$(df -h "${DATA_DIR}" | awk 'NR==2 {print $3 " / " $2 " (" $5 " brukt)"}')
        echo "  Disk: ${disk_info}"
    fi

    echo ""
}

show_todays_activity() {
    echo -e "${BLUE}📺 I dag aktivitet:${NC}"

    if [[ ! -f "${DB_PATH}" ]]; then
        echo "  ⚠️  Database ikke tilgjengelig"
        echo ""
        return
    fi

    if ! command -v sqlite3 >/dev/null 2>&1; then
        echo "  ⚠️  sqlite3 ikke tilgjengelig"
        echo ""
        return
    fi

    # Get today's date in UTC (Story 5.4 AC 21: query watch_history for today's UTC date)
    local today_utc
    today_utc=$(date -u +"%Y-%m-%d")

    # Query watch_history for today's activity
    # Story 5.4 AC 21: Count videos watched and total watch time in minutes
    local query_result
    query_result=$(sqlite3 "${DB_PATH}" <<EOF
SELECT
    COUNT(*) as video_count,
    COALESCE(SUM(duration_watched_seconds) / 60, 0) as total_minutes
FROM watch_history
WHERE DATE(watched_at) = DATE('${today_utc}');
EOF
2>/dev/null || echo "0|0")

    local video_count total_minutes
    IFS='|' read -r video_count total_minutes <<< "${query_result}"

    echo "  Videoer sett: ${video_count}"
    echo "  Total tid: ${total_minutes} minutter"

    # Show time limit status if we have data
    if [[ ${video_count} -gt 0 ]]; then
        # Get daily limit setting
        local daily_limit
        daily_limit=$(sqlite3 "${DB_PATH}" "SELECT value FROM settings WHERE key = 'daily_limit_minutes';" 2>/dev/null || echo "30")

        local remaining=$((daily_limit - total_minutes))
        if [[ ${remaining} -lt 0 ]]; then
            remaining=0
        fi

        echo "  Tid gjenstående: ${remaining} minutter (grense: ${daily_limit} min)"
    fi

    echo ""
}

show_recent_errors() {
    echo -e "${BLUE}⚠️  Siste feil (siste time):${NC}"

    if ! command -v journalctl >/dev/null 2>&1; then
        echo "  ⚠️  journalctl ikke tilgjengelig"
        echo ""
        return
    fi

    # Count errors in last hour
    local error_count=0
    error_count=$(journalctl -u youtube-viewer.service --since "1 hour ago" --no-pager 2>/dev/null | grep -i ERROR | wc -l || echo 0)

    if [[ ${error_count} -eq 0 ]]; then
        echo -e "  ${GREEN}✅${NC} Ingen feil"
    else
        echo -e "  ${YELLOW}⚠️ ${NC} ${error_count} feil (sjekk logger)"
        echo ""
        echo "  Siste 3 feilmeldinger:"
        journalctl -u youtube-viewer.service --since "1 hour ago" --no-pager 2>/dev/null | grep -i ERROR | tail -3 | sed 's/^/    /' || true
    fi

    echo ""
}

show_footer() {
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "For detaljert helsekontroll, kjør: ./scripts/check-health.sh"
    echo "For å oppdatere dashboard, kjør kommandoen på nytt"
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    print_header
    show_service_status
    show_resource_usage
    show_todays_activity
    show_recent_errors
    show_footer
}

main "$@"
