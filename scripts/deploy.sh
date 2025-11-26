#!/bin/bash
################################################################################
# deploy.sh - Automated Deployment Script for Safe YouTube Viewer for Kids
################################################################################
#
# Purpose:
#   Automates deployment of application updates with quality gates, testing
#   validation, and automatic rollback on failure.
#
# Usage:
#   cd /opt/youtube-viewer/app
#   ./scripts/deploy.sh
#
# Requirements:
#   - Git repository with remote configured
#   - User in youtube-viewer group
#   - Sudo permission for systemctl commands
#   - Environment file at /opt/youtube-viewer/.env
#   - uv (Python package manager)
#   - npm (Node package manager)
#   - sqlite3 command-line tool
#
# Exit Codes:
#   0 - Deployment successful
#   1 - Deployment failed (see logs for details)
#
# Log Location:
#   /opt/youtube-viewer/logs/deployments.log
#
################################################################################

# Strict error handling
set -euo pipefail

# Configuration
readonly APP_DIR="/opt/youtube-viewer/app"
readonly ENV_FILE="/opt/youtube-viewer/.env"
readonly DB_PATH="/opt/youtube-viewer/data/app.db"
readonly LOG_DIR="/opt/youtube-viewer/logs"
readonly LOG_FILE="${LOG_DIR}/deployments.log"
readonly SERVICE_NAME="youtube-viewer.service"
readonly HEALTH_URL="http://localhost:8000/health"

# Color codes for output (optional, for terminal visibility)
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Global variables for rollback
PREVIOUS_COMMIT=""
NEW_COMMIT=""
DEPLOYMENT_FAILED=false

################################################################################
# Logging Functions
################################################################################

# Log message with ISO 8601 timestamp
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Create log directory if it doesn't exist
    mkdir -p "${LOG_DIR}"

    # Write to log file
    echo "[${timestamp}] [${level}] ${message}" >> "${LOG_FILE}"

    # Also write to stdout with color
    case "${level}" in
        INFO)
            echo -e "${GREEN}[INFO]${NC} ${message}"
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} ${message}"
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} ${message}"
            ;;
        *)
            echo "[${level}] ${message}"
            ;;
    esac
}

log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_error() {
    log "ERROR" "$@"
}

################################################################################
# Error Handler and Rollback
################################################################################

# Error handler function (called on any command failure)
handle_error() {
    local exit_code=$?
    local line_number=$1

    log_error "Command failed with exit code ${exit_code} at line ${line_number}"
    log_error "DEPLOYMENT FAILED - Initiating rollback procedure"

    DEPLOYMENT_FAILED=true

    # Trigger rollback if we have a previous commit to roll back to
    if [[ -n "${PREVIOUS_COMMIT}" ]]; then
        perform_rollback
    else
        log_error "No previous commit available for rollback"
    fi

    exit 1
}

# Set up trap to catch errors
trap 'handle_error ${LINENO}' ERR

################################################################################
# Rollback Procedure
################################################################################

perform_rollback() {
    log_info "=========================================="
    log_info "Starting Rollback Procedure"
    log_info "=========================================="

    log_info "Rolling back to commit: ${PREVIOUS_COMMIT}"

    # Navigate to app directory
    cd "${APP_DIR}"

    # Restore previous code
    log_info "Restoring previous code..."
    if git reset --hard "${PREVIOUS_COMMIT}"; then
        log_info "Code restored to commit ${PREVIOUS_COMMIT}"
    else
        log_error "Failed to restore previous commit"
        exit 1
    fi

    # Rebuild frontend (static/ is gitignored)
    log_info "Rebuilding frontend..."
    cd frontend
    local build_output
    if build_output=$(npm run build 2>&1); then
        log_info "Frontend rebuilt successfully"
    else
        log_error "Failed to rebuild frontend during rollback"
        log_error "Build output: ${build_output}"
        exit 1
    fi
    cd ..

    # Restart service
    log_info "Restarting service..."
    if sudo systemctl restart "${SERVICE_NAME}"; then
        log_info "Service restarted"
    else
        log_error "Failed to restart service during rollback"
        exit 1
    fi

    # Wait for service to be ready
    log_info "Waiting for service to be ready..."
    sleep 5

    # Verify health endpoint
    log_info "Verifying health endpoint..."
    if curl -sf "${HEALTH_URL}" > /dev/null 2>&1; then
        log_info "Health check passed after rollback"
        log_info "Successfully rolled back to commit ${PREVIOUS_COMMIT}"
    else
        log_error "Health check failed after rollback - manual intervention required"
        exit 1
    fi

    log_info "=========================================="
    log_info "Rollback Complete"
    log_info "=========================================="

    exit 1
}

################################################################################
# Validation Functions
################################################################################

# Validate environment variables
validate_environment() {
    log_info "Validating environment variables..."

    if [[ ! -f "${ENV_FILE}" ]]; then
        log_error "Environment file not found: ${ENV_FILE}"
        exit 1
    fi

    # Source the env file
    set -a
    source "${ENV_FILE}"
    set +a

    # Required environment variables
    local required_vars=(
        "DATABASE_PATH"
        "YOUTUBE_API_KEY"
        "ALLOWED_HOSTS"
        "DEBUG"
        "LOG_LEVEL"
        "LOG_FILE"
    )

    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("${var}")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        exit 1
    fi

    log_info "Environment validation passed - all required variables present"
}

################################################################################
# Git Operations
################################################################################

# Pull latest code from repository
pull_latest_code() {
    log_info "Pulling latest code from repository..."

    # Store current commit SHA for rollback
    PREVIOUS_COMMIT=$(git rev-parse HEAD)
    log_info "Current commit: ${PREVIOUS_COMMIT}"

    # Pull latest code from main branch
    if git pull origin main; then
        NEW_COMMIT=$(git rev-parse HEAD)
        log_info "Successfully pulled latest code"
        log_info "New commit: ${NEW_COMMIT}"

        if [[ "${PREVIOUS_COMMIT}" == "${NEW_COMMIT}" ]]; then
            log_info "No new commits - repository already up to date"
        else
            log_info "Deploying changes from ${PREVIOUS_COMMIT} to ${NEW_COMMIT}"
        fi
    else
        log_error "Failed to pull latest code from repository"
        exit 1
    fi
}

################################################################################
# Database Operations
################################################################################

# Run database migrations if they exist
run_database_migrations() {
    log_info "Checking for database migrations..."

    local migration_script="${APP_DIR}/backend/db/migrate.py"

    if [[ -f "${migration_script}" ]]; then
        log_info "Migration script found: ${migration_script}"
        log_info "Running database migrations..."

        if uv run python backend/db/migrate.py; then
            log_info "Database migrations completed successfully"
        else
            log_error "Database migrations failed"
            exit 1
        fi
    else
        log_info "No migration script found - migrations not needed"
    fi
}

################################################################################
# Backend Quality Checks and Testing
################################################################################

# Install/update backend dependencies
install_backend_dependencies() {
    log_info "Installing/updating backend dependencies..."

    if uv sync --extra dev; then
        log_info "Backend dependencies installed/updated successfully"
    else
        log_error "Failed to install backend dependencies"
        exit 1
    fi
}

# Run backend code quality checks
run_backend_quality_checks() {
    log_info "Running backend code quality checks..."

    # Black formatter check (don't auto-fix in deployment)
    log_info "Running black formatter check..."
    if uv run black . --check; then
        log_info "Black formatter check passed"
    else
        log_error "Black formatter check failed - code needs formatting"
        exit 1
    fi

    # Ruff linter
    log_info "Running ruff linter..."
    if uv run ruff check .; then
        log_info "Ruff linter check passed"
    else
        log_error "Ruff linter check failed"
        exit 1
    fi

    # Mypy type checker
    log_info "Running mypy type checker..."
    if uv run mypy backend/; then
        log_info "Mypy type checker passed"
    else
        log_error "Mypy type checker failed"
        exit 1
    fi

    log_info "All backend quality checks passed"
}

# Run TIER 1 safety tests (DEPLOYMENT BLOCKER)
run_tier1_safety_tests() {
    log_info "=========================================="
    log_info "Running TIER 1 Safety Tests (CRITICAL)"
    log_info "=========================================="

    # Run TIER 1 tests
    if uv run pytest -m tier1 -v; then
        log_info "TIER 1 safety tests PASSED - deployment can proceed"
    else
        log_error "TIER 1 SAFETY TESTS FAILED - BLOCKING DEPLOYMENT"
        log_error "This is a critical failure - any TIER 1 test failure blocks deployment"
        exit 1
    fi
}

# Verify no async/await in backend code (architectural constraint)
verify_no_async_await() {
    log_info "Verifying architectural constraint: no async/await in backend..."

    # Search for async/await patterns in backend code (exclude tests and common non-production directories)
    local async_matches
    async_matches=$(grep -r "async def\|await " backend/ \
        --exclude-dir=__pycache__ \
        --exclude-dir=.pytest_cache \
        --exclude-dir=.venv \
        --exclude-dir=.mypy_cache \
        --exclude="*.pyc" \
        2>/dev/null || true)

    if [[ -n "${async_matches}" ]]; then
        log_error "ARCHITECTURAL VIOLATION: async/await detected in backend code"
        log_error "Backend must be 100% synchronous (no async/await allowed)"
        log_error "Files with violations:"
        echo "${async_matches}" | while read -r line; do
            log_error "  ${line}"
        done
        exit 1
    else
        log_info "Architectural constraint verified: no async/await found in backend"
    fi
}

################################################################################
# Frontend Build and Quality Checks
################################################################################

# Build frontend for production
build_frontend() {
    log_info "Building frontend for production..."

    # Change to frontend directory
    cd frontend

    # Install/update npm dependencies
    log_info "Installing/updating npm dependencies..."
    if npm install; then
        log_info "npm dependencies installed/updated successfully"
    else
        log_error "Failed to install npm dependencies"
        exit 1
    fi

    # Build production assets
    log_info "Building production assets..."
    if npm run build; then
        log_info "Frontend build completed successfully"

        # Verify build output exists
        if [[ -d "../static" ]]; then
            local asset_count
            asset_count=$(find ../static -type f | wc -l)
            log_info "Build output: ${asset_count} files in static/ directory"
        else
            log_error "Build output directory not found: ../static"
            exit 1
        fi
    else
        log_error "Frontend build failed"
        exit 1
    fi

    # Return to app root
    cd ..
}

# Run frontend code quality checks
run_frontend_quality_checks() {
    log_info "Running frontend code quality checks..."

    # Change to frontend directory
    cd frontend

    # Run ESLint
    log_info "Running ESLint..."
    if npm run lint; then
        log_info "ESLint check passed"
    else
        log_error "ESLint check failed"
        exit 1
    fi

    # Run Prettier format check (check only, don't auto-format)
    log_info "Running Prettier format check..."
    if npm run format -- --check; then
        log_info "Prettier format check passed"
    else
        log_error "Prettier format check failed - code needs formatting"
        exit 1
    fi

    log_info "All frontend quality checks passed"

    # Return to app root
    cd ..
}

# Run frontend tests
run_frontend_tests() {
    log_info "Running frontend tests..."

    # Change to frontend directory
    cd frontend

    # Run Vitest tests
    if npm test; then
        log_info "Frontend tests passed"
    else
        log_error "Frontend tests failed"
        exit 1
    fi

    # Return to app root
    cd ..
}

################################################################################
# Service Deployment
################################################################################

# Perform SQLite WAL checkpoint
perform_database_checkpoint() {
    log_info "Performing SQLite WAL checkpoint..."

    # Run WAL checkpoint (FULL mode - blocks until all frames checkpointed)
    if sqlite3 "${DB_PATH}" "PRAGMA wal_checkpoint(FULL);"; then
        log_info "Database WAL checkpoint completed successfully"
    else
        log_warn "Database WAL checkpoint failed - continuing deployment"
        log_warn "This is not a deployment blocker, but may indicate database issues"
    fi
}

# Restart systemd service
restart_service() {
    log_info "Restarting systemd service: ${SERVICE_NAME}..."

    # Restart the service
    if sudo systemctl restart "${SERVICE_NAME}"; then
        log_info "Service restart command issued successfully"
    else
        log_error "Failed to restart service"
        exit 1
    fi

    # Wait for service to be ready
    log_info "Waiting for service to be ready (5 seconds)..."
    sleep 5

    # Check service status
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log_info "Service is active and running"
    else
        log_error "Service is not active after restart"
        log_error "Service status:"
        sudo systemctl status "${SERVICE_NAME}" || true
        exit 1
    fi
}

# Verify health endpoint
verify_health_endpoint() {
    log_info "Verifying health endpoint..."

    # Attempt health check with curl
    local health_response
    if health_response=$(curl -sf "${HEALTH_URL}" 2>&1); then
        log_info "Health endpoint returned HTTP 200"

        # Parse JSON response using Python (more reliable than grep)
        local status
        local database_status

        # Try Python JSON parsing first
        if command -v python3 > /dev/null 2>&1; then
            status=$(echo "${health_response}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null || echo "")
            database_status=$(echo "${health_response}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('database', ''))" 2>/dev/null || echo "")
        else
            # Fallback to grep-based parsing if Python not available
            status=$(echo "${health_response}" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || true)
            database_status=$(echo "${health_response}" | grep -o '"database":"[^"]*"' | cut -d'"' -f4 || true)
        fi

        log_info "Health check response: status=${status}, database=${database_status}"

        # Verify status is "ok"
        if [[ "${status}" != "ok" ]]; then
            log_error "Health check failed: status is '${status}' (expected 'ok')"
            exit 1
        fi

        # Verify database is "connected"
        if [[ "${database_status}" != "connected" ]]; then
            log_error "Health check failed: database is '${database_status}' (expected 'connected')"
            exit 1
        fi

        log_info "Health check passed: application is healthy and database is connected"
    else
        log_error "Health check failed: unable to reach ${HEALTH_URL}"
        log_error "Response: ${health_response}"
        exit 1
    fi
}

################################################################################
# Main Deployment Functions
################################################################################

# Main deployment function
main() {
    log_info "=========================================="
    log_info "Starting Deployment"
    log_info "=========================================="
    log_info "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    log_info "User: $(whoami)"
    log_info "Working Directory: ${APP_DIR}"

    # Change to application directory
    cd "${APP_DIR}"

    # Step 1: Validate environment
    validate_environment

    # Step 2: Pull latest code
    pull_latest_code

    # Step 3: Run database migrations
    run_database_migrations

    # Step 4: Install backend dependencies
    install_backend_dependencies

    # Step 5: Run backend quality checks
    run_backend_quality_checks

    # Step 6: Run TIER 1 safety tests (CRITICAL - deployment blocker)
    run_tier1_safety_tests

    # Step 7: Verify architectural constraint (no async/await)
    verify_no_async_await

    # Step 8: Build frontend for production
    build_frontend

    # Step 9: Run frontend quality checks
    run_frontend_quality_checks

    # Step 10: Run frontend tests
    run_frontend_tests

    # Step 11: Perform database checkpoint
    perform_database_checkpoint

    # Step 12: Restart service
    restart_service

    # Step 13: Verify health endpoint
    verify_health_endpoint

    log_info "=========================================="
    log_info "Deployment Complete"
    log_info "=========================================="
}

# Run main function
main "$@"
