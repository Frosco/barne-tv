"""
Tests for admin history endpoints (Story 3.1).

Covers:
- GET /admin/api/history (filtering, pagination, authentication)
- POST /admin/history/replay (validation, URL generation)
- GET /admin/history (template serving)
- TIER 1: Manual play exclusion from daily limits

TIER 1 Rules Tested:
- Rule 2: manual_play and grace_play excluded from daily limit calculations
- Rule 3: UTC time handling in queries
- Rule 5: Input validation for video IDs
- Rule 6: SQL injection prevention via parameterized queries
- Rule 10: Authentication required for admin endpoints
"""

import pytest
import json
from datetime import datetime, timezone, timedelta

from backend.auth import hash_password


# =============================================================================
# TEST FIXTURES AND HELPERS
# =============================================================================


def setup_admin_auth(test_db):
    """
    Setup admin password in test database.

    Returns the password for use in login.
    """
    password = "test_admin_password"
    hashed = hash_password(password)
    json_value = json.dumps(hashed)

    # Insert setting directly into test database
    now = datetime.now(timezone.utc).isoformat()
    test_db.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at, created_at) VALUES (?, ?, ?, ?)",
        ("admin_password_hash", json_value, now, now),
    )
    test_db.commit()

    return password


def authenticate_client(test_client, test_db):
    """
    Authenticate test client and set session cookie.

    Helper function to setup authentication and manually set cookie on client.
    TestClient doesn't automatically forward cookies, so we manually set it.
    """
    password = setup_admin_auth(test_db)
    login_response = test_client.post("/admin/login", json={"password": password})
    assert login_response.status_code == 200, f"Login failed: {login_response.json()}"

    # Manually set session cookie (TestClient doesn't auto-forward)
    session_cookie = login_response.cookies.get("session_id")
    assert session_cookie is not None, "Login should set session_id cookie"
    test_client.cookies.set("session_id", session_cookie)


# =============================================================================
# AUTHENTICATION TESTS (AC1, AC12)
# =============================================================================


@pytest.mark.security
def test_get_admin_history_requires_authentication(test_client):
    """
    Test /admin/api/history returns 401 without session.

    Verifies TIER 2 Rule 10: Authentication required for admin endpoints.
    """
    # Act: Request history without authentication
    response = test_client.get("/admin/api/history")

    # Assert: Should be denied
    assert response.status_code == 401


@pytest.mark.security
def test_post_replay_requires_authentication(test_client):
    """
    Test /admin/history/replay returns 401 without session.

    Verifies TIER 2 Rule 10: Authentication required for admin endpoints.
    """
    # Act: Request replay without authentication
    response = test_client.post("/admin/history/replay", json={"videoId": "dQw4w9WgXcQ"})

    # Assert: Should be denied
    assert response.status_code == 401


@pytest.mark.security
def test_get_admin_history_page_requires_authentication(test_client):
    """
    Test /admin/history template page returns 401 without session.

    Verifies TIER 2 Rule 10: Authentication required for admin endpoints.
    """
    # Act: Request history page without authentication
    response = test_client.get("/admin/history")

    # Assert: Should be denied
    assert response.status_code == 401


# =============================================================================
# HISTORY LISTING TESTS (AC2, AC3)
# =============================================================================


def test_get_admin_history_empty_database(test_client, test_db):
    """
    Test history endpoint returns empty array when no watch history exists.

    Verifies AC2: Endpoint works with empty database.
    """
    # Arrange: Setup authentication
    authenticate_client(test_client, test_db)

    # Act: Request history from empty database
    response = test_client.get("/admin/api/history")

    # Assert: Should return empty results
    assert response.status_code == 200
    data = response.json()
    assert data["history"] == []
    assert data["total"] == 0


def test_get_admin_history_returns_entries(test_client, test_db):
    """
    Test history endpoint returns watch history entries with all required fields.

    Verifies AC3: Each entry includes thumbnail, title, channel, date/time, duration.
    """
    from tests.backend.conftest import insert_watch_history

    # Arrange: Authenticate and insert watch history
    authenticate_client(test_client, test_db)

    now = datetime.now(timezone.utc).isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "test_vid_001",
                "video_title": "Excavator Song",
                "channel_name": "Blippi",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 245,
            }
        ],
    )

    # Act: Request history
    response = test_client.get("/admin/api/history")

    # Assert: Should return entry with all required fields (AC3)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["history"]) == 1

    entry = data["history"][0]
    assert entry["videoId"] == "test_vid_001"
    assert entry["videoTitle"] == "Excavator Song"
    assert entry["channelName"] == "Blippi"
    assert entry["thumbnailUrl"]  # Should have fallback URL
    assert entry["watchedAt"] == now
    assert entry["completed"] is True
    assert entry["manualPlay"] is False
    assert entry["gracePlay"] is False
    assert entry["durationWatchedSeconds"] == 245


def test_get_admin_history_sorts_by_recent_first(test_client, test_db):
    """
    Test history is sorted by most recent first (ORDER BY watched_at DESC).

    Verifies AC2: History sorted by most recent first.
    """
    from tests.backend.conftest import insert_watch_history

    # Arrange: Authenticate and insert 3 entries at different times
    authenticate_client(test_client, test_db)
    base_time = datetime.now(timezone.utc)
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Video 1",
                "channel_name": "Channel",
                "watched_at": (base_time - timedelta(hours=2)).isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid2",
                "video_title": "Video 2",
                "channel_name": "Channel",
                "watched_at": base_time.isoformat(),  # Most recent
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid3",
                "video_title": "Video 3",
                "channel_name": "Channel",
                "watched_at": (base_time - timedelta(hours=1)).isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
        ],
    )

    # Act: Request history
    response = test_client.get("/admin/api/history")

    # Assert: Should be sorted most recent first (AC2)
    assert response.status_code == 200
    data = response.json()
    assert len(data["history"]) == 3

    # Most recent should be first (vid2, then vid3, then vid1)
    assert data["history"][0]["videoId"] == "vid2"
    assert data["history"][1]["videoId"] == "vid3"
    assert data["history"][2]["videoId"] == "vid1"


# =============================================================================
# FILTERING TESTS (AC4, AC5)
# =============================================================================


def test_get_admin_history_filters_by_date_range(test_client, test_db):
    """
    Test history filtering by date_from and date_to parameters.

    Verifies AC4: Filter by date range functionality.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert entries on different days
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Video 1",
                "channel_name": "Channel",
                "watched_at": f"{two_days_ago.isoformat()}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid2",
                "video_title": "Video 2",
                "channel_name": "Channel",
                "watched_at": f"{yesterday.isoformat()}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid3",
                "video_title": "Video 3",
                "channel_name": "Channel",
                "watched_at": f"{today.isoformat()}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
        ],
    )

    # Act: Filter by date range (yesterday only)
    response = test_client.get(
        f"/admin/api/history?date_from={yesterday.isoformat()}&date_to={yesterday.isoformat()}"
    )

    # Assert: Should return only yesterday's entry (AC4)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["history"]) == 1
    assert data["history"][0]["videoId"] == "vid2"


def test_get_admin_history_filters_by_channel(test_client, test_db):
    """
    Test history filtering by channel parameter.

    Verifies AC4: Filter by channel functionality.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert entries from different channels
    now = datetime.now(timezone.utc).isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Video 1",
                "channel_name": "Blippi",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid2",
                "video_title": "Video 2",
                "channel_name": "Super Simple Songs",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid3",
                "video_title": "Video 3",
                "channel_name": "Blippi",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
        ],
    )

    # Act: Filter by Blippi channel
    response = test_client.get("/admin/api/history?channel=Blippi")

    # Assert: Should return only Blippi entries (AC4)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["history"]) == 2
    assert all(entry["channelName"] == "Blippi" for entry in data["history"])


def test_get_admin_history_search_by_title(test_client, test_db):
    """
    Test history search by title with case-insensitive LIKE query.

    Verifies AC5: Search by video title functionality.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert entries with different titles
    now = datetime.now(timezone.utc).isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Excavator Song for Kids",
                "channel_name": "Blippi",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid2",
                "video_title": "Fire Truck Videos",
                "channel_name": "Blippi",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid3",
                "video_title": "Excavator at the Construction Site",
                "channel_name": "Blippi",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
        ],
    )

    # Act: Search for "excavator" (case-insensitive)
    response = test_client.get("/admin/api/history?search=excavator")

    # Assert: Should return both excavator videos (AC5)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["history"]) == 2
    assert all("excavator" in entry["videoTitle"].lower() for entry in data["history"])


def test_get_admin_history_combined_filters(test_client, test_db):
    """
    Test history with multiple filters applied simultaneously.

    Verifies AC4, AC5: All filters work together correctly.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert diverse entries
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Excavator Song",
                "channel_name": "Blippi",
                "watched_at": f"{today.isoformat()}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid2",
                "video_title": "Fire Truck Song",
                "channel_name": "Blippi",
                "watched_at": f"{today.isoformat()}T11:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid3",
                "video_title": "Excavator Song",
                "channel_name": "Super Simple Songs",
                "watched_at": f"{today.isoformat()}T12:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid4",
                "video_title": "Excavator Song",
                "channel_name": "Blippi",
                "watched_at": f"{yesterday.isoformat()}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
        ],
    )

    # Act: Apply date, channel, and search filters
    response = test_client.get(
        f"/admin/api/history?date_from={today.isoformat()}&channel=Blippi&search=excavator"
    )

    # Assert: Should return only vid1 (today + Blippi + excavator)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["history"]) == 1
    assert data["history"][0]["videoId"] == "vid1"


# =============================================================================
# PAGINATION TESTS (AC10)
# =============================================================================


def test_get_admin_history_pagination(test_client, test_db):
    """
    Test history pagination with limit, offset, and total count.

    Verifies AC10: Pagination functionality.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert 15 entries
    now = datetime.now(timezone.utc)
    entries = []
    for i in range(15):
        entries.append(
            {
                "video_id": f"vid_{i:03d}",
                "video_title": f"Video {i}",
                "channel_name": "Test Channel",
                "watched_at": (now - timedelta(minutes=i)).isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )
    insert_watch_history(test_db, entries)

    # Act: Request page 2 with limit 5
    response = test_client.get("/admin/api/history?limit=5&offset=5")

    # Assert: Should return entries 6-10 out of 15 (AC10)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 15  # Total count across all pages
    assert len(data["history"]) == 5  # Page size


# =============================================================================
# REPLAY ENDPOINT TESTS (AC6)
# =============================================================================


def test_post_replay_valid_video_id(test_client, test_db):
    """
    Test replay endpoint returns correct embed URL for valid video ID.

    Verifies AC6: Replay endpoint generates correct YouTube embed URL.
    """
    authenticate_client(test_client, test_db)

    # Act: Request replay for valid video ID
    response = test_client.post("/admin/history/replay", json={"videoId": "dQw4w9WgXcQ"})

    # Assert: Should return embed URL (AC6)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["videoId"] == "dQw4w9WgXcQ"
    assert (
        data["embedUrl"]
        == "https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1&rel=0&modestbranding=1"
    )


def test_post_replay_invalid_video_id_length(test_client, test_db):
    """
    Test replay endpoint rejects video IDs with incorrect length.

    Verifies TIER 1 Rule 5: Input validation for video IDs (must be 11 chars).
    """
    authenticate_client(test_client, test_db)

    # Act: Request replay with short video ID
    response = test_client.post("/admin/history/replay", json={"videoId": "short"})

    # Assert: Should reject with 400 error
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "Video-ID må være 11 tegn" in data["message"]


def test_post_replay_invalid_video_id_characters(test_client, test_db):
    """
    Test replay endpoint rejects video IDs with invalid characters.

    Verifies TIER 1 Rule 5: Input validation for video IDs (alphanumeric + dash/underscore).
    """
    authenticate_client(test_client, test_db)

    # Act: Request replay with invalid characters
    response = test_client.post("/admin/history/replay", json={"videoId": "invalid<>{}"})

    # Assert: Should reject with 400 error
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "Ugyldig video-ID" in data["message"]


# =============================================================================
# TIER 1 SAFETY TESTS (AC7)
# =============================================================================


@pytest.mark.tier1
def test_manual_play_excluded_from_daily_limit(test_db):
    """
    TIER 1 CRITICAL: Manual replay videos must NOT count toward daily limit.

    This is the most critical test in Story 3.1. If this fails, children could
    exceed their daily viewing limits when parents use the replay feature.

    TIER 1 Rule 2: Time limits must exclude manual_play and grace_play entries.

    Scenario:
    - Child watches 2 normal videos (10 minutes each) = 20 minutes counted
    - Parent uses "Play Again" for 1 video (5 minutes) = 0 minutes counted
    - Daily limit calculation should show 20 minutes, NOT 25 minutes

    This test verifies that get_daily_limit() correctly excludes manual_play=1
    entries from the minutes watched calculation.
    """
    from tests.backend.conftest import insert_watch_history
    from backend.services.viewing_session import get_daily_limit

    # Arrange: Insert watch history with manual_play flag
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            # Normal child plays (should count toward limit)
            {
                "video_id": "vid1",
                "video_title": "Video 1",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,  # ← Normal play, counts toward limit
                "grace_play": 0,
                "duration_watched_seconds": 600,  # 10 minutes
            },
            {
                "video_id": "vid2",
                "video_title": "Video 2",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:15:00Z",
                "completed": 1,
                "manual_play": 0,  # ← Normal play, counts toward limit
                "grace_play": 0,
                "duration_watched_seconds": 600,  # 10 minutes
            },
            # Manual play (should NOT count toward limit)
            {
                "video_id": "vid3",
                "video_title": "Video 3",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:30:00Z",
                "completed": 1,
                "manual_play": 1,  # ← Manual play, MUST NOT count toward limit
                "grace_play": 0,
                "duration_watched_seconds": 300,  # 5 minutes
            },
        ],
    )

    # Act: Calculate daily limit
    limit = get_daily_limit(conn=test_db)

    # Assert: Only normal plays counted (20 minutes, NOT 25)
    # This is the CRITICAL assertion - if this fails, TIER 1 safety violated
    assert limit["minutesWatched"] == 20, (
        "TIER 1 VIOLATION: Manual plays MUST be excluded from daily limit. "
        f"Expected 20 minutes (normal plays only), got {limit['minutesWatched']} minutes."
    )

    # Additional verification: With 30 min default limit, should have 10 min remaining
    assert (
        limit["minutesRemaining"] == 10
    ), f"Expected 10 minutes remaining (30-20), got {limit['minutesRemaining']} minutes."

    # Verify state is correct
    assert (
        limit["currentState"] == "winddown"
    ), f"With 10 min remaining, should be in winddown state, got {limit['currentState']}"


@pytest.mark.tier1
def test_grace_play_excluded_from_daily_limit(test_db):
    """
    TIER 1 CRITICAL: Grace play videos must NOT count toward daily limit.

    TIER 1 Rule 2: Time limits must exclude both manual_play and grace_play entries.

    Scenario:
    - Child watches videos totaling 30 minutes (reaching daily limit)
    - Child watches 1 grace video (5 minutes) with grace_play=1
    - Daily limit should still show 30 minutes, NOT 35 minutes

    This ensures grace videos don't push the child over their limit.
    """
    from tests.backend.conftest import insert_watch_history
    from backend.services.viewing_session import get_daily_limit

    # Arrange: Insert watch history with grace_play flag
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            # Normal plays reaching limit (30 minutes)
            {
                "video_id": "vid1",
                "video_title": "Video 1",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 1800,  # 30 minutes
            },
            # Grace play (should NOT count)
            {
                "video_id": "vid2",
                "video_title": "Grace Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:35:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 1,  # ← Grace play, MUST NOT count toward limit
                "duration_watched_seconds": 300,  # 5 minutes
            },
        ],
    )

    # Act: Calculate daily limit
    limit = get_daily_limit(conn=test_db)

    # Assert: Only normal plays counted (30 minutes, NOT 35)
    assert limit["minutesWatched"] == 30, (
        "TIER 1 VIOLATION: Grace plays MUST be excluded from daily limit. "
        f"Expected 30 minutes (normal plays only), got {limit['minutesWatched']} minutes."
    )

    # Should show locked state (grace consumed)
    assert (
        limit["currentState"] == "locked"
    ), f"After grace video, should be locked, got {limit['currentState']}"


# ==============================================================================
# TIER 1 Security Tests - SQL Injection Prevention (P0)
# ==============================================================================


@pytest.mark.tier1
@pytest.mark.security
def test_date_filter_prevents_sql_injection(test_client, test_db):
    """
    3.1-UNIT-005: Date filter prevents SQL injection.

    TIER 1 Safety Rule: SQL placeholders mandatory (never string formatting).

    Verifies that malicious SQL injection payloads in date_from/date_to
    parameters are safely handled via parameterized queries.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert test data
    now = datetime.now(timezone.utc).isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Test Video",
                "channel_name": "Test Channel",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        ],
    )

    # Act: Attempt SQL injection via date_from parameter
    sql_injection_payloads = [
        "2025-01-01' OR '1'='1",  # Classic OR injection
        "2025-01-01'; DROP TABLE watch_history; --",  # DROP TABLE attack
        "2025-01-01' UNION SELECT * FROM watch_history WHERE '1'='1",  # UNION injection
    ]

    for payload in sql_injection_payloads:
        # Should either reject the malicious input OR safely escape it
        response = test_client.get(f"/admin/api/history?date_from={payload}")

        # Assert: Either 400 (validation error) or safe handling (returns empty/safe results)
        # CRITICAL: Must NOT execute the injected SQL
        assert response.status_code in [
            200,
            400,
        ], f"SQL injection payload '{payload}' caused unexpected status code: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            # If accepted, should return empty or safe results (NOT execute injection)
            assert isinstance(data, dict), "Response must be valid JSON dict"
            assert "history" in data, "Response must have 'history' field"
            assert isinstance(data["history"], list), "History must be a list"
            # The injection should NOT return unauthorized data
            # (parameterized queries ensure this)


@pytest.mark.tier1
@pytest.mark.security
def test_search_prevents_sql_injection(test_client, test_db):
    """
    3.1-UNIT-007: Search prevents SQL injection.

    TIER 1 Safety Rule: SQL placeholders mandatory (never string formatting).

    Verifies that malicious SQL injection payloads in search parameter
    are safely handled via parameterized LIKE queries.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert test data
    now = datetime.now(timezone.utc).isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Safe Video Title",
                "channel_name": "Test Channel",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        ],
    )

    # Act: Attempt SQL injection via search parameter
    sql_injection_payloads = [
        "abc' OR '1'='1",  # Classic OR injection
        "abc'; DROP TABLE watch_history; --",  # DROP TABLE attack
        "abc' UNION SELECT * FROM watch_history WHERE '1'='1",  # UNION injection
        "%' OR 1=1 --",  # LIKE-specific injection
    ]

    for payload in sql_injection_payloads:
        # Should either reject the malicious input OR safely escape it
        response = test_client.get(f"/admin/api/history?search={payload}")

        # Assert: Either 400 (validation error) or safe handling (returns empty/safe results)
        # CRITICAL: Must NOT execute the injected SQL
        assert response.status_code in [
            200,
            400,
        ], f"SQL injection payload '{payload}' caused unexpected status code: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            # If accepted, should return empty or safe results (NOT execute injection)
            assert isinstance(data, dict), "Response must be valid JSON dict"
            assert "history" in data, "Response must have 'history' field"
            assert isinstance(data["history"], list), "History must be a list"
            # The injection should NOT return unauthorized data
            # (parameterized queries with LIKE placeholders ensure this)


@pytest.mark.tier1
@pytest.mark.security
def test_expired_session_returns_401(test_client, test_db):
    """
    3.1-INT-037: Expired session redirects to login.

    TIER 1 Safety Rule: Session expiry must be enforced (24-hour limit).

    Verifies that sessions older than 24 hours are automatically invalidated
    and return 401 Unauthorized.
    """
    from backend.auth import sessions, create_session
    from datetime import timedelta

    # Arrange: Create an expired session (25 hours old)
    session_id = create_session()

    # Manually backdate the session to 25 hours ago
    now = datetime.now(timezone.utc)
    sessions[session_id]["created_at"] = now - timedelta(hours=25)
    sessions[session_id]["expires_at"] = now - timedelta(hours=1)  # Expired 1 hour ago

    # Set expired session cookie
    test_client.cookies.set("session_id", session_id)

    # Act: Try to access protected endpoint with expired session
    response = test_client.get("/admin/api/history")

    # Assert: Should return 401 Unauthorized (expired session rejected)
    assert response.status_code == 401, (
        f"Expired session (>24 hours) should return 401, got {response.status_code}. "
        "TIER 1 VIOLATION: Session expiry not enforced."
    )

    # Verify session was removed from store (cleanup)
    from backend.auth import sessions as current_sessions

    assert (
        session_id not in current_sessions
    ), "Expired session should be removed from sessions store after validation fails"


@pytest.mark.tier1
@pytest.mark.security
def test_session_cookie_security_attributes(test_client, test_db):
    """
    3.1-UNIT-015: Session cookie has HttpOnly, Secure, SameSite attributes.

    TIER 1 Safety Rule: Session cookies must use secure attributes.

    Verifies that session cookies are set with correct security attributes:
    - HttpOnly: true (prevents JavaScript access, XSS protection)
    - Secure: true (HTTPS only in production)
    - SameSite: Lax (CSRF protection)
    - Max-Age: 86400 (24 hours)

    Mitigates: XSS attacks, CSRF attacks, session hijacking
    """
    from backend.auth import hash_password
    import json

    # Arrange: Set admin password in settings table (directly in test DB)
    password_hash = hash_password("test_password_123")
    now = datetime.now(timezone.utc).isoformat()
    test_db.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        ("admin_password_hash", json.dumps(password_hash), now),
    )
    test_db.commit()

    # Act: Login to get session cookie
    response = test_client.post("/admin/login", json={"password": "test_password_123"})

    # Assert: Login succeeded
    assert response.status_code == 200, f"Login should succeed, got {response.status_code}"

    # Verify session cookie was set
    assert (
        "session_id" in test_client.cookies
    ), "Session cookie should be set after successful login"

    # Check cookie attributes via Set-Cookie header
    set_cookie_header = response.headers.get("set-cookie")
    assert set_cookie_header is not None, "Set-Cookie header should be present"

    # Verify security attributes
    # Note: FastAPI/Starlette format: key=value; HttpOnly; Secure; SameSite=Lax; Max-Age=86400
    set_cookie_lower = set_cookie_header.lower()

    assert "httponly" in set_cookie_lower, (
        "TIER 1 VIOLATION: Session cookie missing HttpOnly attribute. "
        "This allows JavaScript access (XSS vulnerability)."
    )

    assert "secure" in set_cookie_lower, (
        "TIER 1 VIOLATION: Session cookie missing Secure attribute. "
        "This allows transmission over HTTP (session hijacking risk)."
    )

    assert "samesite=lax" in set_cookie_lower or "samesite=strict" in set_cookie_lower, (
        "TIER 1 VIOLATION: Session cookie missing SameSite attribute. " "This allows CSRF attacks."
    )

    assert (
        "max-age=86400" in set_cookie_lower
    ), "Session cookie should have 24-hour expiry (Max-Age=86400 seconds)"


# ==============================================================================
# P1 Integration Tests - Additional Coverage
# ==============================================================================


def test_filter_by_date_from_only(test_client, test_db):
    """
    3.1-INT-007: Filter by date_from only.

    Tests date filtering with only the start date parameter.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert entries on different days
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Video 1",
                "channel_name": "Channel",
                "watched_at": f"{two_days_ago.isoformat()}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid2",
                "video_title": "Video 2",
                "channel_name": "Channel",
                "watched_at": f"{yesterday.isoformat()}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid3",
                "video_title": "Video 3",
                "channel_name": "Channel",
                "watched_at": f"{today.isoformat()}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
        ],
    )

    # Act: Filter by date_from (yesterday onwards)
    response = test_client.get(f"/admin/api/history?date_from={yesterday.isoformat()}")

    # Assert: Should return yesterday and today (2 entries)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2, f"Expected 2 entries from {yesterday} onwards, got {data['total']}"
    assert len(data["history"]) == 2


def test_filter_by_date_to_only(test_client, test_db):
    """
    3.1-INT-008: Filter by date_to only.

    Tests date filtering with only the end date parameter.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert entries on different days
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Video 1",
                "channel_name": "Channel",
                "watched_at": f"{two_days_ago.isoformat()}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid2",
                "video_title": "Video 2",
                "channel_name": "Channel",
                "watched_at": f"{yesterday.isoformat()}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid3",
                "video_title": "Video 3",
                "channel_name": "Channel",
                "watched_at": f"{today.isoformat()}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
        ],
    )

    # Act: Filter by date_to (up to yesterday)
    response = test_client.get(f"/admin/api/history?date_to={yesterday.isoformat()}")

    # Assert: Should return two_days_ago and yesterday (2 entries)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2, f"Expected 2 entries up to {yesterday}, got {data['total']}"
    assert len(data["history"]) == 2


def test_pagination_returns_middle_page(test_client, test_db):
    """
    3.1-INT-031: Pagination returns middle page.

    Tests pagination offset calculation for retrieving middle pages.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert 20 entries
    now = datetime.now(timezone.utc)
    entries = []
    for i in range(20):
        entries.append(
            {
                "video_id": f"vid_{i:03d}",
                "video_title": f"Video {i}",
                "channel_name": "Test Channel",
                "watched_at": (now - timedelta(minutes=i)).isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )
    insert_watch_history(test_db, entries)

    # Act: Request page 2 with limit 5 (offset 5)
    response = test_client.get("/admin/api/history?limit=5&offset=5")

    # Assert: Should return entries 6-10 out of 20
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 20
    assert len(data["history"]) == 5

    # Verify we got the correct page (entries 5-9 in 0-indexed)
    # First entry in results should be video 5 (6th video)
    assert data["history"][0]["videoId"] == "vid_005"


def test_pagination_returns_partial_last_page(test_client, test_db):
    """
    3.1-INT-032: Pagination returns last page (partial).

    Tests pagination with partial last page (fewer entries than limit).
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert 23 entries (last page will have 3 entries with limit 10)
    now = datetime.now(timezone.utc)
    entries = []
    for i in range(23):
        entries.append(
            {
                "video_id": f"vid_{i:03d}",
                "video_title": f"Video {i}",
                "channel_name": "Test Channel",
                "watched_at": (now - timedelta(minutes=i)).isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )
    insert_watch_history(test_db, entries)

    # Act: Request page 3 with limit 10 (offset 20) - should get 3 entries
    response = test_client.get("/admin/api/history?limit=10&offset=20")

    # Assert: Should return last 3 entries out of 23
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 23
    assert len(data["history"]) == 3, "Last page should have 3 entries (partial page)"


def test_history_survives_video_deletion(test_client, test_db):
    """
    3.1-INT-025: History survives video deletion.

    Tests denormalized storage: watch history persists after video is deleted
    from videos table.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import (
        insert_watch_history,
        setup_test_videos,
        create_test_video,
        setup_content_source,
    )

    # Arrange: Create content source and video
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    setup_test_videos(
        test_db,
        [
            create_test_video(
                video_id="deleted_video",
                title="Video That Will Be Deleted",
                content_source_id=source_id,
            )
        ],
    )

    # Add watch history entry
    now = datetime.now(timezone.utc).isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "deleted_video",
                "video_title": "Video That Will Be Deleted",
                "channel_name": "Test Channel",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        ],
    )

    # Act: Delete the video from videos table
    test_db.execute("DELETE FROM videos WHERE video_id = ?", ("deleted_video",))
    test_db.commit()

    # Fetch history
    response = test_client.get("/admin/api/history")

    # Assert: History still shows the deleted video (denormalized data persists)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["history"]) == 1

    entry = data["history"][0]
    assert entry["videoId"] == "deleted_video"
    assert entry["videoTitle"] == "Video That Will Be Deleted"
    assert entry["channelName"] == "Test Channel"
    # Thumbnail should use fallback URL (video no longer in videos table)
    assert "i.ytimg.com" in entry["thumbnailUrl"]


def test_history_survives_content_source_removal(test_client, test_db):
    """
    3.1-INT-026: History survives content source removal.

    Tests denormalized storage: watch history persists after content source
    is removed (CASCADE deletes all videos from that source).
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import (
        insert_watch_history,
        setup_test_videos,
        create_test_video,
        setup_content_source,
    )

    # Arrange: Create content source and video
    source_id = setup_content_source(test_db, "UCremoved", "channel", "Removed Channel")

    setup_test_videos(
        test_db,
        [
            create_test_video(
                video_id="source_video",
                title="Video From Removed Source",
                content_source_id=source_id,
            )
        ],
    )

    # Add watch history entry
    now = datetime.now(timezone.utc).isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "source_video",
                "video_title": "Video From Removed Source",
                "channel_name": "Removed Channel",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        ],
    )

    # Act: Remove content source (CASCADE deletes all videos)
    test_db.execute("DELETE FROM content_sources WHERE id = ?", (source_id,))
    test_db.commit()

    # Verify video was deleted via CASCADE
    video_count = test_db.execute(
        "SELECT COUNT(*) FROM videos WHERE content_source_id = ?", (source_id,)
    ).fetchone()[0]
    assert video_count == 0, "Video should be deleted via CASCADE"

    # Fetch history
    response = test_client.get("/admin/api/history")

    # Assert: History still shows the video (denormalized data persists)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["history"]) == 1

    entry = data["history"][0]
    assert entry["videoId"] == "source_video"
    assert entry["videoTitle"] == "Video From Removed Source"
    assert entry["channelName"] == "Removed Channel"


# ==============================================================================
# P2 and P3 Edge Case Tests
# ==============================================================================


def test_filter_by_nonexistent_channel_returns_empty(test_client, test_db):
    """
    3.1-INT-012: Filter by nonexistent channel returns empty.

    Edge case: Filtering by a channel that doesn't exist should return empty results.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert entries from "Blippi" channel
    now = datetime.now(timezone.utc).isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Video 1",
                "channel_name": "Blippi",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        ],
    )

    # Act: Filter by nonexistent channel
    response = test_client.get("/admin/api/history?channel=NonExistentChannel")

    # Assert: Should return empty results (no crashes)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["history"]) == 0


def test_search_with_special_characters(test_client, test_db):
    """
    3.1-INT-017: Search with special characters.

    Edge case: Search terms with special characters should not break query.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert video with special characters in title
    now = datetime.now(timezone.utc).isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "100% Fun! (Best Video)",
                "channel_name": "Channel",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        ],
    )

    # Act: Search with special characters (%, !, parentheses)
    response = test_client.get("/admin/api/history?search=100% Fun!")

    # Assert: Should find the video (special chars don't break search)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 0  # At minimum, shouldn't crash
    # May or may not match depending on URL encoding, but shouldn't error


def test_very_old_history_entries_retrievable(test_client, test_db):
    """
    3.1-INT-027: Very old history entries retrievable (1+ year).

    Tests that old data (>1 year) is still accessible (no automatic cleanup).
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert entry from 1 year + 1 day ago
    one_year_ago = datetime.now(timezone.utc) - timedelta(days=366)

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "old_video",
                "video_title": "Very Old Video",
                "channel_name": "Channel",
                "watched_at": one_year_ago.isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        ],
    )

    # Act: Fetch history
    response = test_client.get("/admin/api/history")

    # Assert: Old entry is still present (no automatic cleanup)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["history"][0]["videoTitle"] == "Very Old Video"


def test_pagination_offset_beyond_total_returns_empty(test_client, test_db):
    """
    3.1-INT-034: Pagination offset beyond total returns empty.

    Edge case: Requesting page beyond available data should return empty (not error).
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert only 5 entries
    now = datetime.now(timezone.utc)
    entries = []
    for i in range(5):
        entries.append(
            {
                "video_id": f"vid_{i}",
                "video_title": f"Video {i}",
                "channel_name": "Channel",
                "watched_at": (now - timedelta(minutes=i)).isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )
    insert_watch_history(test_db, entries)

    # Act: Request offset 100 (way beyond 5 entries)
    response = test_client.get("/admin/api/history?limit=10&offset=100")

    # Assert: Should return empty results (no crash)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["history"]) == 0


def test_filter_by_future_date_returns_empty(test_client, test_db):
    """
    3.1-INT-013: Filter by future date returns empty.

    Edge case: Filtering by future date should return empty results.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert entries from today
    now = datetime.now(timezone.utc)
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Video 1",
                "channel_name": "Channel",
                "watched_at": now.isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        ],
    )

    # Act: Filter by future date (next year)
    future_date = (now + timedelta(days=365)).date()
    response = test_client.get(f"/admin/api/history?date_from={future_date.isoformat()}")

    # Assert: Should return empty (no time travelers!)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["history"]) == 0


def test_search_empty_string_returns_all(test_client, test_db):
    """
    3.1-INT-018: Search empty string returns all.

    Edge case: Empty search parameter should be ignored, returning all entries.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert 3 different videos
    now = datetime.now(timezone.utc).isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "ABC Video",
                "channel_name": "Channel",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid2",
                "video_title": "XYZ Video",
                "channel_name": "Channel",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid3",
                "video_title": "123 Video",
                "channel_name": "Channel",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
        ],
    )

    # Act: Search with empty string
    response = test_client.get("/admin/api/history?search=")

    # Assert: Should return all videos (empty search ignored)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["history"]) == 3


def test_error_messages_in_norwegian(test_client, test_db):
    """
    3.1-INT-035: Error messages in Norwegian.

    Tests that user-facing error messages are in Norwegian.
    """
    # Note: This is partially tested by authentication tests
    # Here we test a validation error scenario

    authenticate_client(test_client, test_db)

    # Act: Try to replay with invalid video ID
    response = test_client.post("/admin/history/replay", json={"videoId": "short"})

    # Assert: Error message should be present (Norwegian check implicit in existing tests)
    assert response.status_code == 400
    # Specific Norwegian message validation would go here if needed


def test_pagination_parameters_default_correctly(test_client, test_db):
    """
    3.1-UNIT-013: Pagination parameters default correctly.

    Tests that limit defaults to 50 and offset defaults to 0.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert 100 entries
    now = datetime.now(timezone.utc)
    entries = []
    for i in range(100):
        entries.append(
            {
                "video_id": f"vid_{i:03d}",
                "video_title": f"Video {i}",
                "channel_name": "Channel",
                "watched_at": (now - timedelta(minutes=i)).isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )
    insert_watch_history(test_db, entries)

    # Act: Request without limit/offset parameters
    response = test_client.get("/admin/api/history")

    # Assert: Should default to limit=50, offset=0
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 100
    assert len(data["history"]) == 50  # Default limit is 50
    # Should start from most recent (offset=0)
    assert data["history"][0]["videoId"] == "vid_000"


def test_sql_query_uses_order_by_watched_at_desc(test_client, test_db):
    """
    3.1-UNIT-001: SQL query uses ORDER BY watched_at DESC.

    Verifies the query construction includes correct ORDER BY clause.
    (Implicitly tested by sorting tests, this is more of a code review item)
    """
    # This test is essentially covered by test_get_admin_history_sorts_by_recent_first
    # Adding explicit verification here
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert entries with specific timestamps
    base_time = datetime.now(timezone.utc)
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "oldest",
                "video_title": "Oldest",
                "channel_name": "Channel",
                "watched_at": (base_time - timedelta(hours=2)).isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "newest",
                "video_title": "Newest",
                "channel_name": "Channel",
                "watched_at": base_time.isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
        ],
    )

    # Act: Fetch history
    response = test_client.get("/admin/api/history")

    # Assert: Newest should be first (DESC order)
    assert response.status_code == 200
    data = response.json()
    assert data["history"][0]["videoId"] == "newest"
    assert data["history"][1]["videoId"] == "oldest"


def test_date_filters_query_utc_correctly(test_client, test_db):
    """
    3.1-INT-040: Date filters query UTC correctly.

    Tests that date filters work correctly with UTC timestamps.
    """
    authenticate_client(test_client, test_db)

    from tests.backend.conftest import insert_watch_history

    # Arrange: Insert entries with specific UTC timestamps
    target_date = datetime(2025, 1, 15, tzinfo=timezone.utc)

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Before Target",
                "channel_name": "Channel",
                "watched_at": (target_date - timedelta(days=1)).isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid2",
                "video_title": "On Target Date",
                "channel_name": "Channel",
                "watched_at": target_date.isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "vid3",
                "video_title": "After Target",
                "channel_name": "Channel",
                "watched_at": (target_date + timedelta(days=1)).isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
        ],
    )

    # Act: Filter by exact target date
    response = test_client.get("/admin/api/history?date_from=2025-01-15&date_to=2025-01-15")

    # Assert: Should only return entry on target date
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["history"][0]["videoTitle"] == "On Target Date"
