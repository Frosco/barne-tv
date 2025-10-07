# Core Workflows

This section illustrates key system workflows using sequence diagrams. These diagrams show the interactions between components during critical user journeys, clarifying the architecture in action.

## Workflow 1: Child Watches Video with Error Handling

**User Goal:** Child selects and watches a video, then returns to grid for another selection

```mermaid
sequenceDiagram
    participant Child
    participant Browser
    participant Routes
    participant ViewingSession
    participant DB
    participant YouTubePlayer

    Child->>Browser: Page loads
    Browser->>Routes: GET /api/videos?count=9
    Routes->>ViewingSession: get_videos_for_grid(9)
    ViewingSession->>DB: get_watch_history_for_date(today)
    DB-->>ViewingSession: history[]
    ViewingSession->>DB: get_available_videos(exclude_banned=true)
    DB-->>ViewingSession: available_videos[]
    ViewingSession->>ViewingSession: weighted_random_selection()
    ViewingSession->>DB: get_setting('daily_limit_minutes')
    DB-->>ViewingSession: 30
    ViewingSession-->>Routes: (videos[], dailyLimit{})
    Routes-->>Browser: JSON response
    Browser->>Browser: renderGrid()
    
    Child->>Browser: Clicks video thumbnail
    Browser->>Browser: Disable all cards
    Browser->>YouTubePlayer: Load IFrame API
    YouTubePlayer-->>Browser: API ready
    Browser->>YouTubePlayer: Create player(videoId)
    
    alt Video loads successfully
        YouTubePlayer->>YouTubePlayer: Check fullscreen support
        
        alt Fullscreen supported
            YouTubePlayer->>YouTubePlayer: Request fullscreen
        else Fullscreen not supported
            YouTubePlayer->>Browser: Maximize in viewport
            Browser->>Browser: Set width/height to 100vw/100vh
        end
        
        YouTubePlayer-->>Child: Video plays
        
        alt Normal playback
            Note over Child: Child watches video...
            YouTubePlayer->>Browser: onStateChange: ENDED
            Browser->>Routes: POST /api/videos/watch {completed: true}
            Routes->>ViewingSession: log_watch_and_update(...)
            ViewingSession->>DB: insert_watch_history(manual_play=false, grace_play=false)
            
        else Network interruption
            YouTubePlayer->>Browser: Buffering >30 seconds
            Browser->>Browser: Show mascot "Videoene trenger internett"
            Browser->>Browser: Show "Tilbake til videoer" button
            Child->>Browser: Clicks button
            Browser->>Routes: POST /api/videos/watch {completed: false, partialDuration}
            Routes->>ViewingSession: log_watch_and_update(completed=false)
            ViewingSession->>DB: insert_watch_history(manual_play=false, grace_play=false)
        end
        
    else Video unavailable
        YouTubePlayer->>Browser: Error event (code 150/100)
        Browser->>Routes: POST /api/videos/unavailable {videoId}
        Routes->>DB: UPDATE videos SET is_available=false WHERE video_id=...
        DB-->>Routes: Success
        Browser->>Browser: Show mascot "Oops! Det videoen gjemmer seg!"
        Browser->>Browser: Auto-return after 5 seconds
    end
    
    Browser->>Browser: Destroy player
    Browser->>Routes: GET /api/videos?count=9
    Browser->>Browser: renderGrid()
    Browser-->>Child: Ready for next selection
```

**Key Points:**
- All operations synchronous, run in thread pool
- Grid regenerates with new random selection after each video
- Watch history logged only on video completion (ESC cancels without logging)
- Daily limit recalculated after every watch
- Video unavailability marks ALL duplicate instances globally
- Network interruptions handled with mascot guidance
- Fullscreen fallback for unsupported browsers

## Workflow 2: Time Limit Progression with Warnings

**User Goal:** Child receives progressive warnings as daily limit approaches

```mermaid
sequenceDiagram
    participant Child
    participant Browser
    participant LimitTracker
    participant Routes
    participant ViewingSession
    participant DB

    Note over Browser: Video grid loaded, child watching videos
    
    Browser->>LimitTracker: startLimitTracking()
    LimitTracker->>LimitTracker: setInterval(30 seconds)
    
    loop Every 30 seconds
        LimitTracker->>Routes: GET /api/limit/status
        Routes->>ViewingSession: get_daily_limit()
        ViewingSession->>DB: get_watch_history_for_date(today)
        DB-->>ViewingSession: history[]
        ViewingSession->>ViewingSession: Calculate minutes watched/remaining
        ViewingSession->>DB: get_setting('daily_limit_minutes')
        DB-->>ViewingSession: 30
        ViewingSession-->>Routes: dailyLimit{minutesRemaining: 12}
        Routes-->>LimitTracker: JSON response
        LimitTracker->>LimitTracker: Check thresholds
    end
    
    Note over LimitTracker: 10 minutes remaining threshold crossed
    
    LimitTracker->>Browser: showWarning(10)
    Browser->>Browser: Create warning overlay
    Browser->>Browser: Show mascot + "10 minutter igjen!"
    Browser->>Browser: Play gentle chime (if audio enabled)
    Browser-->>Child: Warning displayed (3 seconds)
    Browser->>Browser: Auto-dismiss after 3s
    
    Note over Child: Child continues watching, 5 min threshold crossed
    
    LimitTracker->>Browser: showWarning(5)
    Browser->>Browser: Show mascot + "5 minutter igjen!"
    Browser-->>Child: Second warning
    
    Note over Child: Limit drops below 10 minutes
    
    LimitTracker->>LimitTracker: minutesRemaining < 10
    LimitTracker->>Browser: applyWinddownMode()
    Browser->>Browser: body.className = 'mode-winddown'
    Browser->>Browser: CSS transitions: softer colors, border glow
    Browser-->>Child: Visual environment changes
    
    Note over Child: Child finishes current video
    
    Browser->>Routes: GET /api/videos?count=9
    Routes->>ViewingSession: get_videos_for_grid(9)
    ViewingSession->>ViewingSession: dailyLimit.minutesRemaining = 8
    ViewingSession->>DB: get_available_videos(max_duration=480)
    DB-->>ViewingSession: videos[]
    
    alt Videos found under 8 minutes
        ViewingSession-->>Routes: Filtered videos[]
    else No videos under 8 minutes
        ViewingSession->>DB: get_available_videos(max_duration=None)
        DB-->>ViewingSession: All videos
        ViewingSession-->>Routes: Fallback to all videos
        Note over ViewingSession: Better to show videos than empty grid
    end
    
    Routes-->>Browser: Short videos (or all if none fit)
    Browser->>Browser: renderGrid() with wind-down styling
    
    Note over Child: 2 minute warning shown
    
    LimitTracker->>Browser: showWarning(2)
    Browser-->>Child: Final warning before limit
    
    Note over Child: Child selects and finishes short video
    
    Browser->>Routes: POST /api/videos/watch
    Routes->>ViewingSession: log_watch_and_update(...)
    ViewingSession->>ViewingSession: Calculate new limit
    ViewingSession->>ViewingSession: minutesRemaining = 0, state = 'grace'
    ViewingSession-->>Routes: dailyLimit{currentState: 'grace'}
    Routes-->>Browser: Limit reached
    
    Browser->>Browser: window.location.href = '/grace'
    Browser-->>Child: Navigate to grace video screen
```

**Key Points:**
- Polling every 30 seconds (not real-time, acceptable for single user)
- Three warnings: 10, 5, 2 minutes (hardcoded thresholds)
- Wind-down mode filters to videos that fit remaining time
- Empty grid fallback: shows all videos if none fit
- Visual mode changes via CSS classes
- Automatic navigation to grace screen when limit hits

## Workflow 3: Mid-Video Limit Reached

**User Goal:** Handle limit being reached while video is playing

```mermaid
sequenceDiagram
    participant Child
    participant Browser
    participant LimitTracker
    participant Routes
    participant ViewingSession
    participant YouTubePlayer

    Note over Child: Child starts 8-minute video with 6 minutes remaining
    
    Browser->>YouTubePlayer: Playing video, duration=480s
    
    loop Every 30 seconds during playback
        LimitTracker->>Routes: GET /api/limit/status
        Routes->>ViewingSession: get_daily_limit()
        ViewingSession->>DB: get_watch_history_for_date(today)
        DB-->>ViewingSession: history (excluding manual_play and grace_play)
        ViewingSession->>ViewingSession: Calculate minutes remaining
        ViewingSession-->>LimitTracker: dailyLimit{minutesRemaining: 2}
        
        LimitTracker->>LimitTracker: Limit reached mid-video!
        LimitTracker->>ViewingSession: should_interrupt_video(2 min, 8 min video)
        ViewingSession->>ViewingSession: video_minutes (8) <= remaining + 5 (7)?
        ViewingSession->>ViewingSession: No, 8 > 7
        
        alt Video finishes within 5 minutes of limit
            ViewingSession-->>LimitTracker: false (don't interrupt)
            Note over LimitTracker: Let video finish per PRD rule
        else Video too long
            ViewingSession-->>LimitTracker: true (interrupt)
            Browser->>Browser: Show limit screen immediately
        end
    end
    
    Note over Child: Video ends naturally (not interrupted)
    
    Browser->>Routes: POST /api/videos/watch
    Routes->>ViewingSession: log_watch_and_update(...)
    ViewingSession->>DB: insert_watch_history(manual_play=false, grace_play=false)
    ViewingSession->>ViewingSession: Recalculate limit (now over by 2 minutes)
    ViewingSession-->>Routes: dailyLimit{currentState: 'grace'}
    Browser->>Browser: window.location.href = '/grace'
```

**Key Rule:** If video will complete within 5 minutes after limit is reached, let it finish. Otherwise interrupt immediately.

## Workflow 4: Grace Video Selection and Goodbye

**User Goal:** Child offered one final video, then sees friendly goodbye message

```mermaid
sequenceDiagram
    participant Child
    participant Browser
    participant Routes
    participant ViewingSession
    participant DB
    participant YouTubePlayer

    Note over Child: Daily limit reached, navigated to /grace
    
    Browser->>Browser: Load grace.html template
    Browser->>Browser: Show mascot + "Vi er ferdige for i dag!"
    Browser->>Browser: Show "Vil du se én til?" question
    Browser-->>Child: Two buttons: "Ja, én til!" / "Nei, ha det!"
    
    alt Child clicks "Ja, én til!"
        Child->>Browser: Click "Ja" button
        Browser->>Routes: GET /api/videos?count=6
        Routes->>ViewingSession: get_videos_for_grid(6)
        ViewingSession->>ViewingSession: dailyLimit.state = 'grace'
        ViewingSession->>DB: get_available_videos(max_duration=300)
        DB-->>ViewingSession: videos[]
        
        alt Videos found under 5 minutes
            ViewingSession-->>Routes: 4-6 grace videos
        else No videos under 5 minutes
            ViewingSession->>DB: get_available_videos(max_duration=None)
            DB-->>ViewingSession: All videos
            ViewingSession->>ViewingSession: Filter to shortest 6 videos
            ViewingSession-->>Routes: Best effort grace videos
        end
        
        Routes-->>Browser: Grace grid videos
        Browser->>Browser: renderGraceGrid() with softer styling
        Browser-->>Child: Grid with 4-6 thumbnails
        
        Child->>Browser: Clicks grace video
        Browser->>YouTubePlayer: Create player, play video
        YouTubePlayer-->>Child: Grace video plays
        
        Note over Child: Video ends
        
        YouTubePlayer->>Browser: onStateChange: ENDED
        Browser->>Routes: POST /api/videos/watch
        Routes->>ViewingSession: log_watch_and_update(..., grace_play=true)
        ViewingSession->>DB: insert_watch_history(
            manual_play=false,
            grace_play=true
        )
        Note over DB: grace_play=true means doesn't count toward limits
        ViewingSession->>ViewingSession: Grace consumed, state='locked'
        ViewingSession-->>Routes: dailyLimit{currentState: 'locked'}
        Routes-->>Browser: Locked state
        
        Browser->>Browser: window.location.href = '/goodbye'
        
    else Child clicks "Nei, ha det!"
        Child->>Browser: Click "Nei" button
        Browser->>Browser: window.location.href = '/goodbye'
    end
    
    Note over Browser: Goodbye screen loads
    
    Browser->>Browser: Load goodbye.html
    Browser->>Browser: Show mascot waving goodbye
    Browser->>Browser: Show "Ha det! Vi ses i morgen!"
    Browser-->>Child: Static goodbye screen
    
    Note over Child: If child tries to access /api/videos
    
    Child->>Browser: Attempts to reload or navigate
    Browser->>Routes: GET /api/videos
    Routes->>ViewingSession: get_videos_for_grid()
    ViewingSession->>ViewingSession: dailyLimit.state = 'locked'
    ViewingSession-->>Routes: Empty videos[], locked state
    Routes-->>Browser: No videos available
    Browser->>Browser: Redirect to /goodbye or show locked message
    Browser-->>Child: Stays on goodbye screen
    
    Note over Child,DB: Midnight UTC arrives
    
    Browser->>Routes: GET /api/limit/status (next day)
    Routes->>ViewingSession: get_daily_limit()
    ViewingSession->>ViewingSession: today = new date
    ViewingSession->>DB: get_watch_history_for_date(today)
    DB-->>ViewingSession: Empty (new day)
    ViewingSession->>ViewingSession: Minutes watched = 0, state = 'normal'
    ViewingSession-->>Routes: dailyLimit{currentState: 'normal'}
    Routes-->>Browser: Unlocked
    Browser->>Browser: window.location.href = '/'
    Browser-->>Child: Normal grid available again
```

**Key Points:**
- Grace grid shows fewer videos (4-6) with stricter filter (≤5 min)
- Grace video logged with `grace_play=true` (doesn't count toward tomorrow's limit)
- After grace video or "Nei" button, app locks until midnight UTC
- State calculation based on current UTC date, resets automatically at midnight
- No countdown timer on goodbye screen (static, peaceful message)
- Empty grace grid fallback: show shortest available videos

## Workflow 5: Parent Adds Channel/Playlist

**User Goal:** Parent adds new YouTube channel/playlist as approved content source

```mermaid
sequenceDiagram
    participant Parent
    participant Browser
    participant Routes
    participant Auth
    participant ContentSource
    participant DB
    participant YouTubeAPI

    Parent->>Browser: Navigate to /admin
    Browser->>Routes: GET /admin (no session cookie)
    Routes->>Auth: Check authentication
    Auth-->>Routes: Not authenticated
    Routes-->>Browser: Redirect to /admin/login
    
    Browser->>Browser: Show login form
    Parent->>Browser: Enter password, click "Logg inn"
    Browser->>Routes: POST /admin/login {password}
    Routes->>Auth: verify_password(password)
    Auth->>DB: get_setting('admin_password_hash')
    DB-->>Auth: bcrypt_hash
    Auth->>Auth: bcrypt.verify(password, hash)
    Auth-->>Routes: True
    Routes->>Auth: create_session()
    Auth->>Auth: Generate session_id, store in memory
    Auth-->>Routes: session_id
    Routes->>Browser: Set-Cookie: session_id (HttpOnly, Secure)
    Routes-->>Browser: {redirect: '/admin/dashboard'}
    Browser->>Browser: Navigate to dashboard
    
    Parent->>Browser: Click "Kanaler" tab
    Browser->>Routes: GET /admin/sources
    Routes->>Auth: require_auth(session_id from cookie)
    Auth->>Auth: validate_session(session_id)
    Auth-->>Routes: Valid
    Routes->>ContentSource: list_sources()
    ContentSource->>DB: get_all_content_sources()
    DB-->>ContentSource: sources[]
    ContentSource-->>Routes: sources[]
    Routes-->>Browser: JSON {sources: [...]}
    Browser->>Browser: Render channel table
    
    Parent->>Browser: Paste channel URL, click "Legg til"
    Browser->>Routes: POST /admin/sources {input: "https://youtube.com/..."}
    Routes->>Auth: require_auth()
    Auth-->>Routes: Valid
    Routes->>ContentSource: add_source(input)
    
    Note over ContentSource: Runs in thread pool (blocking OK)
    
    ContentSource->>ContentSource: _parse_input(url)
    ContentSource->>ContentSource: Extract channel_id: "UCxyz..."
    ContentSource->>DB: get_source_by_source_id("UCxyz...")
    DB-->>ContentSource: None (doesn't exist)
    
    ContentSource->>YouTubeAPI: search().list(channelId="UCxyz...")
    Note over YouTubeAPI: Blocking HTTP call (page 1) with retry
    YouTubeAPI-->>ContentSource: {items: [...], nextPageToken: "token1"}
    ContentSource->>ContentSource: Extract video_ids[]
    
    ContentSource->>YouTubeAPI: videos().list(id="vid1,vid2,...")
    YouTubeAPI-->>ContentSource: Video details with durations
    
    ContentSource->>ContentSource: Store videos in memory
    
    loop Until no more pages (or error after retries)
        ContentSource->>YouTubeAPI: search().list(pageToken="tokenN")
        
        alt API success (within retry limit)
            YouTubeAPI-->>ContentSource: Next page of videos
            ContentSource->>YouTubeAPI: videos().list() for details
            YouTubeAPI-->>ContentSource: Details with durations
        else Network error after 3 retries
            Note over ContentSource: Return partial results (e.g., 600 of 800)
            ContentSource->>ContentSource: Set fetch_complete = False
        end
    end
    
    Note over ContentSource: Deduplication before save
    
    ContentSource->>ContentSource: _deduplicate_videos(videos)
    ContentSource->>DB: insert_content_source(...)
    DB-->>ContentSource: source{id: 3, ...}
    ContentSource->>DB: bulk_insert_videos(videos, source_id=3)
    Note over DB: Single transaction, 600 INSERTs
    DB-->>ContentSource: Success
    ContentSource->>DB: log_api_call('add_source', cost=100)
    DB-->>ContentSource: Logged
    
    alt Complete fetch
        ContentSource-->>Routes: (source{}, 600, True)
        Routes-->>Browser: {success: true, videosAdded: 600, message: "Kanal lagt til: X (600 videoer)"}
    else Partial fetch
        ContentSource-->>Routes: (source{}, 600, False)
        Routes-->>Browser: {success: true, partial: true, videosAdded: 600, 
                             message: "Lagt til 600 videoer (nettverksfeil). 
                             Klikk 'Oppdater' for å hente resten.",
                             retryAvailable: true}
    end
    
    Browser->>Browser: Show success/partial message
    Browser->>Routes: GET /admin/sources (refresh list)
    Routes->>ContentSource: list_sources()
    ContentSource->>DB: get_all_content_sources()
    DB-->>ContentSource: sources[] (including new one)
    ContentSource-->>Routes: sources[]
    Routes-->>Browser: Updated table data
    Browser->>Browser: Re-render table with new channel
    Browser-->>Parent: Channel added, videos available (with partial notice if applicable)
```

**Key Points:**
- YouTube API calls are blocking (acceptable, runs in thread pool)
- Page-level retry logic (3 attempts, 0s/1s/2s backoff)
- Pagination fetches ALL videos, no artificial limit
- Partial fetch returns what was fetched with flag
- Deduplication removes duplicate video IDs before save
- Single database transaction for bulk insert
- Session-based auth with cookies
- Parent sees loading message during fetch
- Clear partial fetch messaging with retry option

## Workflow 6: Parent Uses "Play Again" for Specific Video

**User Goal:** Parent manually plays specific video child requested, bypassing time limit

```mermaid
sequenceDiagram
    participant Parent
    participant Browser
    participant Routes
    participant Auth
    participant DB
    participant YouTubePlayer
    participant Child

    Note over Child,Parent: Child: "I want the excavator video!"
    
    Parent->>Browser: Open /admin (already logged in)
    Browser->>Browser: Session cookie present
    Parent->>Browser: Click "Historikk" tab
    Browser->>Routes: GET /admin/history
    Routes->>Auth: require_auth()
    Auth-->>Routes: Valid session
    Routes->>DB: get_watch_history(limit=50)
    DB-->>Routes: history[] (last 50 videos)
    Routes-->>Browser: JSON {history: [...]}
    
    Browser->>Browser: Render history table grouped by day
    Browser-->>Parent: "I dag" (5 videos), "I går" (12 videos), etc.
    
    Parent->>Browser: Scroll through history
    Parent->>Parent: "There it is - the excavator video!"
    Parent->>Browser: Click "Spill av igjen" button
    
    Browser->>Routes: POST /admin/history/replay {videoId: "abc123"}
    Routes->>Auth: require_auth()
    Auth-->>Routes: Valid
    Routes->>DB: get_video_by_video_id("abc123")
    DB-->>Routes: video{title, channel, duration, ...}
    Routes-->>Browser: {success: true, videoId: "abc123"}
    
    Browser->>Browser: Create fullscreen player container
    Browser->>YouTubePlayer: Load IFrame API (if not loaded)
    YouTubePlayer-->>Browser: API ready
    Browser->>YouTubePlayer: Create player("abc123", autoplay=1)
    YouTubePlayer->>YouTubePlayer: Request fullscreen
    YouTubePlayer-->>Child: Video plays fullscreen
    
    Note over Child: Child watches excavator video
    
    alt Video completes
        YouTubePlayer->>Browser: onStateChange: ENDED
        Browser->>Browser: Calculate duration watched
        Browser->>Routes: POST /api/videos/watch
        Routes->>ViewingSession: log_watch_and_update(..., manual_play=true)
        ViewingSession->>DB: insert_watch_history(manual_play=true, grace_play=false)
        Note over DB: manual_play=true means doesn't count toward limit
        DB-->>Routes: Success
        Routes-->>Browser: Logged
        
        Browser->>Browser: Destroy player
        Browser->>Browser: Stay in admin context
        Browser-->>Parent: Return to history view
        
    else Parent/Child presses ESC
        Browser->>Browser: Exit fullscreen
        Browser->>Browser: Destroy player
        Note over Browser: No watch history logged (canceled)
        Browser-->>Parent: Return to history view
    end
    
    Parent->>Browser: Can close admin, return to child mode
    Browser->>Browser: Navigate to /
    Browser-->>Child: Normal video grid (child mode)
```

**Key Points:**
- Manual playback sets `manual_play=true` flag in watch history
- Manual plays do NOT count toward daily time limit (excluded from calculation)
- Returns to admin context after video (not child grid)
- Parent can play multiple videos in sequence if needed
- ESC at any time cancels without logging
- Clear separation between manual (parent) and automatic (child) playback

---

