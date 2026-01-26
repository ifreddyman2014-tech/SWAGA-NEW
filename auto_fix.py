#!/usr/bin/env python3
"""
SWAGA VPN - 3X-UI Connection Diagnostic & Auto-Fix Script

This script diagnoses and fixes connection issues between the bot and 3X-UI panel.

Usage:
    # Inside bot container:
    python auto_fix.py

    # Or with custom server ID:
    python auto_fix.py --server-id 1
"""

import asyncio
import logging
import os
import sys
from typing import Optional, Dict, List, Tuple

import aiohttp
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)


class XUIConnectionTester:
    """Tests various 3X-UI API connection combinations."""

    def __init__(self, host: str, port: int, username: str, password: str, root_path: str = ""):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.root_path = root_path.strip("/")
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)

    def _build_test_urls(self) -> List[str]:
        """Build list of URL variations to test."""
        urls = []

        # Direct IP variations
        if self.root_path:
            urls.append(f"http://{self.host}:{self.port}/{self.root_path}")
        urls.append(f"http://{self.host}:{self.port}")

        # Gateway variations (for Docker)
        urls.append(f"http://host.docker.internal:{self.port}/{self.root_path}" if self.root_path else f"http://host.docker.internal:{self.port}")
        urls.append(f"http://172.17.0.1:{self.port}/{self.root_path}" if self.root_path else f"http://172.17.0.1:{self.port}")

        # Localhost variations
        urls.append(f"http://localhost:{self.port}/{self.root_path}" if self.root_path else f"http://localhost:{self.port}")
        urls.append(f"http://127.0.0.1:{self.port}/{self.root_path}" if self.root_path else f"http://127.0.0.1:{self.port}")

        return urls

    async def test_login(self, base_url: str) -> Tuple[bool, Optional[str], Optional[aiohttp.ClientSession]]:
        """
        Test login to 3X-UI panel.

        Returns:
            (success, final_url, session)
        """
        session = aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar(unsafe=True),
            timeout=self.timeout,
        )

        try:
            login_url = f"{base_url}/login"
            payload = {"username": self.username, "password": self.password}

            headers = {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/json; charset=UTF-8",
            }

            logger.info(f"Testing: {login_url}")

            async with session.post(login_url, json=payload, headers=headers, allow_redirects=True) as resp:
                # Check for 307 redirect
                if resp.status == 307:
                    redirect_url = resp.headers.get("Location")
                    logger.warning(f"  → Got 307 redirect to: {redirect_url}")

                    if redirect_url and self.root_path and self.root_path not in redirect_url:
                        # Add root path to base URL
                        new_base = f"{base_url.rstrip('/')}/{self.root_path}"
                        logger.info(f"  → Retrying with: {new_base}/login")

                        async with session.post(f"{new_base}/login", json=payload, headers=headers) as resp2:
                            data = await self._parse_response(resp2)
                            if data.get("success"):
                                logger.info(f"  ✅ LOGIN SUCCESS with redirected URL!")
                                return True, new_base, session

                    await session.close()
                    return False, None, None

                # Normal response
                data = await self._parse_response(resp)

                if data.get("success"):
                    logger.info(f"  ✅ LOGIN SUCCESS!")
                    return True, base_url, session
                else:
                    logger.warning(f"  ❌ Login failed: {data}")
                    await session.close()
                    return False, None, None

        except aiohttp.ClientConnectorError as e:
            logger.warning(f"  ❌ Connection failed: {e}")
            await session.close()
            return False, None, None
        except Exception as e:
            logger.warning(f"  ❌ Error: {e}")
            await session.close()
            return False, None, None

    async def _parse_response(self, resp: aiohttp.ClientResponse) -> Dict:
        """Parse response as JSON or return error dict."""
        try:
            return await resp.json()
        except:
            return {"success": False, "raw": await resp.text()}

    async def find_working_connection(self) -> Optional[Tuple[str, aiohttp.ClientSession]]:
        """
        Try all URL combinations and return working one.

        Returns:
            (working_base_url, authenticated_session) or None
        """
        test_urls = self._build_test_urls()

        logger.info("=" * 80)
        logger.info("TESTING 3X-UI API CONNECTIONS")
        logger.info("=" * 80)

        for url in test_urls:
            success, final_url, session = await self.test_login(url)
            if success:
                return final_url, session

        logger.error("❌ No working connection found!")
        return None

    async def detect_vless_inbound(self, session: aiohttp.ClientSession, base_url: str) -> Optional[int]:
        """
        Fetch all inbounds and find VLESS one.

        Returns:
            Inbound ID or None
        """
        logger.info("")
        logger.info("=" * 80)
        logger.info("AUTO-DETECTING VLESS INBOUND")
        logger.info("=" * 80)

        endpoints = [
            f"{base_url}/panel/api/inbounds/list",
            f"{base_url}/xui/api/inbounds/list",
            f"{base_url}/panel/inbounds/list",
            f"{base_url}/xui/inbounds/list",
        ]

        for endpoint in endpoints:
            try:
                logger.info(f"Trying: {endpoint}")

                async with session.post(endpoint) as resp:
                    data = await self._parse_response(resp)

                    if not data.get("success"):
                        continue

                    obj = data.get("obj")
                    if isinstance(obj, list):
                        inbounds = obj
                    elif isinstance(obj, dict):
                        inbounds = obj.get("inbounds") or obj.get("list") or []
                    else:
                        continue

                    logger.info(f"  → Found {len(inbounds)} inbounds")

                    # Find VLESS inbound
                    for inbound in inbounds:
                        inbound_id = inbound.get("id")
                        protocol = inbound.get("protocol", "").lower()
                        remark = inbound.get("remark", "")
                        port = inbound.get("port")

                        logger.info(f"  → ID {inbound_id}: {protocol} | {remark} | Port {port}")

                        if protocol == "vless":
                            logger.info(f"  ✅ FOUND VLESS INBOUND: ID = {inbound_id}")
                            return inbound_id

                    if inbounds:
                        # Return first inbound if no VLESS found
                        first_id = inbounds[0].get("id")
                        logger.warning(f"  ⚠️  No VLESS found, using first inbound: ID = {first_id}")
                        return first_id

            except Exception as e:
                logger.warning(f"  ❌ Error: {e}")
                continue

        logger.error("❌ Could not detect inbound ID")
        return None


async def main():
    """Main diagnostic routine."""
    logger.info("=" * 80)
    logger.info("SWAGA VPN - 3X-UI CONNECTION DIAGNOSTIC & AUTO-FIX")
    logger.info("=" * 80)
    logger.info("")

    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("❌ DATABASE_URL environment variable not set!")
        sys.exit(1)

    logger.info(f"Database: {db_url.split('@')[1] if '@' in db_url else 'configured'}")

    # Connect to database
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Fetch server 1 credentials
        logger.info("")
        logger.info("=" * 80)
        logger.info("FETCHING SERVER CREDENTIALS FROM DATABASE")
        logger.info("=" * 80)

        result = await session.execute(
            text("SELECT id, name, api_url, username, password, inbound_id, host, port FROM servers WHERE id = 1")
        )
        row = result.fetchone()

        if not row:
            logger.error("❌ Server ID 1 not found in database!")
            logger.info("\nRun this to check existing servers:")
            logger.info("  docker compose exec postgres psql -U swaga_user -d swaga -c 'SELECT id, name, api_url FROM servers;'")
            sys.exit(1)

        server_id, name, api_url, username, password, inbound_id, vpn_host, vpn_port = row

        logger.info(f"Server ID: {server_id}")
        logger.info(f"Name: {name}")
        logger.info(f"Current api_url: {api_url}")
        logger.info(f"Username: {username}")
        logger.info(f"Password: {'*' * len(password)}")
        logger.info(f"Current inbound_id: {inbound_id}")
        logger.info(f"VPN Host: {vpn_host}")
        logger.info(f"VPN Port: {vpn_port}")
        logger.info("")

        # Parse host and port from api_url
        if "://" in api_url:
            parts = api_url.split("://")[1].split(":")
            host = parts[0]
            port_and_path = parts[1] if len(parts) > 1 else "2055"
            port = int(port_and_path.split("/")[0])
            root_path = "/".join(port_and_path.split("/")[1:])
        else:
            host = "150.241.77.138"
            port = 2055
            root_path = "JXmOAqpCBtH14wRJ2t"

        logger.info(f"Extracted: host={host}, port={port}, root_path={root_path}")
        logger.info("")

        # Test connections
        tester = XUIConnectionTester(host, port, username, password, root_path)
        result = await tester.find_working_connection()

        if not result:
            logger.error("")
            logger.error("=" * 80)
            logger.error("❌ DIAGNOSTIC FAILED - NO WORKING CONNECTION FOUND")
            logger.error("=" * 80)
            logger.error("")
            logger.error("Possible issues:")
            logger.error("  1. Panel is not running on host")
            logger.error("  2. Port 2055 is blocked by firewall")
            logger.error("  3. Wrong username/password in database")
            logger.error("  4. Docker network issue")
            logger.error("")
            logger.error("Manual checks:")
            logger.error(f"  curl http://{host}:{port}/login")
            logger.error(f"  docker compose exec bot ping {host}")
            sys.exit(1)

        working_url, authenticated_session = result

        # Detect inbound ID
        detected_inbound_id = await tester.detect_vless_inbound(authenticated_session, working_url)

        await authenticated_session.close()

        # Generate fix
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ DIAGNOSTIC COMPLETE - GENERATING FIX")
        logger.info("=" * 80)
        logger.info("")

        if api_url == working_url and inbound_id == detected_inbound_id:
            logger.info("✅ Configuration is already correct! No fix needed.")
        else:
            logger.info("🔧 CONFIGURATION FIX REQUIRED")
            logger.info("")
            logger.info("Current configuration:")
            logger.info(f"  api_url: {api_url}")
            logger.info(f"  inbound_id: {inbound_id}")
            logger.info("")
            logger.info("Correct configuration:")
            logger.info(f"  api_url: {working_url}")
            logger.info(f"  inbound_id: {detected_inbound_id}")
            logger.info("")
            logger.info("=" * 80)
            logger.info("RUN THIS SQL TO FIX:")
            logger.info("=" * 80)
            logger.info("")

            sql = f"""
UPDATE servers
SET
    api_url = '{working_url}',
    inbound_id = {detected_inbound_id},
    updated_at = NOW()
WHERE id = {server_id};

-- Verify the fix:
SELECT id, name, api_url, inbound_id FROM servers WHERE id = {server_id};
""".strip()

            print(sql)

            logger.info("")
            logger.info("=" * 80)
            logger.info("HOW TO APPLY THE FIX:")
            logger.info("=" * 80)
            logger.info("")
            logger.info("Option 1: Run SQL directly")
            logger.info("  docker compose exec postgres psql -U swaga_user -d swaga")
            logger.info("  # Then paste the SQL above")
            logger.info("")
            logger.info("Option 2: Restart bot after manual fix")
            logger.info("  docker compose restart bot")
            logger.info("")

        logger.info("=" * 80)
        logger.info("✅ DIAGNOSTIC COMPLETE")
        logger.info("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n\n❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
