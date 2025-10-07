# Test Strategy and Standards

**CRITICAL CONTEXT:** This is a child safety application where bugs in time limits or content filtering could allow unlimited viewing or inappropriate content exposure. Testing is not optional - it's a child safety requirement.

## Testing Philosophy

**Approach:** Test-first for safety-critical features, test-after acceptable for UI polish

**Coverage Goals:**
- **Overall Target:** 85% code coverage
- **Safety-Critical Code:** 100% coverage required
  - Time limit calculation
  - Video filtering (banned, unavailable)
  - Daily limit enforcement
  - Admin authentication
  - Input validation
  - Session management
  - Retry logic
  - Partial fetch handling
- **Business Logic:** 90% coverage target
- **UI Components:** 70% coverage acceptable

**Test Pyramid Distribution:**
```
        E2E Tests (8 tests, 6%)
       /                      \
    Integration (18 tests, 13%)
   /                              \
  Unit Tests (108 tests, 81%)
```

**Total: ~134 tests**

**Rationale:** Heavy unit testing for safety logic, integration for API contracts, E2E for critical user journeys only.

---

## Test Types and Organization

### Unit Tests - Backend

**Framework:** pytest 8.0.0  
**Mocking:** pytest-mock 3.12.0  
**Coverage:** pytest-cov 4.1.0  
**Location:** `tests/backend/` mirroring `backend/` structure

**File Convention:**
```
backend/services/viewing_session.py
  → tests/backend/services/test_viewing_session.py

backend/db/queries.py
  → tests/backend/db/test_queries.py
```

**Test Function Naming:**
```python
def test_<function_name>_<scenario>_<expected_result>():
    """
    Test that <function_name> <expected_result> when <scenario>.
    """
```

---

### TIER 1: Child Safety Tests (100% Coverage Required)

These tests verify the 6 critical safety rules from Coding Standards.

```python
# tests/backend/safety/test_tier1_safety_rules.py
"""
TIER 1 CHILD SAFETY TESTS

These tests verify the 6 critical safety rules that directly protect
child safety and time limits. All must pass - failures block deployment.
"""

import pytest
from datetime import datetime, timezone, timedelta
from backend.services.viewing_session import (
    get_videos_for_grid,
    calculate_minutes_watched
)
from backend.services.content_source import add_source
from backend.auth import hash_password, verify_password, create_session, validate_session
from backend.exceptions import ValidationError

# =============================================================================
# RULE 1: Video Selection Filtering
# =============================================================================

@pytest.mark.tier1
def test_rule1_banned_videos_never_appear_in_grid(test_db):
    """
    TIER 1 SAFETY RULE 1: Banned videos must NEVER appear in child's grid.
    
    This is the most critical test - if this fails, child can see banned content.
    """
    # Arrange
    setup_test_videos(test_db, [
        create_test_video("safe123", is_available=True),
        create_test_video("banned456", is_available=True),
        create_test_video("safe789", is_available=True)
    ])
    ban_video(test_db, "banned456")
    
    # Act - Test 50 times to account for randomness
    for _ in range(50):
        videos = get_videos_for_grid(count=10)
        video_ids = [v['videoId'] for v in videos]
        
        # Assert
        assert "banned456" not in video_ids, "CRITICAL: Banned video appeared in grid!"

@pytest.mark.tier1
def test_rule1_unavailable_videos_never_appear_in_grid(test_db):
    """
    TIER 1 SAFETY RULE 1: Unavailable videos must NEVER appear in grid.
    """
    # Arrange
    setup_test_videos(test_db, [
        create_test_video("available123", is_available=True),
        create_test_video("unavailable456", is_available=False)
    ])
    
    # Act - Test 50 times to account for randomness
    for _ in range(50):
        videos = get_videos_for_grid(count=10)
        video_ids = [v['videoId'] for v in videos]
        
        # Assert
        assert "unavailable456" not in video_ids, "CRITICAL: Unavailable video appeared!"

# =============================================================================
# RULE 2: Time Limit Calculation
# =============================================================================

@pytest.mark.tier1
def test_rule2_time_limit_excludes_manual_play(test_db):
    """
    TIER 1 SAFETY RULE 2: Parent's "play again" must NOT count toward child's limit.
    """
    # Arrange
    today = datetime.now(timezone.utc).date().isoformat()
    insert_watch_history(test_db, [
        {"video_id": "v1", "duration_watched_seconds": 300, "watched_at": today,
         "manual_play": False, "grace_play": False, "completed": True},  # 5 min - counts
        {"video_id": "v2", "duration_watched_seconds": 180, "watched_at": today,
         "manual_play": True, "grace_play": False, "completed": True},   # 3 min - excluded
        {"video_id": "v3", "duration_watched_seconds": 240, "watched_at": today,
         "manual_play": False, "grace_play": False, "completed": True},  # 4 min - counts
    ])
    
    # Act
    minutes = calculate_minutes_watched(today)
    
    # Assert
    assert minutes == 9, f"Expected 9 minutes, got {minutes}. Manual play was counted!"

@pytest.mark.tier1
def test_rule2_time_limit_excludes_grace_play(test_db):
    """
    TIER 1 SAFETY RULE 2: Grace video must NOT count toward next day's limit.
    """
    # Arrange
    today = datetime.now(timezone.utc).date().isoformat()
    insert_watch_history(test_db, [
        {"video_id": "v1", "duration_watched_seconds": 300, "watched_at": today,
         "manual_play": False, "grace_play": False, "completed": True},  # 5 min - counts
        {"video_id": "v2", "duration_watched_seconds": 240, "watched_at": today,
         "manual_play": False, "grace_play": True, "completed": True},   # 4 min - excluded
    ])
    
    # Act
    minutes = calculate_minutes_watched(today)
    
    # Assert
    assert minutes == 5, f"Expected 5 minutes, got {minutes}. Grace play was counted!"

# =============================================================================
# RULE 3: UTC Time Operations
# =============================================================================

@pytest.mark.tier1
def test_rule3_time_calculations_use_utc(test_db):
    """
    TIER 1 SAFETY RULE 3: All time operations must use UTC to prevent timezone bugs.
    """
    # Arrange
    utc_now = datetime.now(timezone.utc)
    utc_date = utc_now.date().isoformat()
    
    # Act - Insert watch with current UTC time
    insert_watch_history(test_db, [
        {"video_id": "v1", "duration_watched_seconds": 300, 
         "watched_at": utc_now.isoformat(),
         "manual_play": False, "grace_play": False, "completed": True}
    ])
    
    # Calculate using Python UTC
    python_minutes = calculate_minutes_watched(utc_date)
    
    # Calculate using SQL DATE('now') which should also be UTC
    with get_connection() as conn:
        sql_date = conn.execute("SELECT DATE('now')").fetchone()[0]
    
    # Assert
    assert utc_date == sql_date, "SQL DATE('now') doesn't match Python UTC date!"
    assert python_minutes == 5, "Time calculation failed with UTC"

# =============================================================================
# RULE 4: Admin Password Security
# =============================================================================

@pytest.mark.tier1
def test_rule4_password_uses_bcrypt():
    """
    TIER 1 SAFETY RULE 4: Admin passwords must be hashed with bcrypt.
    """
    # Arrange
    password = "test_admin_password_123"
    
    # Act
    hashed = hash_password(password)
    
    # Assert
    assert hashed.startswith('$2b$'), "Password not hashed with bcrypt!"
    assert len(hashed) == 60, "Bcrypt hash wrong length"
    assert verify_password(password, hashed), "Password verification failed"
    assert not verify_password("wrong_password", hashed), "Wrong password verified!"

# =============================================================================
# RULE 5: Input Validation
# =============================================================================

@pytest.mark.tier1
def test_rule5_sql_injection_blocked():
    """
    TIER 1 SAFETY RULE 5: SQL injection attempts must be blocked.
    """
    injection_attempts = [
        "'; DROP TABLE videos; --",
        "' OR '1'='1",
        "'; DELETE FROM content_sources WHERE '1'='1'; --",
        "admin'--",
        "' UNION SELECT * FROM banned_videos--",
        "1'; UPDATE videos SET is_available=0; --"
    ]
    
    for attempt in injection_attempts:
        with pytest.raises(ValidationError) as exc_info:
            add_source(attempt)
        assert "Invalid" in str(exc_info.value) or "Not a valid" in str(exc_info.value)

@pytest.mark.tier1
def test_rule5_xss_blocked():
    """
    TIER 1 SAFETY RULE 5: XSS attempts must be blocked.
    """
    xss_attempts = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
        "javascript:alert('xss')",
        "<iframe src='javascript:alert(\"xss\")'></iframe>",
        "<<SCRIPT>alert('xss');//<</SCRIPT>",
    ]
    
    for attempt in xss_attempts:
        with pytest.raises(ValidationError):
            add_source(attempt)

# =============================================================================
# RULE 6: SQL Parameterization
# =============================================================================

@pytest.mark.tier1
def test_rule6_sql_uses_placeholders(test_db):
    """
    TIER 1 SAFETY RULE 6: All SQL queries must use placeholders, not f-strings.
    """
    # Arrange - Try to inject via video_id parameter
    malicious_video_id = "abc123' OR '1'='1"
    setup_test_videos(test_db, [
        create_test_video("abc123"),
        create_test_video("def456")
    ])
    
    # Act - Get specific video (should use placeholder)
    from backend.db.queries import get_video_by_video_id
    result = get_video_by_video_id(malicious_video_id)
    
    # Assert - Should return None (no match) not all videos
    assert result is None, "SQL injection succeeded - not using placeholders!"
```

---

### Core Feature Tests

```python
# tests/backend/services/test_viewing_session.py
import pytest
from backend.services.viewing_session import (
    get_videos_for_grid,
    calculate_minutes_watched,
    get_daily_limit,
    should_interrupt_video
)

def test_get_videos_for_grid_returns_requested_count(test_db):
    """Test that grid returns exact number of videos requested."""
    # Arrange
    setup_test_videos(test_db, [create_test_video(f"v{i}") for i in range(20)])
    
    # Act
    videos = get_videos_for_grid(count=9)
    
    # Assert
    assert len(videos) == 9

def test_get_videos_for_grid_respects_max_duration(test_db):
    """Test wind-down mode filters videos by duration."""
    # Arrange
    setup_test_videos(test_db, [
        create_test_video("short1", duration_seconds=240),  # 4 min
        create_test_video("short2", duration_seconds=300),  # 5 min
        create_test_video("long1", duration_seconds=600),   # 10 min
        create_test_video("long2", duration_seconds=720),   # 12 min
    ])
    
    # Act - Request videos under 6 minutes (360 seconds)
    videos = get_videos_for_grid(count=10, max_duration_seconds=360)
    
    # Assert
    for video in videos:
        assert video['durationSeconds'] <= 360, f"Video {video['videoId']} too long!"

def test_should_interrupt_video_allows_short_video(test_db):
    """Test that short videos can finish even when limit reached."""
    # Act - 3 minutes remaining, 4 minute video (fits within 5 min grace)
    should_interrupt = should_interrupt_video(minutes_remaining=3, video_duration_minutes=4)
    
    # Assert
    assert should_interrupt is False, "Short video should be allowed to finish"
```

---

### Unit Tests - Frontend

**Framework:** Vitest 1.1.0  
**DOM Testing:** happy-dom 12.10.3  
**Location:** `tests/frontend/` mirroring `frontend/src/`

```javascript
// tests/frontend/child/grid.test.js
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderGrid } from '../../../frontend/src/child/grid.js';

describe('renderGrid', () => {
  beforeEach(() => {
    document.body.innerHTML = '<div data-grid></div>';
  });

  it('renders video cards for each video', () => {
    // Arrange
    const videos = [
      { videoId: 'abc123', title: 'Test Video 1', thumbnailUrl: '/test1.jpg', durationSeconds: 245 },
      { videoId: 'def456', title: 'Test Video 2', thumbnailUrl: '/test2.jpg', durationSeconds: 180 }
    ];

    // Act
    renderGrid(videos);

    // Assert
    const cards = document.querySelectorAll('.video-card');
    expect(cards.length).toBe(2);
    expect(cards[0].dataset.videoId).toBe('abc123');
    expect(cards[1].dataset.videoId).toBe('def456');
  });

  it('uses correct camelCase field names from API', () => {
    // Arrange - API returns camelCase
    const videos = [
      { 
        videoId: 'abc123',           // Not video_id
        thumbnailUrl: '/test.jpg',   // Not thumbnail_url
        youtubeChannelName: 'Blippi', // Not youtube_channel_name
        durationSeconds: 245         // Not duration_seconds
      }
    ];

    // Act
    renderGrid(videos);

    // Assert
    const card = document.querySelector('.video-card');
    expect(card.dataset.videoId).toBe('abc123');
    const img = card.querySelector('img');
    expect(img.src).toContain('/test.jpg');
  });
});
```

---

### Integration Tests

**Framework:** pytest with FastAPI TestClient  
**Location:** `tests/integration/`

```python
# tests/integration/test_api_integration.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

def test_complete_child_viewing_flow(client, test_db):
    """
    Integration test: Add channel → Videos appear → Watch video → Limit updates.
    """
    # Step 1: Setup - Add channel as admin
    admin_session = admin_login(client, "test_password")
    
    response = client.post(
        '/admin/sources',
        json={'input': 'https://youtube.com/channel/UCtest'},
        cookies={'session_id': admin_session}
    )
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['videosAdded'] > 0
    
    # Step 2: Fetch videos for child grid
    response = client.get('/api/videos?count=9')
    assert response.status_code == 200
    data = response.json()
    assert len(data['videos']) == 9
    assert 'dailyLimit' in data
    assert data['dailyLimit']['minutesRemaining'] == 30
    
    # Step 3: Watch a video
    video_id = data['videos'][0]['videoId']
    response = client.post('/api/videos/watch', json={
        'videoId': video_id,
        'completed': True,
        'durationWatchedSeconds': 300  # 5 minutes
    })
    assert response.status_code == 200
    updated_limit = response.json()['dailyLimit']
    assert updated_limit['minutesWatched'] == 5
    assert updated_limit['minutesRemaining'] == 25

def test_ban_video_integration(client, test_db):
    """
    SAFETY-CRITICAL: Ban video → Verify it never appears in child grid.
    """
    # Setup
    setup_test_videos(test_db, [
        create_test_video("safe123"),
        create_test_video("banned456"),
        create_test_video("safe789")
    ])
    
    # Step 1: Ban the video
    admin_session = admin_login(client, "test_password")
    response = client.post(
        '/admin/videos/ban',
        json={'videoId': 'banned456'},
        cookies={'session_id': admin_session}
    )
    assert response.status_code == 200
    
    # Step 2: Verify banned video NEVER appears (test 20 times)
    for _ in range(20):
        response = client.get('/api/videos?count=50')
        video_ids = [v['videoId'] for v in response.json()['videos']]
        assert "banned456" not in video_ids  # CRITICAL
```

---

### End-to-End Tests

**Framework:** Playwright 1.40.0  
**Location:** `tests/e2e/specs/`

```javascript
// tests/e2e/specs/child-viewing-flow.spec.js
import { test, expect } from '@playwright/test';

test.describe('Child Viewing Flow', () => {
  test('child can select video and player loads', async ({ page }) => {
    await page.goto('http://localhost:8000');
    await page.waitForSelector('.video-card');
    
    const firstCard = page.locator('.video-card').first();
    const videoId = await firstCard.getAttribute('data-video-id');
    
    await firstCard.click();
    
    // Verify YouTube IFrame loads with correct video
    await page.waitForSelector('iframe[src*="youtube.com/embed"]');
    const iframe = page.locator('iframe[src*="youtube.com/embed"]');
    const src = await iframe.getAttribute('src');
    expect(src).toContain(videoId);
    expect(src).toContain('autoplay=1');
    expect(src).toContain('rel=0');
  });

  test('keyboard navigation works on video grid', async ({ page }) => {
    await page.goto('http://localhost:8000');
    
    // Tab to first video card
    await page.keyboard.press('Tab');
    
    // Verify focus is on a video card
    const focusedElement = await page.locator(':focus');
    await expect(focusedElement).toHaveClass(/video-card/);
    
    // Enter should activate video
    await page.keyboard.press('Enter');
    
    // Verify video player loads
    await expect(page.locator('iframe[src*="youtube.com"]')).toBeVisible();
  });
});
```

---

## Local Development Testing

### Backend Testing Setup

```bash
# 1. Install test dependencies
cd /opt/youtube-viewer/app
uv sync  # Installs all dependencies including test tools

# 2. Set test environment variables
export DATABASE_PATH=:memory:  # Use in-memory DB for tests
export YOUTUBE_API_KEY=fake_key_for_tests

# 3. Run all backend tests
uv run pytest tests/backend/ -v

# 4. Run with coverage
uv run pytest tests/backend/ -v --cov=backend --cov-report=html

# 5. Run TIER 1 safety tests only
uv run pytest tests/backend/ -m tier1 -v

# 6. Run specific test file
uv run pytest tests/backend/services/test_viewing_session.py -v
```

### Frontend Testing Setup

```bash
# 1. Install dependencies
cd /opt/youtube-viewer/app/frontend
npm install

# 2. Run all frontend tests
npm test

# 3. With coverage
npm run test:coverage

# 4. Watch mode
npm test -- --watch
```

### E2E Testing Setup

```bash
# 1. Install Playwright
npm install
npx playwright install chromium

# 2. Start test server
export DATABASE_PATH=/tmp/test.db
uv run uvicorn backend.main:app --reload --port 8000

# 3. Run E2E tests
npx playwright test

# 4. Run with UI
npx playwright test --ui
```

---

## Pytest Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
markers = [
    "tier1: TIER 1 child safety tests (must pass)",
    "security: Security-specific tests",
    "performance: Performance benchmark tests"
]
addopts = "-v --strict-markers"

[tool.coverage.run]
omit = [
    "tests/*",
    "backend/main.py",
    "*/__pycache__/*"
]

[tool.coverage.report]
fail_under = 85
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
]
```

---

## Summary

**Test Coverage by Type:**
- Unit Tests (Backend): ~90 tests
- Unit Tests (Frontend): ~18 tests  
- Integration Tests: ~18 tests
- E2E Tests: ~8 tests
- **Total: ~134 tests**

**Distribution:**
- Unit: 108 tests (81%)
- Integration: 18 tests (13%)
- E2E: 8 tests (6%)

**Safety-Critical Coverage:**
- ✅ Video filtering (banned, unavailable) - 100%
- ✅ Time limit calculation (all flag scenarios) - 100%
- ✅ UTC time operations - 100%
- ✅ Password security (bcrypt) - 100%
- ✅ Input validation (SQL injection, XSS) - 100%
- ✅ SQL parameterization - 100%
- ✅ Session management - 100%
- ✅ Retry logic (all scenarios) - 100%
- ✅ Partial fetch handling - 100%

**Overall Coverage Target:** 85%+ (enforced in CI)

---

