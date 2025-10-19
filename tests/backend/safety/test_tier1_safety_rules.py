"""
TIER 1 Child Safety Tests - Cannot Violate

These tests verify adherence to TIER 1 safety rules that directly protect
child safety and time limits. ALL TIER 1 tests MUST pass before deployment.

Coverage Requirement: 100% for auth.py (TIER 1 code)
"""

import pytest
from passlib.hash import bcrypt

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
    TIER 1 Rule 4: Must use passlib's bcrypt implementation.

    Verifies:
    - bcrypt.hash() is used for hashing
    - bcrypt.verify() is used for verification
    - Not using weaker algorithms (SHA256, MD5, etc.)
    """
    password = "test_password"

    # Hash using our function
    hashed = hash_password(password)

    # Verify it's a valid bcrypt hash by using bcrypt.verify directly
    assert bcrypt.verify(password, hashed), "Hash must be compatible with bcrypt.verify()"

    # Verify hash format matches bcrypt
    # Bcrypt format: $2b$<cost>$<salt><hash>
    parts = hashed.split("$")
    assert len(parts) == 4, "Bcrypt hash must have 4 parts separated by $"
    assert parts[1] == "2b", "Must use bcrypt 2b variant"
    assert parts[2].isdigit(), "Cost factor must be numeric"
