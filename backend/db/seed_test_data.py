"""
Seed test data for E2E testing.
Creates watch history entries with various channels, dates, and types.
"""

import os
import sqlite3
from datetime import datetime, timedelta, timezone

DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/test_app.db")


def seed_watch_history():
    """Seed watch history with test data for E2E testing."""
    conn = sqlite3.connect(DATABASE_PATH)

    try:
        # Sample channels
        channels = [
            "Peppa Pig - Official Channel",
            "Bluey - Official",
            "Paw Patrol Official",
            "Sesame Street",
            "Super Simple Songs",
        ]

        # Sample videos (using 11-character YouTube-like video IDs for replay testing)
        videos = [
            ("dQw4w9WgXcQ", "Peppa Goes Swimming", 245, channels[0]),
            ("9bZkp7q19f0", "Bluey plays Keepy Uppy", 420, channels[1]),
            ("jNQXAC9IVRw", "Paw Patrol Saves the Day", 1320, channels[2]),
            ("L_jWHffIx5E", "Elmo's World Full Episode", 900, channels[3]),
            ("XqZsoesa55w", "Baby Shark Dance", 136, channels[4]),
            ("3AtDnEC4zak", "Peppa at the Beach", 300, channels[0]),
            ("kJQP7kiw5Fk", "Bluey and Bingo Play", 480, channels[1]),
            ("ZZ5LpwO-An4", "Paw Patrol Mission", 1200, channels[2]),
            ("1qN72LEQnaU", "Cookie Monster Song", 180, channels[3]),
            ("e_04ZrNroTo", "Wheels on the Bus", 195, channels[4]),
        ]

        # Create watch history entries spanning last 14 days
        base_time = datetime.now(timezone.utc)

        entries = []
        for day_offset in range(14):
            current_date = base_time - timedelta(days=day_offset)

            # 2-4 videos per day
            videos_per_day = 2 + (day_offset % 3)
            for i in range(videos_per_day):
                video_idx = (day_offset * 3 + i) % len(videos)
                video_id, title, duration, channel = videos[video_idx]

                # Vary the time of day
                watch_time = current_date - timedelta(hours=12 + i * 2, minutes=i * 15)

                # Some entries are manual plays (shouldn't count toward limits)
                manual_play = (day_offset + i) % 7 == 0
                grace_play = (day_offset + i) % 11 == 0 and not manual_play

                entries.append(
                    (
                        video_id,
                        title,
                        channel,
                        duration,
                        watch_time.isoformat(),
                        1,  # completed
                        manual_play,
                        grace_play,
                    )
                )

        # Insert watch history
        conn.executemany(
            """
            INSERT INTO watch_history
            (video_id, video_title, channel_name, duration_watched_seconds, watched_at, completed, manual_play, grace_play)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            entries,
        )

        conn.commit()
        print(f"✅ Seeded {len(entries)} watch history entries")

        # Show summary
        cursor = conn.execute("SELECT COUNT(*) FROM watch_history")
        total = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(DISTINCT channel_name) FROM watch_history")
        channels_count = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM watch_history WHERE manual_play = 1")
        manual_count = cursor.fetchone()[0]

        print(f"   Total entries: {total}")
        print(f"   Unique channels: {channels_count}")
        print(f"   Manual plays: {manual_count}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error seeding data: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_watch_history()
