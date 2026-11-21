"""Database schema updater for Distribution models."""

import asyncio
import sqlite3
from app.core.config import settings
from app.db.session import init_db


def alter_existing_sqlite():
    if not settings.async_database_url.startswith("sqlite"):
        return
    db_file = settings.DATA_DIR + "/vantyx.db"
    con = sqlite3.connect(db_file)
    cur = con.cursor()

    # video_sources.is_synthetic
    cur.execute("PRAGMA table_info(video_sources)")
    cols = [r[1] for r in cur.fetchall()]
    if "is_synthetic" not in cols:
        cur.execute("ALTER TABLE video_sources ADD COLUMN is_synthetic BOOLEAN DEFAULT 0 NOT NULL")

    # render_jobs.is_synthetic
    cur.execute("PRAGMA table_info(render_jobs)")
    cols = [r[1] for r in cur.fetchall()]
    if "is_synthetic" not in cols:
        cur.execute("ALTER TABLE render_jobs ADD COLUMN is_synthetic BOOLEAN DEFAULT 0 NOT NULL")

    # publish_schedules additions
    cur.execute("PRAGMA table_info(publish_schedules)")
    cols = [r[1] for r in cur.fetchall()]
    if "slot_name" not in cols:
        cur.execute("ALTER TABLE publish_schedules ADD COLUMN slot_name VARCHAR(32) DEFAULT '09:00' NOT NULL")
    if "privacy_status" not in cols:
        cur.execute("ALTER TABLE publish_schedules ADD COLUMN privacy_status VARCHAR(32) DEFAULT 'private' NOT NULL")
    if "retry_count" not in cols:
        cur.execute("ALTER TABLE publish_schedules ADD COLUMN retry_count INTEGER DEFAULT 0 NOT NULL")
    if "is_mock" not in cols:
        cur.execute("ALTER TABLE publish_schedules ADD COLUMN is_mock BOOLEAN DEFAULT 0 NOT NULL")

    con.commit()
    con.close()


async def main():
    alter_existing_sqlite()
    await init_db()
    print("Database migration for Distribution complete!")


if __name__ == "__main__":
    asyncio.run(main())
