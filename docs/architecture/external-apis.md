# External APIs

The application integrates with YouTube's services for video metadata and playback. All integrations are synchronous and run in FastAPI's thread pool.

## YouTube Data API v3 Integration

**Approach:** Synchronous HTTP requests via `google-api-python-client` (naturally sync library)

**No fallback mechanisms.** If YouTube API is unavailable, operations fail with clear error messages. Parent retries later.

**No quota enforcement.** API usage is logged for admin dashboard visibility, but no artificial limits imposed.

**Retry Logic:** Page-level retries with exponential backoff (3 attempts: 0s, 1s, 2s wait times). Non-retryable errors (403 quota, 404 not found) fail immediately.

**Partial Fetch Handling:** If fetching large channel and network fails mid-operation, return what was fetched with `partial: true` flag. Weekly refresh will complete the fetch.

**Key Operations:**

1. **Fetch Channel Videos** - Paginate through all videos with retry logic
2. **Fetch Playlist Videos** - Paginate through all videos with retry logic
3. **Get Video Details** - Fetch duration and metadata
4. **Resolve Channel Name** - Convert name to channel ID

**Typical Usage:**
- Initial setup (8 channels): ~800 quota units
- Weekly refresh (8 channels): ~800 units
- Monthly total: ~4,000 units out of 300,000 available (10k/day × 30 days)
- **Using 1.3% of available quota**

**Error Handling:**
- Network errors with retry: Up to 3 attempts per page with 0s, 1s, 2s backoff
- Quota exceeded (403): "YouTube API quota exceeded. Try again tomorrow."
- Channel not found (404): "Kanal ikke funnet"
- Partial fetch: Return what was fetched, flag as incomplete, offer retry

**Deduplication:**
YouTube API sometimes returns duplicate video IDs. Service deduplicates before saving to database.

## YouTube IFrame Player API

**Purpose:** Video playback in child interface

**Integration:** Client-side JavaScript, loaded from YouTube CDN

**Configuration:**
```javascript
const playerVars = {
    autoplay: 1,
    rel: 0,
    modestbranding: 1,
    fs: 1,
    controls: 1,
    disablekb: 0,
    iv_load_policy: 3,
    cc_load_policy: 0,
    playsinline: 0
};
```

**No API quota impact** - playback doesn't count against Data API limits

**Error Handling:**
- Video unavailable (error 150/100): Mark as unavailable in database, show mascot error, auto-return to grid
- Network interruption: Show mascot message after 30s buffering, offer return button
- Fullscreen not supported: Fallback to maximize in viewport

---

