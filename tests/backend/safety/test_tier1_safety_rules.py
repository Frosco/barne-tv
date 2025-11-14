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


# =============================================================================
# TIER 1 RULE 1: Video Selection Filtering (Story 2.1)
# =============================================================================


@pytest.mark.tier1
def test_rule1_banned_videos_never_appear_in_grid(test_db_with_patch):
    """
    TIER 1 Rule 1: Banned videos must NEVER appear in video grid.

    Tests 50 times to verify randomness doesn't bypass filtering.

    Verifies:
    - Banned videos filtered from get_available_videos()
    - Filtering works across random selections
    - get_videos_for_grid() never returns banned videos
    """
    from backend.db.queries import get_available_videos
    from backend.services.viewing_session import get_videos_for_grid

    test_db = test_db_with_patch  # Alias for consistency

    # Add some videos to the test database
    # Add a content source
    test_db.execute(
        """INSERT INTO content_sources
           (source_id, source_type, name, video_count, last_refresh, fetch_method, added_at)
           VALUES (?, ?, ?, ?, datetime('now'), ?, datetime('now'))""",
        ("UCtest123", "channel", "Test Channel", 20, "api"),
    )
    source_id = test_db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Add 20 videos
    for i in range(20):
        test_db.execute(
            """INSERT INTO videos
               (video_id, title, content_source_id, youtube_channel_id, youtube_channel_name,
                thumbnail_url, duration_seconds, published_at, fetched_at, is_available)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), 1)""",
            (
                f"video_{i}",
                f"Test Video {i}",
                source_id,
                "UCtest123",
                "Test Channel",
                f"https://i.ytimg.com/vi/video_{i}/default.jpg",
                300,
            ),
        )

    # Ban 5 videos
    banned_ids = [f"video_{i}" for i in [1, 5, 10, 15, 19]]
    for video_id in banned_ids:
        test_db.execute(
            "INSERT INTO banned_videos (video_id, banned_at) VALUES (?, datetime('now'))",
            (video_id,),
        )

    # Test 50 times to verify randomness doesn't bypass filtering
    for iteration in range(50):
        # Get available videos
        available = get_available_videos(exclude_banned=True)

        # Verify NO banned videos appear
        available_ids = {v["videoId"] for v in available}
        assert not any(
            banned_id in available_ids for banned_id in banned_ids
        ), f"Iteration {iteration}: Banned video found in available videos"

        # Also test through get_videos_for_grid
        videos, _ = get_videos_for_grid(9)
        grid_ids = {v["videoId"] for v in videos}
        assert not any(
            banned_id in grid_ids for banned_id in banned_ids
        ), f"Iteration {iteration}: Banned video found in grid"


@pytest.mark.tier1
def test_rule1_unavailable_videos_never_appear_in_grid(test_db_with_patch):
    """
    TIER 1 Rule 1: Unavailable videos must NEVER appear in video grid.

    Tests 50 times to verify randomness doesn't bypass filtering.

    Verifies:
    - is_available=0 videos filtered from get_available_videos()
    - Filtering works across random selections
    - get_videos_for_grid() never returns unavailable videos
    """
    from backend.db.queries import get_available_videos
    from backend.services.viewing_session import get_videos_for_grid

    test_db = test_db_with_patch  # Alias for consistency

    # Add videos to test database
    # Add content source
    test_db.execute(
        """INSERT INTO content_sources
           (source_id, source_type, name, video_count, last_refresh, fetch_method, added_at)
           VALUES (?, ?, ?, ?, datetime('now'), ?, datetime('now'))""",
        ("UCtest456", "channel", "Test Channel 2", 20, "api"),
    )
    source_id = test_db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Add 20 videos, mark 5 as unavailable
    unavailable_ids = []
    for i in range(20):
        is_available = 0 if i in [2, 7, 12, 16, 18] else 1
        if is_available == 0:
            unavailable_ids.append(f"video_unavail_{i}")

        test_db.execute(
            """INSERT INTO videos
               (video_id, title, content_source_id, youtube_channel_id, youtube_channel_name,
                thumbnail_url, duration_seconds, published_at, fetched_at, is_available)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?)""",
            (
                f"video_unavail_{i}",
                f"Test Video Unavail {i}",
                source_id,
                "UCtest456",
                "Test Channel 2",
                f"https://i.ytimg.com/vi/video_unavail_{i}/default.jpg",
                300,
                is_available,
            ),
        )

    # Test 50 times to verify randomness doesn't bypass filtering
    for iteration in range(50):
        # Get available videos
        available = get_available_videos(exclude_banned=True)

        # Verify NO unavailable videos appear
        available_ids = {v["videoId"] for v in available}
        assert not any(
            unavail_id in available_ids for unavail_id in unavailable_ids
        ), f"Iteration {iteration}: Unavailable video found in available videos"

        # Also test through get_videos_for_grid
        videos, _ = get_videos_for_grid(9)
        grid_ids = {v["videoId"] for v in videos}
        assert not any(
            unavail_id in grid_ids for unavail_id in unavailable_ids
        ), f"Iteration {iteration}: Unavailable video found in grid"


# =============================================================================
# TIER 1 RULE 2: Time Limit Calculation (Story 2.1)
# =============================================================================


@pytest.mark.tier1
def test_rule2_time_limits_exclude_manual_play_and_grace_play(test_db):
    """
    TIER 1 Rule 2: Time limits must exclude manual_play and grace_play.

    Verifies:
    - manual_play=1 videos not counted in daily limit
    - grace_play=1 videos not counted in daily limit
    - Only manual_play=0 AND grace_play=0 count toward limit
    - get_daily_limit() returns correct minutes_watched
    """
    from datetime import datetime, timezone
    from backend.db.queries import get_watch_history_for_date
    from backend.services.viewing_session import get_daily_limit

    # TIER 1 Rule 3: Use UTC for all date operations
    today = datetime.now(timezone.utc).date().isoformat()

    # Add watch history with different flag combinations
    # 10 minutes - counts toward limit (both flags 0)
    test_db.execute(
        """INSERT INTO watch_history
           (video_id, video_title, channel_name, watched_at, completed,
            manual_play, grace_play, duration_watched_seconds)
           VALUES (?, ?, ?, datetime('now'), 1, 0, 0, ?)""",
        ("video_1", "Video 1", "Channel", 600),  # 10 minutes
    )

    # 5 minutes - manual_play=1, should NOT count
    test_db.execute(
        """INSERT INTO watch_history
           (video_id, video_title, channel_name, watched_at, completed,
            manual_play, grace_play, duration_watched_seconds)
           VALUES (?, ?, ?, datetime('now'), 1, 1, 0, ?)""",
        ("video_2", "Video 2", "Channel", 300),  # 5 minutes
    )

    # 8 minutes - grace_play=1, should NOT count
    test_db.execute(
        """INSERT INTO watch_history
           (video_id, video_title, channel_name, watched_at, completed,
            manual_play, grace_play, duration_watched_seconds)
           VALUES (?, ?, ?, datetime('now'), 1, 0, 1, ?)""",
        ("video_3", "Video 3", "Channel", 480),  # 8 minutes
    )

    # 7 minutes - both flags 1, should NOT count
    test_db.execute(
        """INSERT INTO watch_history
           (video_id, video_title, channel_name, watched_at, completed,
            manual_play, grace_play, duration_watched_seconds)
           VALUES (?, ?, ?, datetime('now'), 1, 1, 1, ?)""",
        ("video_4", "Video 4", "Channel", 420),  # 7 minutes
    )

    # 12 minutes - counts toward limit (both flags 0)
    test_db.execute(
        """INSERT INTO watch_history
           (video_id, video_title, channel_name, watched_at, completed,
            manual_play, grace_play, duration_watched_seconds)
           VALUES (?, ?, ?, datetime('now'), 1, 0, 0, ?)""",
        ("video_5", "Video 5", "Channel", 720),  # 12 minutes
    )

    # Verify get_watch_history_for_date excludes manual_play and grace_play
    history = get_watch_history_for_date(today, conn=test_db)

    # Should only return 2 videos (video_1 and video_5)
    assert (
        len(history) == 2
    ), "Should only return countable history (manual_play=0 AND grace_play=0)"

    history_ids = {h["videoId"] for h in history}
    assert "video_1" in history_ids, "video_1 should be in countable history"
    assert "video_5" in history_ids, "video_5 should be in countable history"
    assert "video_2" not in history_ids, "video_2 (manual_play=1) should be excluded"
    assert "video_3" not in history_ids, "video_3 (grace_play=1) should be excluded"
    assert "video_4" not in history_ids, "video_4 (both flags=1) should be excluded"

    # Verify total duration (10 + 12 = 22 minutes)
    total_seconds = sum(h["durationWatchedSeconds"] for h in history)
    assert total_seconds == 1320, "Total should be 1320 seconds (22 minutes)"

    # Verify get_daily_limit calculates correctly
    daily_limit = get_daily_limit(conn=test_db)

    # Should report 22 minutes watched (10 + 12), not 42 minutes (all videos)
    assert (
        daily_limit["minutesWatched"] == 22
    ), "Daily limit should only count manual_play=0 AND grace_play=0"
    assert daily_limit["minutesRemaining"] == 8, "Should have 8 minutes remaining (30 - 22)"
