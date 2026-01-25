-- ============================================================
-- SWAGA VPN - Production Server Configuration
-- ============================================================
--
-- CRITICAL: Before running this script, replace these 4 values:
--   1. REPLACE_WITH_ADMIN_LOGIN     → Your 3X-UI admin username
--   2. REPLACE_WITH_ADMIN_PASS      → Your 3X-UI admin password
--   3. REPLACE_WITH_REALITY_PUB_KEY → Reality public key from panel
--   4. REPLACE_WITH_SHORT_ID        → Short ID from panel (comma-separated if multiple)
--
-- Execution:
--   docker compose exec -T postgres psql -U swaga_user -d swaga < seed.sql
--
-- Or manually:
--   docker compose exec postgres psql -U swaga_user -d swaga
--   \i /app/seed.sql
-- ============================================================

\echo '============================================================'
\echo 'SWAGA VPN - Seeding Production Server Configuration'
\echo '============================================================'

-- Insert production server configuration
INSERT INTO servers (
    name,
    is_active,
    api_url,
    username,
    password,
    inbound_id,
    host,
    port,
    public_key,
    short_ids,
    domain,
    security,
    network_type,
    flow,
    fingerprint,
    spider_x,
    xhttp_host,
    xhttp_path,
    xhttp_mode,
    created_at,
    updated_at
) VALUES (
    'Main Europe',                                       -- name
    true,                                                -- is_active
    'http://150.241.77.138:2055/JXmOAqpCBtH14wRJ2t',   -- api_url (3X-UI panel with sub-path)
    'REPLACE_WITH_ADMIN_LOGIN',                         -- username ⚠️ REPLACE THIS
    'REPLACE_WITH_ADMIN_PASS',                          -- password ⚠️ REPLACE THIS
    1,                                                   -- inbound_id
    'sub.swaga-vpn.ru',                                 -- host (VPN server address for VLESS)
    443,                                                 -- port
    'REPLACE_WITH_REALITY_PUB_KEY',                     -- public_key ⚠️ REPLACE THIS
    'REPLACE_WITH_SHORT_ID',                            -- short_ids (comma-separated) ⚠️ REPLACE THIS
    'swaga-vpn.ru',                                     -- domain (SNI for Reality)
    'reality',                                           -- security
    'xhttp',                                             -- network_type
    'xtls-rprx-vision',                                 -- flow
    'chrome',                                            -- fingerprint
    '/',                                                 -- spider_x
    'yandex.ru',                                         -- xhttp_host
    '/adv',                                              -- xhttp_path
    'packet-up',                                         -- xhttp_mode
    NOW(),                                               -- created_at
    NOW()                                                -- updated_at
) ON CONFLICT (name) DO UPDATE SET
    api_url = EXCLUDED.api_url,
    username = EXCLUDED.username,
    password = EXCLUDED.password,
    host = EXCLUDED.host,
    port = EXCLUDED.port,
    public_key = EXCLUDED.public_key,
    short_ids = EXCLUDED.short_ids,
    domain = EXCLUDED.domain,
    updated_at = NOW();

\echo ''
\echo '============================================================'
\echo 'Server Configuration Summary:'
\echo '============================================================'

-- Display inserted/updated server
SELECT
    id,
    name,
    host || ':' || port AS vpn_endpoint,
    api_url,
    is_active,
    flow,
    domain AS sni
FROM servers
WHERE name = 'Main Europe';

\echo ''
\echo '⚠️  CRITICAL: Verify these 4 values were replaced:'
\echo '   1. username    → Should NOT be "REPLACE_WITH_ADMIN_LOGIN"'
\echo '   2. password    → Should NOT be "REPLACE_WITH_ADMIN_PASS"'
\echo '   3. public_key  → Should NOT be "REPLACE_WITH_REALITY_PUB_KEY"'
\echo '   4. short_ids   → Should NOT be "REPLACE_WITH_SHORT_ID"'
\echo ''
\echo '✅ Production server configuration seeded!'
\echo ''
\echo 'Next steps:'
\echo '1. Verify bot startup: docker compose logs -f bot'
\echo '2. Test trial activation in Telegram'
\echo '3. Verify 3X-UI connectivity: Check bot logs for "3X-UI authentication successful"'
\echo ''
