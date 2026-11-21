"""Database schema updater for Orchestration models."""

import asyncio
from app.db.session import init_db


async def main():
    await init_db()
    print("Database migration for Orchestration complete!")


if __name__ == "__main__":
    asyncio.run(main())
