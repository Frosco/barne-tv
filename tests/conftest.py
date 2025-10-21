"""
Root test configuration.

Sets TESTING environment variable before any FastAPI imports to ensure
rate limiting is properly disabled for all test suites.

This fixes the issue where running all tests together from root (`pytest`)
would fail due to rate limiting, while running test suites separately
(`pytest tests/backend/`, `pytest tests/integration/`) would pass.

Story 1.5 - Channel Management (E2E Test Implementation)
"""

import os

# CRITICAL: Must be set BEFORE any backend imports
# This ensures rate limiting middleware is disabled for ALL test suites
os.environ["TESTING"] = "true"
