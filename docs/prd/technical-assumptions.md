# Technical Assumptions

## Repository Structure: Monorepo

## Service Architecture: Monolith

## Testing Requirements: Unit + Integration

## Additional Technical Assumptions and Requests

**Frontend Technology:**
- Vanilla JavaScript with minimal dependencies (no build step if possible)
- Simple DOM manipulation for the video grid
- YouTube IFrame API for player embedding
- CSS Grid/Flexbox for responsive layout

**Backend Technology:**
- Python with FastAPI (simple, fast, minimal boilerplate)
- uv for Python package management (fast, modern alternative to pip)
- Jinja2 templates for server-side rendering where appropriate
- Static file serving for assets
- YouTube Data API v3 for both channels and playlists (primary approach)
- RSS parsing as fallback option (only shows 15 most recent videos)

**Database:**
- SQLite for persistence

**YouTube API Configuration:**
- Google Cloud project with YouTube Data API v3 enabled
- API key stored as environment variable
- Daily quota: 10,000 units (sufficient for initial channel loads and daily refreshes)
- Channel video fetch: ~100 units per channel (one-time, then cached)
- Playlist fetch: 1 unit per playlist
- Video metadata caching to minimize repeated API calls

**Deployment:**
- Direct deployment to Hetzner VPS (no Docker unless needed)
- Simple systemd service for the Python app
- Nginx reverse proxy
- Git pull + uv sync for updates
