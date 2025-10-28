# Epic 2: Child Viewing Experience

**Goal:** Implement the child-facing interface for video selection and playback using content from Epic 1.

**Deliverable:** Child can select and watch videos from parent-approved channels in a safe, engaging interface.

## Story 2.1: Child-Friendly Video Grid Interface

As a child,
I want to see colorful video thumbnails in a grid,
so that I can choose what to watch.

**Acceptance Criteria:**
1. HTML page displays a configurable grid of video thumbnails (default 9 videos, range 4-15 per parent setting)
2. Videos selected using weighted random algorithm (60-80% novelty, 20-40% favorites based on watch history)
3. Thumbnails are large and clickable (minimum 200x150px)
4. Video titles appear below thumbnails in readable font
5. Colorful, playful CSS styling with yellow accents (using design system from Story 1.Z)
6. Page works on 1920x1080 screens (laptop primary)
7. Responsive layout adapts for tablet screens (1024x768 minimum)
8. No navigation elements or text-based menus
9. Mascot character visible in corner or header
10. Grid refreshes when returning from video playback
11. Grid size controlled by `grid_size` setting in admin interface (parent-configurable)

## Story 2.2: Video Playback

As a child,
I want to click a video thumbnail and watch the video,
so that I can enjoy the content.

**Acceptance Criteria:**
1. Clicking thumbnail opens full-screen video player
2. YouTube IFrame Player API embedded for playback
3. Player fills entire screen with minimal chrome
   - Primary: Request fullscreen via YouTube IFrame API
   - Fallback: If fullscreen API unsupported, maximize in viewport (100vw/100vh)
4. "Back to Videos" button prominently displayed (large, colorful)
5. Video plays immediately on load (autoplay enabled)
6. Player controls are child-friendly (large play/pause, volume)
7. Video completes and returns to grid automatically
   - Grid fetches NEW random selection from `/api/videos` (not same videos)
   - Response includes updated `dailyLimit` object
8. Back button and ESC key return to grid without reloading entire page
   - ESC key does NOT log watch history (cancelled playback)
   - "Back to Videos" button DOES log partial watch with actual duration
9. Video playback tracked via `POST /api/videos/watch` with parameters:
   - `videoId` (string): YouTube video ID
   - `completed` (boolean): true if video finished, false if interrupted
   - `durationWatchedSeconds` (number): actual seconds watched
   - No explicit timestamp parameter (recorded server-side in UTC)
10. Error handling for failed video loads with specific scenarios:
    - **Video Unavailable** (YouTube error codes 150/100):
      - Show mascot with "Oops! Det videoen gjemmer seg!"
      - Call `POST /api/videos/unavailable` to mark video globally unavailable
      - Auto-return to grid after 5 seconds
    - **Network Interruption** (buffering >30 seconds):
      - Show mascot with "Videoene trenger internett"
      - Display "Tilbake til videoer" button
      - User-initiated return (not automatic)
11. State-based navigation after logging watched video:
    - Check `dailyLimit.currentState` in response
    - If `'grace'`: Navigate to `/grace` screen (limit reached - Story 4.3)
    - If `'locked'`: Navigate to `/goodbye` screen (grace consumed - Story 4.3)
    - Otherwise: Return to normal grid
12. Partial watch logging tracks actual viewing time for interrupted playback

## Story 2.3: Security and SEO Prevention

As a parent,
I want the application to prevent search engine indexing and unauthorized access,
so that the application remains private and safe.

**Implementation Note:** Security headers are primarily configured in Nginx (production reverse proxy), with FastAPI middleware providing defense-in-depth.

**Acceptance Criteria:**
1. robots.txt file created blocking all crawlers (User-agent: *, Disallow: /)
   - File location: `/opt/youtube-viewer/static/robots.txt`
   - Served by Nginx at `/robots.txt` endpoint
2. Meta tags added to all pages (noindex, nofollow, noarchive)
3. X-Robots-Tag HTTP header added to all responses (noindex, nofollow)
4. Google-specific meta tags to prevent indexing (googlebot: noindex)
5. No external analytics or tracking scripts included
6. Content Security Policy (CSP) header configured to restrict external resources:
   - `default-src 'self'`
   - `script-src 'self' https://www.youtube.com https://s.ytimg.com`
   - `style-src 'self' 'unsafe-inline'` (required for dynamic child UI styling)
   - `img-src 'self' https://i.ytimg.com data:`
   - `frame-src https://www.youtube.com` (YouTube IFrame Player)
   - `media-src 'self' https://www.youtube.com`
   - `connect-src 'self'`
   - `font-src 'self'`
   - `object-src 'none'`
   - `base-uri 'self'`
   - `form-action 'self'`
   - `frame-ancestors 'self'`
   - **Development Note:** CSP relaxed for Vite dev server (allows 'unsafe-eval' and WebSocket connections)
7. Child interface has no external links or navigation away from application
8. YouTube player API only loads necessary components
9. HTTPS enforced in production (HTTP redirects to HTTPS):
   - Let's Encrypt certificates via Certbot
   - TLS 1.2 and TLS 1.3 protocols only (no older versions)
   - Strong cipher suites: ECDHE-ECDSA-AES128-GCM-SHA256, ECDHE-RSA-AES128-GCM-SHA256, ECDHE-ECDSA-AES256-GCM-SHA384, ECDHE-RSA-AES256-GCM-SHA384
   - Automatic certificate renewal via systemd timer
10. Admin interface behind authentication (no anonymous access)
11. X-Frame-Options header set to SAMEORIGIN (prevents clickjacking attacks)
12. X-Content-Type-Options header set to nosniff (prevents MIME type sniffing)
13. X-XSS-Protection header set to "1; mode=block" (legacy browser XSS protection)
14. Strict-Transport-Security (HSTS) header configured:
    - max-age=31536000 (1 year)
    - includeSubDomains flag enabled
15. Referrer-Policy header set to strict-origin-when-cross-origin
16. Permissions-Policy header disables unnecessary browser features:
    - geolocation=()
    - microphone=()
    - camera=()
    - payment=()
    - usb=()
    - magnetometer=()
    - gyroscope=()
    - accelerometer=()
17. FastAPI TrustedHostMiddleware configured with ALLOWED_HOSTS from environment variable
18. FastAPI security headers middleware as defense-in-depth (redundant with Nginx but provides protection if Nginx bypassed)

---
