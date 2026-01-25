# SWAGA VPN Bot - Production-Ready MVP

A professional, scalable Telegram VPN bot refactored from legacy monolithic architecture.

## 🏗️ Architecture

### Tech Stack
- **Language**: Python 3.11+
- **Bot Framework**: aiogram 3.x (Routers, Dependency Injection)
- **Database**: PostgreSQL + SQLAlchemy 2.0 (Async)
- **VPN Panel**: 3X-UI (MHSanaei fork)
- **Protocol**: VLESS-Reality + xtls-rprx-vision
- **Payments**: YooKassa (Webhook-based)
- **Deployment**: Docker Compose

### Database Schema (Federated Identity)

**Key Design**: User has ONE static UUID synced across all servers.

```
User (telegram_id, username, balance, user_uuid)
  ↓
Subscription (user_id, expiry_date, is_active, plan_type)
  ↓
Key (subscription_id, server_id, key_uuid) [ONE per server per subscription]
  ↓
Server (api_url, credentials, host, port, public_key, short_ids, domain)
```

## 📁 Project Structure

```
MVP-SWAGA-NEW/
├── docker-compose.yml          # PostgreSQL + Bot services
├── Dockerfile                  # Bot container
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── migrate_legacy.py           # SQLite → PostgreSQL migration
├── logs/                       # Application logs
└── src/
    ├── config.py               # Pydantic settings
    ├── main.py                 # Entry point (Bot + FastAPI webhook)
    ├── database/
    │   ├── models.py           # SQLAlchemy models
    │   ├── session.py          # DB connection management
    │   └── migrations.py       # Schema initialization
    ├── services/
    │   ├── xui.py              # 3X-UI API client
    │   └── payment.py          # YooKassa service
    └── bot/
        ├── keyboards.py        # Inline keyboards
        └── handlers/
            └── user.py         # User command handlers
```

## 🚀 Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- 3X-UI panel (MHSanaei fork) running
- YooKassa account configured

### 2. Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
nano .env
```

**Critical settings**:
```env
# Database
DATABASE_URL=postgresql+asyncpg://swaga_user:SECURE_PASSWORD@postgres:5432/swaga

# Bot
BOT_TOKEN=your_bot_token_here
ADMIN_CHAT_ID=your_telegram_id

# 3X-UI Panel
XUI_BASE=https://your-panel.example.com
XUI_USERNAME=admin
XUI_PASSWORD=secure_password
XUI_INBOUND_ID=1

# YooKassa
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET=live_xxxxxxxxxxxxx
WEBHOOK_BASE_URL=https://your-webhook-domain.com
```

### 3. Deploy

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Check health
curl http://localhost:8000/health
```

### 4. Configure YooKassa Webhook

In YooKassa dashboard, set webhook URL:
```
https://your-webhook-domain.com/webhook/yookassa
```

### 5. Add Server Configuration

After deployment, add actual server details to the `servers` table in PostgreSQL:

```sql
INSERT INTO servers (
    name, is_active, api_url, username, password, inbound_id,
    host, port, public_key, short_ids, domain,
    security, network_type, flow, fingerprint, spider_x
) VALUES (
    'Main Server', true,
    'https://panel.example.com', 'admin', 'password', 1,
    'vpn.example.com', 443, 'YOUR_PUBLIC_KEY', 'SHORT_ID_1,SHORT_ID_2', 'example.com',
    'reality', 'xhttp', 'xtls-rprx-vision', 'chrome', '/'
);
```

## 📦 Migration from Legacy

To migrate from the old SQLite-based bot:

```bash
# Run migration script
python migrate_legacy.py --sqlite-path /path/to/old/bot.db --server-name "Main Server"

# Follow post-migration steps from script output
```

**Migration handles**:
- ✅ Users (telegram_id, username, trial_used)
- ✅ Active subscriptions (with expiry dates)
- ✅ Payment history
- ✅ Creates keys for existing subscriptions
- ⚠️ Server config needs manual update after migration

## 🔑 3X-UI Integration

### Critical: JSON Serialization

The MHSanaei 3X-UI fork requires `settings` field as a **JSON string**:

```python
# ✅ CORRECT
payload = {
    "id": 1,
    "settings": '{"clients": [{"uuid": "...", ...}]}'  # String!
}

# ❌ WRONG
payload = {
    "id": 1,
    "settings": {"clients": [...]}  # Object will fail!
}
```

Our `ThreeXUIClient` handles this automatically.

### Flow Configuration

All clients use `xtls-rprx-vision` flow by default (configurable via `VPN_FLOW` env var).

## 💳 Payment Flow

1. User clicks payment button → `YooKassaService.create_payment()`
2. Payment record saved with status `pending`
3. User completes payment on YooKassa
4. YooKassa sends webhook → `/webhook/yookassa`
5. `YooKassaService.process_successful_payment()`:
   - Creates/extends subscription
   - Syncs keys to all active servers
   - Updates payment status to `succeeded`
6. User receives keys automatically via bot message

## 🔄 Background Tasks

### Subscription Reminders (15-minute interval)

- **24h before expiry**: "Subscription expiring tomorrow"
- **Day of expiry**: "Subscription expiring today"
- **After expiry**: Deactivate subscription, notify user

## 🔗 Deep Linking

Generated VLESS links include v2raytun:// deep link for one-click setup:

```
v2raytun://install-config?url=vless%3A%2F%2F...&name=SWAGA
```

Users can tap to auto-import config into V2RayTun app.

## 📊 Scaling Notes

### Current: 1 VPS
- PostgreSQL + Bot in Docker Compose
- Single 3X-UI server

### Scale to 10+ Servers
1. Add servers to `servers` table
2. Payment webhook automatically creates keys on ALL active servers
3. Users get multi-server configs (automatic failover in V2RayTun)

### Scale to 50k Users
1. Use managed PostgreSQL (connection pooling)
2. Deploy bot on multiple instances (polling can run on multiple workers)
3. Redis for distributed locks (if needed)
4. Load balancer for webhook endpoint

## 🛠️ Development

### Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
python -m src.database.migrations

# Run bot
python -m src.main
```

### Testing

```bash
# Test 3X-UI connection
from src.services.xui import ThreeXUIClient

async def test():
    client = ThreeXUIClient(
        base_url="https://panel.example.com",
        username="admin",
        password="password",
    )
    async with client.session():
        clients = await client.list_clients()
        print(f"Found {len(clients)} clients")

asyncio.run(test())
```

## 🔒 Security

- ✅ Environment variables for secrets
- ✅ PostgreSQL with secure passwords
- ✅ HTTPS required for webhook
- ✅ Webhook signature validation (if configured)
- ✅ No secrets in code
- ✅ SQL injection protection (SQLAlchemy ORM)

## 📝 Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | - | PostgreSQL connection URL |
| `BOT_TOKEN` | ✅ | - | Telegram Bot API token |
| `XUI_BASE` | ✅ | - | 3X-UI panel URL |
| `XUI_USERNAME` | ✅ | - | Panel admin username |
| `XUI_PASSWORD` | ✅ | - | Panel admin password |
| `YOOKASSA_SHOP_ID` | ✅ | - | YooKassa shop ID |
| `YOOKASSA_SECRET` | ✅ | - | YooKassa secret key |
| `WEBHOOK_BASE_URL` | ✅ | - | Public webhook URL |
| `ADMIN_CHAT_ID` | ❌ | - | Admin Telegram ID |
| `VPN_FLOW` | ❌ | `xtls-rprx-vision` | VLESS flow control |
| `TRIAL_DAYS` | ❌ | `7` | Trial period duration |
| `PRICE_M1` | ❌ | `130` | 1-month price (RUB) |
| `PRICE_M3` | ❌ | `350` | 3-month price (RUB) |
| `PRICE_M12` | ❌ | `800` | 12-month price (RUB) |

## 🐛 Troubleshooting

### Bot not responding
```bash
docker-compose logs -f bot
# Check for authentication errors or network issues
```

### 3X-UI connection fails
- Verify `XUI_BASE` includes `https://`
- Check credentials
- Test panel accessibility: `curl -k $XUI_BASE/login`

### Payments not processing
- Verify webhook URL is publicly accessible
- Check YooKassa webhook logs
- Check bot logs: `docker-compose logs -f bot | grep -i webhook`

### Database connection errors
- Ensure PostgreSQL is running: `docker-compose ps`
- Check `DATABASE_URL` format
- Verify network connectivity

## 📄 License

Proprietary - SWAGA VPN

## 🤝 Support

For issues and questions:
- Check logs: `docker-compose logs -f bot`
- Review configuration: `.env` file
- Contact: @SWAGASupport_bot (Telegram)

---

**Built with** ❤️ **for scalability and production readiness**
