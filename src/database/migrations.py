"""Database migrations entry point."""

import asyncio
import logging

from .session import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run database migrations."""
    logger.info("Running database migrations...")
    await init_db()
    logger.info("Migrations completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
