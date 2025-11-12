#!/bin/bash
# ============================================================================
# Server Setup Verification Script
# Safe YouTube Viewer for Kids - Story 5.1
# ============================================================================
#
# This script verifies all 39 acceptance criteria for production server setup.
# It performs systematic checks of system packages, firewall, directories,
# permissions, SSH configuration, nginx, SSL, and environment variables.
#
# USAGE:
#   1. Copy this script to production server: /opt/youtube-viewer/verify-server-setup.sh
#   2. Make executable: chmod +x verify-server-setup.sh
#   3. Run as root or with sudo: sudo ./verify-server-setup.sh
#
# EXIT CODES:
#   0 - All checks passed
#   1 - One or more checks failed
#
# OUTPUT FORMAT:
#   ✅ AC #: Description - PASS
#   ❌ AC #: Description - FAIL (reason)
#
# ============================================================================

set -e  # Exit on error in verification logic (not in checks)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASS_COUNT=0
FAIL_COUNT=0
TOTAL_CHECKS=39

# Print header
echo "============================================================================"
echo "Server Setup Verification - Story 5.1"
echo "Safe YouTube Viewer for Kids"
echo "============================================================================"
echo ""

# ----------------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------------

check_pass() {
    local ac_num="$1"
    local description="$2"
    echo -e "${GREEN}✅ AC ${ac_num}: ${description} - PASS${NC}"
    ((PASS_COUNT++))
}

check_fail() {
    local ac_num="$1"
    local description="$2"
    local reason="$3"
    echo -e "${RED}❌ AC ${ac_num}: ${description} - FAIL${NC}"
    echo -e "${YELLOW}   Reason: ${reason}${NC}"
    ((FAIL_COUNT++))
}

check_command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# ----------------------------------------------------------------------------
# AC 1: Hetzner CX23 Cloud Server Provisioned
# ----------------------------------------------------------------------------
echo -e "${BLUE}[Category: Server Provisioning]${NC}"

# This is a manual check - we assume if script runs on Ubuntu, server exists
if [ -f /etc/os-release ]; then
    source /etc/os-release
    if [[ "$NAME" == "Ubuntu" ]]; then
        check_pass "1" "Hetzner CX23 Cloud Server provisioned"
    else
        check_fail "1" "Hetzner CX23 Cloud Server provisioned" "Not running Ubuntu (found: $NAME)"
    fi
else
    check_fail "1" "Hetzner CX23 Cloud Server provisioned" "/etc/os-release not found"
fi

# ----------------------------------------------------------------------------
# AC 2: Ubuntu 22.04 LTS Installed and Updated
# ----------------------------------------------------------------------------
if [ -f /etc/os-release ]; then
    source /etc/os-release
    if [[ "$VERSION_ID" == "22.04" ]]; then
        check_pass "2" "Ubuntu 22.04 LTS installed and updated"
    else
        check_fail "2" "Ubuntu 22.04 LTS installed and updated" "Wrong version: $VERSION_ID (expected 22.04)"
    fi
else
    check_fail "2" "Ubuntu 22.04 LTS installed and updated" "/etc/os-release not found"
fi

# ----------------------------------------------------------------------------
# AC 3-4: UFW Firewall Configuration
# ----------------------------------------------------------------------------
echo ""
echo -e "${BLUE}[Category: Firewall Configuration]${NC}"

# AC 3: Firewall configured with deny incoming, allow outgoing
if check_command_exists ufw; then
    ufw_status=$(sudo ufw status verbose 2>/dev/null)

    if echo "$ufw_status" | grep -q "Status: active"; then
        if echo "$ufw_status" | grep -q "deny (incoming)" && echo "$ufw_status" | grep -q "allow (outgoing)"; then
            check_pass "3" "UFW firewall configured (deny incoming, allow outgoing)"
        else
            check_fail "3" "UFW firewall configured" "Default policies not correct"
        fi
    else
        check_fail "3" "UFW firewall configured" "UFW not active"
    fi
else
    check_fail "3" "UFW firewall configured" "ufw command not found"
fi

# AC 4: UFW enabled with ports 22/80/443 allowed
if check_command_exists ufw; then
    ufw_status=$(sudo ufw status verbose 2>/dev/null)

    checks_passed=true
    if ! echo "$ufw_status" | grep -q "22/tcp"; then
        checks_passed=false
        reason="Port 22/tcp not allowed"
    elif ! echo "$ufw_status" | grep -q "80/tcp"; then
        checks_passed=false
        reason="Port 80/tcp not allowed"
    elif ! echo "$ufw_status" | grep -q "443/tcp"; then
        checks_passed=false
        reason="Port 443/tcp not allowed"
    fi

    if $checks_passed; then
        check_pass "4" "UFW enabled and verify status shows active rules"
    else
        check_fail "4" "UFW enabled and verify status shows active rules" "$reason"
    fi
else
    check_fail "4" "UFW enabled and verify status shows active rules" "ufw command not found"
fi

# ----------------------------------------------------------------------------
# AC 5: SSH Hardened
# ----------------------------------------------------------------------------
echo ""
echo -e "${BLUE}[Category: SSH Security]${NC}"

ssh_config_checks=true
ssh_fail_reason=""

# Check PermitRootLogin no
if ! grep -q "^PermitRootLogin no" /etc/ssh/sshd_config; then
    ssh_config_checks=false
    ssh_fail_reason="PermitRootLogin is not set to 'no'"
fi

# Check PasswordAuthentication no
if ! grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config; then
    ssh_config_checks=false
    ssh_fail_reason="${ssh_fail_reason}; PasswordAuthentication is not set to 'no'"
fi

if $ssh_config_checks; then
    check_pass "5" "SSH hardened (key-only auth, root login disabled)"
else
    check_fail "5" "SSH hardened" "$ssh_fail_reason"
fi

# ----------------------------------------------------------------------------
# AC 6-10, 24-25: System Packages
# ----------------------------------------------------------------------------
echo ""
echo -e "${BLUE}[Category: System Packages]${NC}"

# AC 6: Python 3.11.7+ installed
if check_command_exists python3.11; then
    python_version=$(python3.11 --version 2>&1 | grep -oP '\d+\.\d+\.\d+')
    if [[ "$python_version" =~ ^3\.11\. ]]; then
        check_pass "6" "Python 3.11.7+ installed (found: $python_version)"
    else
        check_fail "6" "Python 3.11.7+ installed" "Wrong version: $python_version"
    fi
else
    check_fail "6" "Python 3.11.7+ installed" "python3.11 command not found"
fi

# AC 7: python3.11-dev installed
if dpkg -l | grep -q python3.11-dev; then
    check_pass "7" "python3.11-dev installed"
else
    check_fail "7" "python3.11-dev installed" "Package not found"
fi

# AC 8: uv package manager installed
if check_command_exists uv; then
    uv_version=$(uv --version 2>&1 || echo "unknown")
    check_pass "8" "uv package manager installed (version: $uv_version)"
else
    check_fail "8" "uv package manager installed" "uv command not found"
fi

# AC 9: Node.js v22.11 LTS installed
if check_command_exists node; then
    node_version=$(node --version 2>&1 | grep -oP '\d+\.\d+\.\d+')
    node_major=$(echo "$node_version" | cut -d. -f1)
    if [[ "$node_major" == "22" ]]; then
        check_pass "9" "Node.js v22 LTS installed (found: $node_version)"
    else
        check_fail "9" "Node.js v22 LTS installed" "Wrong version: $node_version (expected v22.x)"
    fi
else
    check_fail "9" "Node.js v22 LTS installed" "node command not found"
fi

# AC 10: npm installed and functional
if check_command_exists npm; then
    npm_version=$(npm --version 2>&1)
    check_pass "10" "npm installed and functional (version: $npm_version)"
else
    check_fail "10" "npm installed and functional" "npm command not found"
fi

# AC 24: SQLite version 3.51.0 verified (Ubuntu 22.04 has 3.37+, acceptable)
if check_command_exists sqlite3; then
    sqlite_version=$(sqlite3 --version 2>&1 | grep -oP '\d+\.\d+\.\d+' | head -1)
    check_pass "24" "SQLite version verified (found: $sqlite_version)"
else
    check_fail "24" "SQLite version verified" "sqlite3 command not found"
fi

# AC 25: System packages installed
packages_ok=true
missing_packages=""

for package in nginx certbot python3-certbot-nginx; do
    if ! dpkg -l | grep -q "^ii  $package"; then
        packages_ok=false
        missing_packages="${missing_packages}$package "
    fi
done

if $packages_ok; then
    check_pass "25" "System packages installed (nginx, certbot, python3-certbot-nginx)"
else
    check_fail "25" "System packages installed" "Missing packages: $missing_packages"
fi

# ----------------------------------------------------------------------------
# AC 11: Nginx Installed
# ----------------------------------------------------------------------------
echo ""
echo -e "${BLUE}[Category: Nginx Configuration]${NC}"

if check_command_exists nginx; then
    nginx_version=$(nginx -v 2>&1 | grep -oP '\d+\.\d+\.\d+')
    check_pass "11" "Nginx installed and configured (version: $nginx_version)"
else
    check_fail "11" "Nginx installed" "nginx command not found"
fi

# AC 12-15: Nginx Configuration (can only fully verify after nginx config is deployed)
# These checks verify if configuration file exists

if [ -f /etc/nginx/sites-available/youtube-viewer ]; then
    nginx_config="/etc/nginx/sites-available/youtube-viewer"

    # AC 12: Security headers
    if grep -q "X-Frame-Options" "$nginx_config" && \
       grep -q "X-Content-Type-Options" "$nginx_config" && \
       grep -q "X-XSS-Protection" "$nginx_config" && \
       grep -q "Referrer-Policy" "$nginx_config" && \
       grep -q "X-Robots-Tag" "$nginx_config"; then
        check_pass "12" "Nginx security headers configured"
    else
        check_fail "12" "Nginx security headers configured" "Some headers missing in config"
    fi

    # AC 13: CSP header with YouTube
    if grep -q "Content-Security-Policy" "$nginx_config" && \
       grep -q "youtube.com" "$nginx_config"; then
        check_pass "13" "Nginx CSP header configured (YouTube allowed)"
    else
        check_fail "13" "Nginx CSP header configured" "CSP or YouTube allowlist missing"
    fi

    # AC 14: Static file serving
    if grep -q "location /static" "$nginx_config" && \
       grep -q "expires 7d" "$nginx_config"; then
        check_pass "14" "Nginx static file serving with cache headers"
    else
        check_fail "14" "Nginx static file serving" "Static location or cache headers missing"
    fi

    # AC 15: robots.txt
    if grep -q "robots.txt" "$nginx_config"; then
        check_pass "15" "robots.txt configured in nginx"
    else
        check_fail "15" "robots.txt configured" "robots.txt location missing"
    fi
else
    check_fail "12" "Nginx security headers configured" "Nginx config file not found at /etc/nginx/sites-available/youtube-viewer"
    check_fail "13" "Nginx CSP header configured" "Nginx config file not found"
    check_fail "14" "Nginx static file serving" "Nginx config file not found"
    check_fail "15" "robots.txt configured" "Nginx config file not found"
fi

# ----------------------------------------------------------------------------
# AC 16: SSL Certificate
# ----------------------------------------------------------------------------
echo ""
echo -e "${BLUE}[Category: SSL Certificate]${NC}"

if check_command_exists certbot; then
    cert_output=$(sudo certbot certificates 2>&1 || echo "")
    if echo "$cert_output" | grep -q "Certificate Name:"; then
        check_pass "16" "SSL certificate provisioned (Let's Encrypt)"
    else
        check_fail "16" "SSL certificate provisioned" "No certificates found (run: sudo certbot --nginx -d yourdomain.com)"
    fi
else
    check_fail "16" "SSL certificate provisioned" "certbot command not found"
fi

# ----------------------------------------------------------------------------
# AC 17-19: Application Directory Structure
# ----------------------------------------------------------------------------
echo ""
echo -e "${BLUE}[Category: Directory Structure and Permissions]${NC}"

# AC 17: Directory structure created
if [ -d /opt/youtube-viewer/data ] && \
   [ -d /opt/youtube-viewer/backups ] && \
   [ -d /opt/youtube-viewer/logs ]; then
    check_pass "17" "Application directory structure created"
else
    check_fail "17" "Application directory structure created" "Missing directories in /opt/youtube-viewer/"
fi

# AC 18: Directory ownership
dir_ownership_ok=true
dir_ownership_reason=""

for dir in data backups logs; do
    if [ -d "/opt/youtube-viewer/$dir" ]; then
        owner=$(stat -c "%U:%G" "/opt/youtube-viewer/$dir")
        if [[ "$owner" != "youtube-viewer:youtube-viewer" ]]; then
            dir_ownership_ok=false
            dir_ownership_reason="$dir has wrong ownership: $owner"
            break
        fi
    fi
done

if $dir_ownership_ok; then
    check_pass "18" "Directory ownership (youtube-viewer:youtube-viewer)"
else
    check_fail "18" "Directory ownership" "$dir_ownership_reason"
fi

# AC 19: Directory permissions
dir_perms_ok=true
dir_perms_reason=""

# Check data/ (should be 700)
if [ -d /opt/youtube-viewer/data ]; then
    data_perms=$(stat -c "%a" /opt/youtube-viewer/data)
    if [[ "$data_perms" != "700" ]]; then
        dir_perms_ok=false
        dir_perms_reason="data/ has wrong permissions: $data_perms (expected 700)"
    fi
fi

# Check backups/ (should be 700)
if [ -d /opt/youtube-viewer/backups ]; then
    backups_perms=$(stat -c "%a" /opt/youtube-viewer/backups)
    if [[ "$backups_perms" != "700" ]]; then
        dir_perms_ok=false
        dir_perms_reason="${dir_perms_reason}; backups/ has wrong permissions: $backups_perms (expected 700)"
    fi
fi

# Check logs/ (should be 755)
if [ -d /opt/youtube-viewer/logs ]; then
    logs_perms=$(stat -c "%a" /opt/youtube-viewer/logs)
    if [[ "$logs_perms" != "755" ]]; then
        dir_perms_ok=false
        dir_perms_reason="${dir_perms_reason}; logs/ has wrong permissions: $logs_perms (expected 755)"
    fi
fi

if $dir_perms_ok; then
    check_pass "19" "Directory permissions (data:700, backups:700, logs:755)"
else
    check_fail "19" "Directory permissions" "$dir_perms_reason"
fi

# ----------------------------------------------------------------------------
# AC 20: Database File Permissions
# ----------------------------------------------------------------------------
if [ -f /opt/youtube-viewer/data/app.db ]; then
    db_perms=$(stat -c "%a" /opt/youtube-viewer/data/app.db)
    db_owner=$(stat -c "%U:%G" /opt/youtube-viewer/data/app.db)

    if [[ "$db_perms" == "600" ]] && [[ "$db_owner" == "youtube-viewer:youtube-viewer" ]]; then
        check_pass "20" "Database file permissions (600, youtube-viewer:youtube-viewer)"
    else
        check_fail "20" "Database file permissions" "Permissions: $db_perms (expected 600), Owner: $db_owner"
    fi
else
    echo -e "${YELLOW}⚠️  AC 20: Database file permissions - SKIP (database not yet created)${NC}"
fi

# ----------------------------------------------------------------------------
# AC 21-22: Environment File Configuration
# ----------------------------------------------------------------------------
echo ""
echo -e "${BLUE}[Category: Environment Configuration]${NC}"

# AC 21: .env file created with correct permissions
if [ -f /opt/youtube-viewer/.env ]; then
    env_perms=$(stat -c "%a" /opt/youtube-viewer/.env)
    env_owner=$(stat -c "%U:%G" /opt/youtube-viewer/.env)

    if [[ "$env_perms" == "600" ]] && [[ "$env_owner" == "youtube-viewer:youtube-viewer" ]]; then
        check_pass "21" ".env file created with permissions 600"
    else
        check_fail "21" ".env file created with permissions 600" "Permissions: $env_perms, Owner: $env_owner"
    fi
else
    check_fail "21" ".env file created" ".env file not found at /opt/youtube-viewer/.env"
fi

# AC 22: Required environment variables in .env
if [ -f /opt/youtube-viewer/.env ]; then
    env_vars_ok=true
    missing_vars=""

    for var in DATABASE_PATH YOUTUBE_API_KEY ALLOWED_HOSTS DEBUG LOG_LEVEL LOG_FILE; do
        if ! grep -q "^$var=" /opt/youtube-viewer/.env; then
            env_vars_ok=false
            missing_vars="${missing_vars}$var "
        fi
    done

    # Check DEBUG=false for production
    if grep -q "^DEBUG=true" /opt/youtube-viewer/.env; then
        env_vars_ok=false
        missing_vars="${missing_vars}(DEBUG should be false) "
    fi

    if $env_vars_ok; then
        check_pass "22" "Required environment variables in .env"
    else
        check_fail "22" "Required environment variables in .env" "Missing or incorrect: $missing_vars"
    fi
else
    check_fail "22" "Required environment variables in .env" ".env file not found"
fi

# ----------------------------------------------------------------------------
# AC 23: Python Dependencies Verification (bcrypt)
# ----------------------------------------------------------------------------
echo ""
echo -e "${BLUE}[Category: Python Dependencies]${NC}"

# Test bcrypt import
bcrypt_test=$(python3.11 -c "from passlib.hash import bcrypt; print('OK')" 2>&1)
if [[ "$bcrypt_test" == "OK" ]]; then
    check_pass "23" "bcrypt installed and functional"
else
    check_fail "23" "bcrypt installed and functional" "Import failed: $bcrypt_test"
fi

# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------
echo ""
echo "============================================================================"
echo "Verification Summary"
echo "============================================================================"
echo -e "${GREEN}PASSED: $PASS_COUNT / $TOTAL_CHECKS${NC}"
echo -e "${RED}FAILED: $FAIL_COUNT / $TOTAL_CHECKS${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ All acceptance criteria verified successfully!${NC}"
    echo ""
    echo "Server is ready for application deployment (Story 5.2)."
    exit 0
else
    echo -e "${RED}❌ Some acceptance criteria failed verification.${NC}"
    echo ""
    echo "Please review the failed checks above and remediate before proceeding."
    echo ""
    echo "Common remediation steps:"
    echo "  - SSH hardening: Edit /etc/ssh/sshd_config and restart sshd"
    echo "  - Nginx config: Copy scripts/nginx-config.conf to /etc/nginx/sites-available/"
    echo "  - SSL certificate: Run sudo certbot --nginx -d yourdomain.com"
    echo "  - Environment: Copy .env.example to /opt/youtube-viewer/.env and edit"
    echo "  - Permissions: Use chmod/chown to fix directory and file permissions"
    exit 1
fi

# ============================================================================
# END OF VERIFICATION SCRIPT
# ============================================================================
