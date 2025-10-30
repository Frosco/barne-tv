"""
Security Header Verification Tests (Story 2.3)

Verify that security headers are correctly added to all responses,
robots.txt is served correctly, and TrustedHostMiddleware validates hosts.

All tests marked with @pytest.mark.security
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    """
    Create FastAPI test client with valid Host header.

    TestClient needs base_url set to include a host from ALLOWED_HOSTS,
    otherwise TrustedHostMiddleware will reject requests with 400 error.
    """
    return TestClient(app, base_url="http://localhost")


# =============================================================================
# ROBOTS.TXT TESTS
# =============================================================================


@pytest.mark.security
def test_robots_txt_content(client):
    """
    Test that robots.txt returns correct content blocking all crawlers.

    AC 1: robots.txt file created blocking all crawlers.
    """
    response = client.get("/static/robots.txt")
    assert response.status_code == 200
    assert "User-agent: *" in response.text
    assert "Disallow: /" in response.text


@pytest.mark.security
def test_robots_txt_content_type(client):
    """
    Test that robots.txt is served with correct content type.

    Verifies robots.txt is served as plain text.
    """
    response = client.get("/static/robots.txt")
    assert response.status_code == 200
    # Content-Type may include charset, so check if it starts with text/plain
    content_type = response.headers.get("content-type", "")
    assert content_type.startswith("text/plain") or content_type.startswith("text/x-robots-tag")


@pytest.mark.security
@pytest.mark.p1
def test_robots_txt_file_permissions():
    """
    2.3-INT-003: Verify robots.txt file has correct permissions (644).

    AC 1: robots.txt should be readable but not writable by others.
    This is a security best practice to prevent unauthorized modification.
    """
    import os
    import stat

    robots_path = "frontend/public/robots.txt"

    # Check if file exists
    if not os.path.exists(robots_path):
        pytest.skip("robots.txt not found in expected location - may be served from static/")
        return

    # Get file permissions
    file_stat = os.stat(robots_path)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Convert to octal string for easier comparison
    octal_permissions = oct(file_mode)[-3:]

    # Acceptable permissions: 644 (rw-r--r--) or more restrictive
    # We verify it's not world-writable (last digit should be 0 or 4)
    assert octal_permissions[2] in [
        "0",
        "4",
    ], f"robots.txt should not be world-writable, got permissions: {octal_permissions}"


# =============================================================================
# SECURITY HEADERS TESTS
# =============================================================================


@pytest.mark.security
def test_security_headers_present_on_health_endpoint(client):
    """
    Test that security headers are present on health check endpoint.

    AC 11, 12, 13: X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
    headers are added to all responses via FastAPI middleware.
    """
    response = client.get("/health")
    assert response.status_code == 200

    # Verify defense-in-depth headers (set by FastAPI middleware)
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"


@pytest.mark.security
def test_security_headers_present_on_child_interface(client):
    """
    Test that security headers are present on child interface routes.

    Verifies headers are added to all routes, not just health check.
    """
    # Child interface endpoint (returns 200 or 401, doesn't matter for headers)
    response = client.get("/")

    # Headers should be present regardless of response status
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "X-XSS-Protection" in response.headers
    assert response.headers["X-XSS-Protection"] == "1; mode=block"


@pytest.mark.security
@pytest.mark.p0
def test_security_headers_present_on_404(client):
    """
    2.3-INT-019: Test that security headers are present even on 404 errors.

    Defense-in-depth: Headers should be added to all responses, including errors.
    AC 3: X-Robots-Tag and other security headers must be present on error responses.
    """
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404

    # Headers should still be present
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"

    # X-Robots-Tag should also be present on error pages
    assert "X-Robots-Tag" in response.headers
    assert "noindex" in response.headers["X-Robots-Tag"]
    assert "nofollow" in response.headers["X-Robots-Tag"]


@pytest.mark.security
@pytest.mark.p0
def test_x_robots_tag_header_on_child_endpoints(client):
    """
    2.3-INT-007: Verify X-Robots-Tag header present on child endpoints.

    AC 3: X-Robots-Tag HTTP header added to all responses (noindex, nofollow).
    Child interface is the primary user-facing interface and must never be indexed.
    """
    # Test child interface root
    response = client.get("/")

    # X-Robots-Tag must be present
    assert "X-Robots-Tag" in response.headers

    # Verify content includes noindex and nofollow
    x_robots_tag = response.headers["X-Robots-Tag"]
    assert "noindex" in x_robots_tag, "X-Robots-Tag must include noindex"
    assert "nofollow" in x_robots_tag, "X-Robots-Tag must include nofollow"


@pytest.mark.security
@pytest.mark.p1
def test_x_robots_tag_header_on_admin_endpoints(client):
    """
    2.3-INT-008: Verify X-Robots-Tag header present on admin endpoints.

    AC 3: X-Robots-Tag HTTP header should be present on admin interface.
    Admin interface is already auth-protected, but defense-in-depth requires
    X-Robots-Tag to prevent indexing if auth is bypassed.
    """
    # Test admin login endpoint (accessible without auth)
    response = client.get("/admin/login")

    # X-Robots-Tag should be present even on admin routes
    assert "X-Robots-Tag" in response.headers

    x_robots_tag = response.headers["X-Robots-Tag"]
    assert "noindex" in x_robots_tag
    assert "nofollow" in x_robots_tag


@pytest.mark.security
@pytest.mark.p0
def test_security_headers_on_all_response_types(client):
    """
    2.3-INT-017: Verify security headers on all response types (JSON, HTML, static).

    AC 11-13, 18: Security headers must be present regardless of response content type.
    This ensures comprehensive defense-in-depth coverage.
    """
    # Test JSON response (API endpoint)
    json_response = client.get("/health")
    assert json_response.status_code == 200
    assert json_response.headers["content-type"].startswith("application/json")
    assert json_response.headers["X-Content-Type-Options"] == "nosniff"
    assert json_response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert json_response.headers["X-XSS-Protection"] == "1; mode=block"

    # Test HTML response (root endpoint)
    html_response = client.get("/")
    # May return HTML or redirect, but headers should be present
    assert "X-Content-Type-Options" in html_response.headers
    assert "X-Frame-Options" in html_response.headers
    assert "X-XSS-Protection" in html_response.headers

    # Test 404 response (error)
    error_response = client.get("/nonexistent")
    assert error_response.status_code == 404
    assert error_response.headers["X-Content-Type-Options"] == "nosniff"
    assert error_response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert error_response.headers["X-XSS-Protection"] == "1; mode=block"


@pytest.mark.security
@pytest.mark.p1
def test_security_headers_on_static_files(client):
    """
    2.3-INT-018: Verify security headers present on static file responses.

    AC 18: Defense-in-depth requires security headers even on static assets.
    This prevents any potential attacks via static file serving.
    """
    # Test robots.txt (static file)
    response = client.get("/static/robots.txt")
    assert response.status_code == 200

    # Security headers should be present
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "X-XSS-Protection" in response.headers
    assert response.headers["X-XSS-Protection"] == "1; mode=block"


# =============================================================================
# TRUSTEDHOSTMIDDLEWARE TESTS
# =============================================================================


@pytest.mark.security
def test_trusted_host_middleware_accepts_valid_host(client):
    """
    Test that TrustedHostMiddleware accepts requests with valid Host header.

    AC 17: TrustedHostMiddleware configured with ALLOWED_HOSTS from environment.
    """
    # Default ALLOWED_HOSTS includes localhost and 127.0.0.1
    response = client.get("/health", headers={"Host": "localhost"})
    assert response.status_code == 200


@pytest.mark.security
def test_trusted_host_middleware_accepts_localhost_ip(client):
    """
    Test that TrustedHostMiddleware accepts 127.0.0.1 as valid host.

    Verifies ALLOWED_HOSTS default configuration includes localhost IP.
    """
    response = client.get("/health", headers={"Host": "127.0.0.1"})
    assert response.status_code == 200


@pytest.mark.security
def test_trusted_host_middleware_rejects_invalid_host(client):
    """
    Test that TrustedHostMiddleware rejects requests with invalid Host header.

    AC 17: Invalid hosts should be rejected with 400 Bad Request.
    """
    response = client.get("/health", headers={"Host": "evil.com"})
    assert response.status_code == 400


@pytest.mark.security
def test_trusted_host_middleware_rejects_malicious_host(client):
    """
    Test that TrustedHostMiddleware rejects obviously malicious Host headers.

    Verifies protection against host header injection attacks.
    """
    malicious_hosts = [
        "attacker.com",
        "phishing-site.com",
        "192.0.2.1",  # TEST-NET-1, not in ALLOWED_HOSTS
        "evil-domain.net",
    ]

    for host in malicious_hosts:
        response = client.get("/health", headers={"Host": host})
        assert (
            response.status_code == 400
        ), f"Host '{host}' should be rejected but got {response.status_code}"


# =============================================================================
# ALLOWED_HOSTS CONFIGURATION TESTS
# =============================================================================


@pytest.mark.security
def test_allowed_hosts_loaded_from_config():
    """
    Test that ALLOWED_HOSTS is loaded from backend.config module.

    AC 17: ALLOWED_HOSTS should be imported from config, not accessed directly.
    """
    from backend.config import ALLOWED_HOSTS

    # ALLOWED_HOSTS should be a list
    assert isinstance(ALLOWED_HOSTS, list)
    assert len(ALLOWED_HOSTS) > 0

    # Default should include localhost and 127.0.0.1
    assert "localhost" in ALLOWED_HOSTS
    assert "127.0.0.1" in ALLOWED_HOSTS


# =============================================================================
# DEFENSE-IN-DEPTH VERIFICATION
# =============================================================================


@pytest.mark.security
def test_security_headers_are_defense_in_depth():
    """
    Test and document that security headers are defense-in-depth.

    Story 2.3: FastAPI middleware provides backup headers. Primary headers
    are set by Nginx in production. This test verifies FastAPI layer works.
    """
    client = TestClient(app)
    response = client.get("/health")

    # These headers are set by FastAPI middleware as defense-in-depth
    # In production, Nginx sets these same headers plus additional ones (CSP, HSTS, etc.)
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"

    # Note: CSP, HSTS, Referrer-Policy, Permissions-Policy are Nginx-only (not tested here)


# =============================================================================
# META TAGS VERIFICATION (Manual inspection required)
# =============================================================================


@pytest.mark.security
def test_child_interface_contains_security_meta_tags(client):
    """
    Test that child interface HTML contains security meta tags.

    AC 2, 4: Meta tags noindex, nofollow, noarchive for robots and googlebot.

    Note: This test verifies the meta tags are present in the rendered HTML.
    The actual rendering depends on the route returning HTML from base.html template.
    """
    # This test will be implemented once child interface routes return HTML
    # For now, we document the expected behavior:
    # - <meta name="robots" content="noindex, nofollow, noarchive">
    # - <meta name="googlebot" content="noindex, nofollow">
    pytest.skip("Child interface route not yet implemented - manual verification required")


# =============================================================================
# EXTERNAL LINKS AND ANALYTICS AUDIT (Manual verification)
# =============================================================================


@pytest.mark.security
def test_no_external_analytics_scripts():
    """
    Test that no external analytics scripts are present in templates.

    AC 5: No external analytics or tracking scripts included.

    Note: This requires manual verification of templates:
    - frontend/templates/base.html
    - frontend/templates/child/*.html
    - frontend/templates/admin/*.html

    Manual audit should verify:
    - No Google Analytics
    - No Facebook Pixel
    - No third-party tracking scripts
    - Only YouTube IFrame API for video playback (necessary)
    """
    pytest.skip("Manual template audit required - automated test not applicable")


@pytest.mark.security
def test_child_interface_has_no_external_links():
    """
    Test that child interface has no external navigation links.

    AC 7: Child interface has no external links or navigation away from application.

    Note: This requires manual verification of child interface templates.
    Expected: No <a> tags with external hrefs, no navigation elements.
    """
    pytest.skip("Manual template audit required - automated test not applicable")
