# Epic 3: Parent Features & History

**Goal:** Provide comprehensive parent management capabilities and viewing history tracking.

**Deliverable:** Parent has complete control over settings and can review watch history.

## Story 3.1: Watch History and Manual Replay

As a parent,
I want to view complete watch history and manually replay any video,
so that I can see what my child watched and review content.

**Acceptance Criteria:**
1. Admin page displays all watched videos with timestamps
2. History sorted by most recent first
3. Each entry shows: thumbnail, title, channel name, date/time watched, duration
4. Filtering options: by date range, by channel, by child (future-proofing)
5. Search functionality to find specific videos by title
6. "Play Video" button opens video in modal player within admin interface
7. Video plays without adding to child's history (admin preview mode)
8. History data stored permanently (not cleared automatically)
9. Export history to CSV functionality (optional)
10. Pagination for long history lists (50 entries per page)

## Story 3.2: Configuration Settings Interface

As a parent,
I want to configure application settings via the admin interface,
so that I can customize behavior and limits.

**Acceptance Criteria:**
1. Settings page accessible from admin dashboard
2. Daily video limit setting (default: 5 videos, range: 1-20)
3. Audio feedback enable/disable toggle (default: enabled)
4. Mascot interactions enable/disable (default: enabled)
5. Smart selection algorithm enable/disable (default: enabled)
6. Settings stored in database (settings table)
7. Settings changes apply immediately without restart
8. "Reset to Defaults" button available
9. Settings validation (e.g., limit must be positive integer)
10. Settings page includes help text explaining each option

## Story 3.X: Admin Help & Documentation

As a parent using the admin interface,
I want inline help and guidance,
so that I can effectively manage the application.

**Acceptance Criteria:**
1. Help text appears on each admin page explaining functionality
2. Getting Started guide created in Norwegian (docs/getting-started-no.md)
3. FAQ section added to admin interface with common questions
4. Tooltips on complex settings (hover to see explanation)
5. Link to full documentation from admin dashboard
6. Contact/support information displayed (if applicable)
7. Version number displayed in admin footer
8. Help text explains key concepts: channels, playlists, daily limits, etc.

---
