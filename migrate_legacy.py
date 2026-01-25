#!/usr/bin/env python3
"""
Legacy SQLite to PostgreSQL Migration Script

Migrates data from the old main.py SQLite database to the new federated schema.

Usage:
    python migrate_legacy.py --sqlite-path /path/to/bot.db --server-name "Main Server"

Environment:
    Requires .env file with DATABASE_URL and 3X-UI server configuration
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiosqlite
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src.database import init_db, get_session
from src.database.models import User, Server, Subscription, Key, Payment

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


class LegacyMigration:
    """Handles migration from legacy SQLite schema to new PostgreSQL schema."""

    def __init__(self, sqlite_path: str, server_name: str):
        """
        Initialize migration.

        Args:
            sqlite_path: Path to legacy bot.db SQLite file
            server_name: Name for the legacy server
        """
        self.sqlite_path = Path(sqlite_path)
        self.server_name = server_name

        if not self.sqlite_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {self.sqlite_path}")

    async def run(self):
        """Execute full migration."""
        logger.info("=" * 60)
        logger.info("SWAGA VPN - Legacy Database Migration")
        logger.info("=" * 60)
        logger.info(f"Source (SQLite): {self.sqlite_path}")
        logger.info(f"Target (PostgreSQL): {settings.database_url.split('@')[1]}")
        logger.info("")

        # Initialize target database
        logger.info("Initializing target database...")
        await init_db()

        # Get session
        async for session in get_session():
            # Create server
            server = await self._create_server(session)
            logger.info(f"Created server: {server.name} (ID: {server.id})")

            # Migrate users
            users_map = await self._migrate_users(session)
            logger.info(f"Migrated {len(users_map)} users")

            # Migrate subscriptions and keys
            subs_count, keys_count = await self._migrate_subscriptions(session, users_map, server)
            logger.info(f"Migrated {subs_count} subscriptions")
            logger.info(f"Created {keys_count} keys")

            # Migrate payments
            payments_count = await self._migrate_payments(session)
            logger.info(f"Migrated {payments_count} payments")

            logger.info("")
            logger.info("=" * 60)
            logger.info("Migration completed successfully!")
            logger.info("=" * 60)
            logger.info("")
            logger.info("Next steps:")
            logger.info("1. Review migrated data in PostgreSQL")
            logger.info("2. Test bot functionality")
            logger.info("3. Backup legacy SQLite database")
            logger.info("4. Start the new bot with: docker-compose up -d")
            logger.info("")

            break  # Exit after first session

    async def _create_server(self, session: AsyncSession) -> Server:
        """Create the legacy server entry."""
        # Check if server already exists
        result = await session.execute(
            select(Server).where(Server.name == self.server_name)
        )
        existing_server = result.scalar_one_or_none()

        if existing_server:
            logger.warning(f"Server '{self.server_name}' already exists, using existing")
            return existing_server

        # Create new server with config from environment
        server = Server(
            name=self.server_name,
            is_active=True,
            api_url=settings.xui_base,
            username=settings.xui_username,
            password=settings.xui_password,
            inbound_id=settings.xui_inbound_id,
            host="CONFIGURE_ME",  # Need to get from VPN_SERVERS_JSON or manual config
            port=443,
            public_key="CONFIGURE_ME",
            short_ids="CONFIGURE_ME",
            domain="CONFIGURE_ME",
            security="reality",
            network_type="xhttp",
            flow=settings.vpn_flow,
            fingerprint="chrome",
            spider_x="/",
        )

        session.add(server)
        await session.commit()
        await session.refresh(server)

        logger.warning(
            "⚠️  Server created with placeholder values. "
            "Update server configuration in database with actual values!"
        )

        return server

    async def _migrate_users(self, session: AsyncSession) -> Dict[int, User]:
        """
        Migrate users from legacy database.

        Returns:
            Dict mapping legacy user ID to new User object
        """
        users_map = {}

        async with aiosqlite.connect(self.sqlite_path) as sqlite_conn:
            sqlite_conn.row_factory = aiosqlite.Row

            async with sqlite_conn.execute("SELECT * FROM users ORDER BY id") as cursor:
                async for row in cursor:
                    tg_id = row["tg_id"]
                    username = row["username"] or None

                    # Check if user already exists
                    result = await session.execute(
                        select(User).where(User.telegram_id == tg_id)
                    )
                    user = result.scalar_one_or_none()

                    if not user:
                        # Create new user
                        user = User(
                            telegram_id=tg_id,
                            username=username,
                            balance=0.0,
                            trial_used=bool(row.get("trial_used", 0)),
                        )
                        session.add(user)
                        await session.commit()
                        await session.refresh(user)

                    users_map[row["id"]] = user

        return users_map

    async def _migrate_subscriptions(
        self,
        session: AsyncSession,
        users_map: Dict[int, User],
        server: Server,
    ) -> tuple[int, int]:
        """
        Migrate subscriptions and create keys.

        Returns:
            Tuple of (subscriptions_count, keys_count)
        """
        subs_count = 0
        keys_count = 0

        async with aiosqlite.connect(self.sqlite_path) as sqlite_conn:
            sqlite_conn.row_factory = aiosqlite.Row

            async with sqlite_conn.execute("SELECT * FROM users WHERE uuid IS NOT NULL ORDER BY id") as cursor:
                async for row in cursor:
                    legacy_user_id = row["id"]
                    user = users_map.get(legacy_user_id)

                    if not user:
                        logger.warning(f"User not found for legacy ID {legacy_user_id}, skipping")
                        continue

                    uuid = row["uuid"]
                    plan = row.get("plan") or "unknown"
                    sub_expire_str = row.get("sub_expire")

                    if not uuid:
                        continue

                    # Parse expiry date
                    expiry_date = None
                    is_active = False

                    if sub_expire_str:
                        try:
                            expiry_date = datetime.strptime(sub_expire_str, "%Y-%m-%d %H:%M")
                            is_active = expiry_date > datetime.utcnow()
                        except ValueError:
                            logger.warning(f"Invalid expiry date for user {user.telegram_id}: {sub_expire_str}")
                            expiry_date = datetime.utcnow()

                    if not expiry_date:
                        # Default to expired
                        expiry_date = datetime.utcnow()

                    # Check if subscription already exists
                    result = await session.execute(
                        select(Subscription)
                        .where(Subscription.user_id == user.id)
                        .where(Subscription.plan_type == plan)
                    )
                    subscription = result.scalar_one_or_none()

                    if not subscription:
                        # Create subscription
                        subscription = Subscription(
                            user_id=user.id,
                            is_active=is_active,
                            expiry_date=expiry_date,
                            plan_type=plan,
                            notified_24h=bool(row.get("notif_24h", 0)),
                            notified_0h=bool(row.get("notif_0h", 0)),
                            expired_handled=bool(row.get("expired_handled", 0)),
                        )
                        session.add(subscription)
                        await session.commit()
                        await session.refresh(subscription)
                        subs_count += 1

                    # Update user's UUID to match legacy
                    user.user_uuid = uuid
                    await session.commit()

                    # Create key for this subscription on the server
                    result = await session.execute(
                        select(Key)
                        .where(Key.subscription_id == subscription.id)
                        .where(Key.server_id == server.id)
                    )
                    key = result.scalar_one_or_none()

                    if not key:
                        email = f"legacy-{user.telegram_id}"
                        key = Key(
                            subscription_id=subscription.id,
                            server_id=server.id,
                            key_uuid=uuid,
                            email=email,
                            synced_to_panel=True,  # Assume already synced
                            last_sync_at=datetime.utcnow(),
                        )
                        session.add(key)
                        await session.commit()
                        keys_count += 1

        return subs_count, keys_count

    async def _migrate_payments(self, session: AsyncSession) -> int:
        """
        Migrate payment records.

        Returns:
            Number of payments migrated
        """
        payments_count = 0

        try:
            async with aiosqlite.connect(self.sqlite_path) as sqlite_conn:
                sqlite_conn.row_factory = aiosqlite.Row

                # Check if payments table exists
                async with sqlite_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='payments'"
                ) as cursor:
                    if not await cursor.fetchone():
                        logger.info("No payments table in legacy database, skipping")
                        return 0

                async with sqlite_conn.execute("SELECT * FROM payments ORDER BY id") as cursor:
                    async for row in cursor:
                        payment_id = row.get("payment_id")

                        if not payment_id:
                            continue

                        # Check if payment already exists
                        result = await session.execute(
                            select(Payment).where(Payment.payment_id == payment_id)
                        )
                        if result.scalar_one_or_none():
                            continue

                        # Create payment
                        payment = Payment(
                            payment_id=payment_id,
                            telegram_id=row.get("tg_id") or 0,
                            plan_type=row.get("plan") or "unknown",
                            amount=float(row.get("amount") or 0),
                            currency="RUB",
                            status=row.get("status") or "unknown",
                        )

                        session.add(payment)
                        payments_count += 1

                await session.commit()

        except Exception as e:
            logger.error(f"Failed to migrate payments: {e}")

        return payments_count


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate legacy SWAGA VPN SQLite database to PostgreSQL"
    )
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default="bot.db",
        help="Path to legacy SQLite database (default: bot.db)",
    )
    parser.add_argument(
        "--server-name",
        type=str,
        default="Legacy Server",
        help="Name for the migrated server (default: Legacy Server)",
    )

    args = parser.parse_args()

    migration = LegacyMigration(
        sqlite_path=args.sqlite_path,
        server_name=args.server_name,
    )

    asyncio.run(migration.run())


if __name__ == "__main__":
    main()
