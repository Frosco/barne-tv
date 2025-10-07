# Requirements

## Functional

- **FR1:** The system shall display a configurable grid (4-15 thumbnails) with videos selected using gentle weighted randomization based on past engagement, favoring variety while allowing familiar content
- **FR2:** The system shall provide a password-protected parent interface for managing approved content sources
- **FR3:** The parent interface shall accept YouTube channel URLs, playlist URLs, or channel names to add new content sources
- **FR4:** The system shall play selected videos in fullscreen mode with spacebar (pause/play) and escape (exit fullscreen) keyboard controls
- **FR5:** The system shall automatically return to the video selection grid after each video ends without showing YouTube's end screen or recommendations
- **FR6:** The system shall track watch history and use it to gently deprioritize (not hide) recently watched videos in the selection algorithm
- **FR7:** The system shall display video titles below thumbnails and show channel names during playback
- **FR8:** The system shall enforce time-based daily viewing limits (default 30 minutes) with audio/visual warning at 5 minutes remaining
- **FR9:** The system shall offer a "one more video" grace option when daily limit is reached, limited to videos under 5 minutes
- **FR10:** The system shall implement a "winding down" mode in the last 10 minutes, filtering to show only videos that fit within remaining time using actual duration data
- **FR11:** The system shall display a child-friendly goodbye message after the grace video or when limit is fully reached
- **FR12:** The system shall prevent access to YouTube comments, live chat, and recommendation sections
- **FR13:** All user interface text shall be displayed in Norwegian while preserving original video titles
- **FR14:** The parent interface shall provide ability to remove channels/playlists and adjust grid size per child
- **FR15:** The system shall refresh available videos from approved sources weekly to include new content
- **FR16:** The parent interface shall allow configuration of daily time limit and grid size

## Non-Functional

- **NFR1:** Video playback shall begin within 3 seconds of thumbnail selection on standard broadband connection
- **NFR2:** The thumbnail grid shall render within 1 second of page load
- **NFR3:** The system shall operate within YouTube API daily quota limits for a single household
- **NFR4:** The parent password shall be stored securely using industry-standard hashing
- **NFR5:** The application shall be accessible only via direct URL and not indexed by search engines
- **NFR6:** The system shall function on modern browsers (Chrome, Firefox, Safari, Edge) released within the last 2 years
- **NFR7:** The interface shall be responsive and usable on both desktop and tablet devices
- **NFR8:** The system shall gracefully handle unavailable videos (removed, private, or region-locked)
- **NFR9:** The weighted randomization shall maintain 20-40% familiar content while ensuring 60-80% variety
- **NFR10:** The system shall continue functioning if individual channels or playlists become unavailable
- **NFR11:** No user data or viewing history shall be shared with third parties beyond required YouTube API calls
- **NFR12:** The warning tone/notification shall be audible but not jarring, using child-friendly sounds
