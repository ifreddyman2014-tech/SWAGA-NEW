-- SWAGA VPN - Test Server Seed Data
-- Execute this after database initialization
--
-- Usage:
--   docker compose exec -T postgres psql -U swaga_user -d swaga < seed.sql
--
-- Or manually:
--   docker compose exec postgres psql -U swaga_user -d swaga
--   \i /app/seed.sql

\echo '=========================================='
\echo 'SWAGA VPN - Seeding Test Server'
\echo '=========================================='

-- Insert test server
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
    'Test Server',                       -- name
    true,                                -- is_active
    'http://127.0.0.1:2053',            -- api_url (3X-UI panel)
    'admin',                             -- username
    'password',                          -- password
    1,                                   -- inbound_id
    '127.0.0.1',                        -- host (VPN server address)
    443,                                 -- port
    'pk_test_public_key_placeholder',   -- public_key (Reality public key)
    'short_id_test',                    -- short_ids (comma-separated)
    'test.local',                       -- domain (SNI for Reality)
    'reality',                           -- security
    'xhttp',                             -- network_type
    'xtls-rprx-vision',                 -- flow
    'chrome',                            -- fingerprint
    '/',                                 -- spider_x
    'yandex.ru',                         -- xhttp_host
    '/adv',                              -- xhttp_path
    'packet-up',                         -- xhttp_mode
    NOW(),                               -- created_at
    NOW()                                -- updated_at
) ON CONFLICT (name) DO NOTHING;

\echo ''
\echo '=========================================='
\echo 'Seed Data Summary:'
\echo '=========================================='

-- Show inserted server
SELECT
    id,
    name,
    host,
    port,
    api_url,
    is_active,
    flow
FROM servers
ORDER BY id;

\echo ''
\echo '✅ Test server seeded successfully!'
\echo ''
\echo 'Next steps:'
\echo '1. Verify bot startup: docker compose logs -f bot'
\echo '2. Update server config with real values for production'
\echo '3. Test trial activation in Telegram bot'
\echo ''
