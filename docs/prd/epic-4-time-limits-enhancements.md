# Epic 4: Time Limits & Enhancements

**Goal:** Implement time-based safety features and enhanced video selection for complete MVP.

**Deliverable:** Application with daily limits, warnings, mascot interactions, and smart selection.

## Story 4.1: Time-Based Viewing Limits

As a parent,
I want automatic daily viewing limits,
so that screen time is controlled without manual intervention.

**Acceptance Criteria:**
1. Watch history entries tracked in database (watched_at, duration_watched_seconds, manual_play, grace_play flags)
2. Daily limit retrieved from settings (default: 30 minutes)
3. Time tracking begins when child first starts a video
4. Minutes watched increments based on duration_watched_seconds of each video (excluding manual_play=true and grace_play=true per TIER 1 safety rule)
5. When minute limit reached, redirect to grace screen offering one bonus video
6. Limit resets at midnight UTC (UTC timezone enforced per TIER 1 safety rule, not configurable)
7. Parent can reset limit early via admin interface (deletes today's watch_history entries where manual_play=false and grace_play=false)
8. Watch history persists across browser refreshes (daily limit state recalculated from database on each request)
9. Actual duration watched in seconds counts toward limit (tracked via duration_watched_seconds field)
10. Admin dashboard shows current daily limit status (minutes watched, minutes remaining, current state)

## Story 4.2: Progressive Warning System and Wind-Down Mode

As a child,
I want gentle warnings before time is up,
so that I'm not surprised when videos end.

**Acceptance Criteria:**
1. Warning appears when 10 minutes remaining threshold is crossed (first warning)
2. Warning message: "10 minutter igjen!" displayed prominently
3. Warning uses friendly, encouraging language
4. Two additional warnings: "5 minutter igjen!" at 5 minutes remaining, "2 minutter igjen!" at 2 minutes remaining
5. Wind-down mode activates when less than 10 minutes remaining (visual changes: softer colors, videos filtered to fit remaining time)
6. Mascot appears during warnings with encouraging messages
7. Warnings auto-dismiss after 3 seconds
8. If daily limit set below 10 minutes, only shows warnings for thresholds below the limit (e.g., 8 min limit shows only 5 min and 2 min warnings)
9. Warnings logged for parent review
10. Audio chime plays with warnings (if audio enabled in settings)
11. Frontend polls /api/limit/status every 30 seconds to check remaining time and update UI state
12. During wind-down mode (≤10 min remaining), video grid filtered to max_duration = minutes_remaining × 60 seconds
13. If no videos fit remaining time during wind-down, show all videos (better than empty grid)

## Story 4.3: Grace Video and Mascot Integration

As a child,
I want a friendly goodbye experience with one bonus "grace video",
so that ending feels positive and rewarding.

**Acceptance Criteria:**
1. When daily minute limit reached, "You're All Done!" (grace) screen appears
2. Mascot character prominently displayed with goodbye message
3. Two buttons: "See You Tomorrow!" and "One More Video?"
4. "One More Video?" allowed once per day (grace video)
5. Grace video logged with grace_play=true flag in watch_history (excluded from daily limit calculation per TIER 1 safety rule)
6. After grace video, only goodbye screen shown (no second grace)
7. Grace video entry includes: grace_play=true, manual_play=false, duration_watched_seconds
8. Mascot animation or special visual when grace video granted
9. Goodbye screen includes time remaining until midnight UTC reset
10. All text in Norwegian, child-friendly language
11. Grace video selection grid shows 4-6 videos (fewer than normal 9-video grid)
12. Grace videos filtered to maximum 5 minutes duration (hardcoded constraint)
13. If no videos under 5 minutes available, show shortest available videos as fallback
14. Mid-video limit handling: If currently playing video will complete within 5 minutes after limit reached, allow it to finish before showing grace screen (prevents abrupt interruption)

## Story 4.4: Engagement-Based Smart Selection

As a parent,
I want videos selected based on past engagement,
so that my child sees varied content they enjoy.

**Acceptance Criteria:**
1. Engagement score calculated per video (completion rate, replay frequency)
2. Videos weighted by engagement: high engagement = higher selection probability
3. Recently watched videos (last 24h) have lower weight (encourage variety)
4. Never completely hide videos (always small chance of selection)
5. Parent can reset engagement data via admin interface
6. Selection algorithm balances novelty and familiar favorites
7. Selection feels random to child despite weighting
8. Algorithm maintains variety across multiple channels
9. Edge case handling: all videos recently watched (select randomly)
10. Engagement data tracked in watch_history table (completed boolean, duration_watched_seconds)

## Story 4.5: Audio Feedback System

As a child,
I want fun sounds when I select videos,
so that the experience feels playful and responsive.

**Acceptance Criteria:**
1. Playful "pop" sound on thumbnail click
2. Gentle transition sound when returning to grid
3. Pleasant chime for warnings (not jarring)
4. Parent setting to enable/disable all sounds
5. Volume controls in parent interface
6. Sounds load quickly and don't delay interactions
7. All audio files optimized for web (small file size, <100KB each)
8. Sounds appropriate for young children (no scary or harsh sounds)
9. Fallback: application works perfectly without audio
10. Audio files stored in frontend/public/sounds/ directory

---
