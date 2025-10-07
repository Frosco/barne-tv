# Epic 4: Time Limits & Enhancements

**Goal:** Implement time-based safety features and enhanced video selection for complete MVP.

**Deliverable:** Application with daily limits, warnings, mascot interactions, and smart selection.

## Story 4.1: Time-Based Viewing Limits

As a parent,
I want automatic daily viewing limits,
so that screen time is controlled without manual intervention.

**Acceptance Criteria:**
1. Viewing session tracked in database (start time, video count, status)
2. Daily limit retrieved from settings (default: 5 videos)
3. Session starts when child first selects a video
4. Video counter increments with each completed video
5. When limit reached, redirect to "That's All for Today" screen
6. Limit resets at midnight (configurable timezone)
7. Parent can reset limit early via admin interface
8. Session persists across browser refreshes
9. Partial videos count toward limit (>50% watched)
10. Admin dashboard shows current session status

## Story 4.2: Progressive Warning System and Wind-Down Mode

As a child,
I want gentle warnings before time is up,
so that I'm not surprised when videos end.

**Acceptance Criteria:**
1. Warning appears after video N-2 (e.g., after video 3 of 5)
2. Warning message: "2 videoer igjen!" displayed prominently
3. Warning uses friendly, encouraging language
4. After video N-1, message: "1 video igjen!"
5. Wind-down mode activates at video N-1 (visual changes: softer colors)
6. Mascot appears during warnings with encouraging messages
7. Warnings dismissible with "Ok, jeg forstår" button
8. No warnings if limit is 1 video (goes straight to goodbye)
9. Warnings logged for parent review
10. Audio chime plays with warnings (if audio enabled in settings)

## Story 4.3: Grace Video and Mascot Integration

As a child,
I want a friendly goodbye experience with one bonus "grace video",
so that ending feels positive and rewarding.

**Acceptance Criteria:**
1. After final video (video N), "You're All Done!" screen appears
2. Mascot character prominently displayed with goodbye message
3. Two buttons: "See You Tomorrow!" and "One More Video?"
4. "One More Video?" allowed once per day (grace video)
5. Grace video counted separately (not in daily limit)
6. After grace video, only goodbye screen shown (no second grace)
7. Grace video tracked in database with flag
8. Mascot animation or special visual when grace video granted
9. Goodbye screen includes time remaining until reset (e.g., "Come back in 8 timer!")
10. All text in Norwegian, child-friendly language

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
10. Engagement data tracked in database (views table with completion percentage)

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
