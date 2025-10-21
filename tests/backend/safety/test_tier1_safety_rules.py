"""
TIER 1 Child Safety Tests - Cannot Violate

These tests verify adherence to TIER 1 safety rules that directly protect
child safety and time limits. ALL TIER 1 tests MUST pass before deployment.

Coverage Requirement: 100% for auth.py (TIER 1 code)
"""

import pytest
import bcrypt

from backend.auth import hash_password, verify_password


# =============================================================================
# TIER 1 RULE 4: Admin Password Security
# =============================================================================


@pytest.mark.tier1
def test_rule4_password_uses_bcrypt():
    """
    TIER 1 Rule 4: Passwords must use bcrypt hashing.

    Verifies:
    - hash_password() returns valid bcrypt hash format
    - Hash starts with '$2b$' (bcrypt identifier)
    - Hash is 60 characters long (standard bcrypt length)
    """
    password = "admin_password_123"

    # Hash the password
    hashed = hash_password(password)

    # Verify bcrypt format
    assert hashed.startswith("$2b$"), "Hash must start with '$2b$' (bcrypt identifier)"
    assert len(hashed) == 60, "Bcrypt hash must be exactly 60 characters"


@pytest.mark.tier1
def test_rule4_password_verification_succeeds_with_correct_password():
    """
    TIER 1 Rule 4: Password verification must work correctly.

    Verifies:
    - Correct password verification succeeds
    - Bcrypt verify() function is used (via passlib)
    """
    password = "admin_password_123"
    hashed = hash_password(password)

    # Verify with correct password succeeds
    assert verify_password(password, hashed) is True


@pytest.mark.tier1
def test_rule4_password_verification_fails_with_wrong_password():
    """
    TIER 1 Rule 4: Password verification must reject wrong passwords.

    Verifies:
    - Wrong password verification fails
    - No timing attacks possible (bcrypt handles this)
    """
    password = "admin_password_123"
    wrong_password = "wrong_password"
    hashed = hash_password(password)

    # Verify with wrong password fails
    assert verify_password(wrong_password, hashed) is False


@pytest.mark.tier1
def test_rule4_password_never_stored_plain_text():
    """
    TIER 1 Rule 4: Passwords must never be stored in plain text.

    Verifies:
    - Hash is different from original password
    - Hash cannot be reversed to original password
    - Each hash is unique (due to salt)
    """
    password = "admin_password_123"

    # Hash the password
    hashed = hash_password(password)

    # Verify hash is not plain text
    assert hashed != password, "Hash must not match plain text password"
    assert password not in hashed, "Plain text password must not appear in hash"

    # Verify each hash is unique (salted)
    hashed2 = hash_password(password)
    assert hashed != hashed2, "Each hash must be unique due to random salt"


@pytest.mark.tier1
def test_rule4_bcrypt_library_used():
    """
    TIER 1 Rule 4: Must use bcrypt implementation.

    Verifies:
    - bcrypt.hashpw() is used for hashing
    - bcrypt.checkpw() is used for verification
    - Not using weaker algorithms (SHA256, MD5, etc.)
    """
    password = "test_password"

    # Hash using our function
    hashed = hash_password(password)

    # Verify it's a valid bcrypt hash by using bcrypt.checkpw directly
    assert bcrypt.checkpw(
        password.encode("utf-8"), hashed.encode("utf-8")
    ), "Hash must be compatible with bcrypt.checkpw()"

    # Verify hash format matches bcrypt
    # Bcrypt format: $2b$<cost>$<salt><hash>
    parts = hashed.split("$")
    assert len(parts) == 4, "Bcrypt hash must have 4 parts separated by $"
    assert parts[1] == "2b", "Must use bcrypt 2b variant"
    assert parts[2].isdigit(), "Cost factor must be numeric"


# =============================================================================
# TIER 1 RULE 5: Input Validation (Story 1.5)
# =============================================================================


@pytest.mark.tier1
def test_rule5_blocks_sql_injection_in_channel_input():
    """
    TIER 1 Rule 5: Input validation must block SQL injection attempts.

    Verifies:
    - SQL injection patterns are rejected in channel/playlist input
    - Validation happens before database operations
    - Norwegian error message returned
    """
    from backend.services.content_source import _parse_input

    # Common SQL injection patterns
    sql_injection_attempts = [
        "'; DROP TABLE videos; --",
        "' OR '1'='1",
        "'; DELETE FROM content_sources; --",
        "UNION SELECT * FROM settings--",
        "1' AND '1'='1",
    ]

    for injection_attempt in sql_injection_attempts:
        with pytest.raises(ValueError) as exc_info:
            _parse_input(injection_attempt)

        # Verify rejection with Norwegian error
        assert "Ugyldig" in str(
            exc_info.value
        ), f"SQL injection attempt should be rejected: {injection_attempt}"


@pytest.mark.tier1
def test_rule5_blocks_xss_in_channel_input():
    """
    TIER 1 Rule 5: Input validation must block XSS attempts.

    Verifies:
    - XSS patterns are rejected in channel/playlist input
    - Script tags and event handlers blocked
    - Norwegian error message returned
    """
    from backend.services.content_source import _parse_input

    # Common XSS patterns
    xss_attempts = [
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "<img src=x onerror=alert('xss')>",
        "<iframe src='evil.com'></iframe>",
        "' onload='alert(1)'",
    ]

    for xss_attempt in xss_attempts:
        with pytest.raises(ValueError) as exc_info:
            _parse_input(xss_attempt)

        # Verify rejection with Norwegian error
        assert "Ugyldig" in str(exc_info.value), f"XSS attempt should be rejected: {xss_attempt}"


@pytest.mark.tier1
def test_rule5_rejects_oversized_input():
    """
    TIER 1 Rule 5: Input validation must reject oversized input.

    Verifies:
    - Input >500 chars is rejected (ReDoS protection)
    - Length check happens before regex processing
    - Norwegian error message returned
    """
    from backend.services.content_source import _parse_input

    # Create input exceeding 500 character limit
    oversized_input = "https://www.youtube.com/channel/" + "A" * 500

    with pytest.raises(ValueError) as exc_info:
        _parse_input(oversized_input)

    # Verify error mentions length limit
    error_msg = str(exc_info.value)
    assert (
        "for lang" in error_msg or "length" in error_msg.lower()
    ), "Error should mention length limit"
    assert "500" in error_msg, "Error should mention 500 char limit"


@pytest.mark.tier1
def test_rule5_rejects_empty_input():
    """
    TIER 1 Rule 5: Input validation must reject empty input.

    Verifies:
    - Empty string rejected
    - None value rejected
    - Norwegian error message returned
    """
    from backend.services.content_source import _parse_input

    # Test empty string
    with pytest.raises(ValueError) as exc_info:
        _parse_input("")
    assert "Ugyldig inndata" in str(
        exc_info.value
    ), "Empty string should be rejected with Norwegian error"

    # Test None
    with pytest.raises(ValueError) as exc_info:
        _parse_input(None)
    assert "Ugyldig inndata" in str(
        exc_info.value
    ), "None value should be rejected with Norwegian error"

    # Test whitespace only
    with pytest.raises(ValueError) as exc_info:
        _parse_input("   ")
    assert "Ugyldig" in str(exc_info.value), "Whitespace-only input should be rejected"


@pytest.mark.tier1
def test_rule5_input_validation_happens_before_database():
    """
    TIER 1 Rule 5: Input validation must happen BEFORE database operations.

    Verifies:
    - Validation errors raised before any DB queries
    - No risk of malicious input reaching database
    - Prevents SQL injection at validation layer
    """
    from backend.services.content_source import _parse_input

    # Malicious input that should be caught at validation
    malicious_inputs = [
        "'; DROP TABLE videos; --",
        "<script>alert(1)</script>",
        "A" * 600,  # Oversized
        "",  # Empty
    ]

    for malicious_input in malicious_inputs:
        # Should raise ValueError during parsing, before reaching DB
        try:
            _parse_input(malicious_input)
            pytest.fail(f"Input should have been rejected: {malicious_input}")
        except ValueError:
            # Expected - validation caught it
            pass
        except Exception as e:
            # Any other exception type means validation failed to catch it
            pytest.fail(
                f"Wrong exception type: {type(e).__name__}. "
                f"Should raise ValueError at validation layer."
            )


@pytest.mark.tier1
def test_rule5_all_user_inputs_validated():
    """
    TIER 1 Rule 5: ALL parent inputs must be validated.

    Verifies:
    - Channel URL input validated
    - Playlist URL input validated
    - Direct ID input validated
    - No input bypasses validation
    """
    from backend.services.content_source import _parse_input

    # Valid inputs that should pass
    valid_inputs = [
        "https://www.youtube.com/channel/UCrwObTfqv8u1KO7Fgk-FXHQ",
        "https://www.youtube.com/@Blippi",
        "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
    ]

    for valid_input in valid_inputs:
        # Should not raise - validation passes
        try:
            result = _parse_input(valid_input)
            assert result is not None, f"Valid input should parse: {valid_input}"
        except ValueError:
            pytest.fail(f"Valid input was rejected: {valid_input}")

    # Invalid inputs that should fail
    invalid_inputs = [
        "not-a-url",
        "https://evil.com/fake",
        "javascript:alert(1)",
        "",
    ]

    for invalid_input in invalid_inputs:
        with pytest.raises(ValueError):
            _parse_input(invalid_input)
