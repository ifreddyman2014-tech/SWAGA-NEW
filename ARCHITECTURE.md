# SWAGA VPN - Architecture Overview

## Executive Summary

SWAGA VPN is a production-ready, scalable Telegram bot for VPN service delivery. Refactored from a legacy monolithic architecture to a modern, maintainable system designed to scale from 1 VPS to 50k+ users without refactoring.

## Key Design Decisions

### 1. Federated Identity Schema

**Problem**: Legacy system stored server configs in User table, making multi-server scaling impossible.

**Solution**: Relational schema with separation of concerns:
```
User → Subscription → Key → Server
```

**Benefits**:
- One static UUID per user (synced across all servers)
- Easy to add new servers without data migration
- Clear subscription lifecycle management
- Supports multiple active subscriptions per user (future)

### 2. Async Architecture

**Components**:
- **aiogram 3.x**: Modern async Telegram bot framework with routers
- **SQLAlchemy 2.0**: Async ORM with connection pooling
- **aiohttp**: Async HTTP client for 3X-UI and YooKassa
- **FastAPI**: Async webhook server

**Benefits**:
- Handle 1000+ concurrent requests
- Non-blocking I/O for all external calls
- Efficient resource utilization
- Scales horizontally

### 3. Webhook-Based Payments

**Legacy**: Polling-based payment checking (inefficient, delayed)

**Modern**: YooKassa webhook → instant activation

**Flow**:
```
User clicks payment → YooKassa → User pays
                                     ↓
                         Webhook: payment.succeeded
                                     ↓
                         Auto-activate subscription
                                     ↓
                         Sync keys to all servers
                                     ↓
                         Send config to user
```

**Benefits**:
- Instant activation (no polling delay)
- Reliable (retry logic built-in)
- Scalable (webhook can handle 1000s of payments)

### 4. Service Layer Pattern

**Structure**:
```
Handlers (bot/handlers/) → Services (services/) → Database (database/)
                                ↓
                         External APIs (3X-UI, YooKassa)
```

**Benefits**:
- Clear separation of concerns
- Testable business logic
- Easy to swap implementations
- Reusable across different interfaces

## Scalability Path

### Current (1 VPS)
```
┌─────────────────────┐
│  VPS (Single Node)  │
│                     │
│  ┌──────────────┐   │
│  │ PostgreSQL   │   │
│  └──────────────┘   │
│  ┌──────────────┐   │
│  │ Bot + Webhook│   │
│  └──────────────┘   │
│  ┌──────────────┐   │
│  │ 3X-UI Server │   │
│  └──────────────┘   │
└─────────────────────┘
```

**Capacity**: ~5k users

### Scale to 10 Servers
```
┌──────────────┐
│  PostgreSQL  │
│  (Managed)   │
└──────────────┘
       ↑
       │
┌──────────────┐
│  Bot + API   │
│  (1 instance)│
└──────────────┘
       ↓
  ┌────┴────┬────┬────┬─────┐
  ↓         ↓    ↓    ↓     ↓
Server1  Server2 ... Server10
```

**Changes needed**: Just add servers to `servers` table

**Capacity**: ~25k users

### Scale to 50k Users
```
                    ┌──────────────┐
                    │ Load Balancer│
                    └──────────────┘
                           ↓
         ┌─────────────────┴─────────────────┐
         ↓                 ↓                  ↓
    ┌────────┐       ┌────────┐        ┌────────┐
    │Bot Inst│       │Bot Inst│        │Bot Inst│
    │   1    │       │   2    │        │   3    │
    └────────┘       └────────┘        └────────┘
         └─────────────────┬─────────────────┘
                           ↓
                  ┌─────────────────┐
                  │  PostgreSQL     │
                  │  (Managed/HA)   │
                  └─────────────────┘
                           ↓
              ┌────────────┴────────────┐
              ↓                         ↓
         ┌─────────┐              ┌─────────┐
         │ Redis   │              │ 20+     │
         │ (Cache) │              │ Servers │
         └─────────┘              └─────────┘
```

**Changes needed**:
- Move to managed PostgreSQL (connection pooling)
- Deploy multiple bot instances
- Add Redis for distributed state (optional)
- Use webhook mode instead of polling (already supported)

**Capacity**: 50k+ users

## Critical Implementation Details

### 3X-UI JSON Serialization

**The Problem**:
MHSanaei 3X-UI fork requires `settings` field as a JSON **string**, not an object.

**Wrong**:
```python
payload = {
    "id": 1,
    "settings": {"clients": [...]}  # ❌ Will fail!
}
```

**Correct**:
```python
payload = {
    "id": 1,
    "settings": json.dumps({"clients": [...]})  # ✅ String
}
```

**Implementation**: `src/services/xui.py` handles this automatically in all methods.

### Deep Linking Strategy

**Format**: `v2raytun://install-config?url={encoded_vless}&name=SWAGA`

**Why v2raytun**:
- Most popular iOS/Android VLESS client in Russia
- Supports one-click config import
- Handles multiple servers (automatic failover)

**Implementation**: `src/bot/handlers/user.py::build_v2raytun_deeplink()`

### Payment Idempotency

**Challenge**: Ensure payment is processed exactly once, even with webhook retries.

**Solution**:
1. Unique `payment_id` from YooKassa (database constraint)
2. Check payment status before processing
3. Atomic database transaction

**Implementation**: `src/services/payment.py::process_successful_payment()`

### Subscription Lifecycle

```
User                  Trial                Paid
 │                      │                   │
 ├─ Activate Trial ────►│                   │
 │                      │                   │
 │                      ├─ 24h reminder     │
 │                      ├─ Expiry reminder  │
 │                      ├─ Expired ────────►│ (inactive)
 │                      │                   │
 ├─ Pay ───────────────────────────────────►│ (active)
 │                                          │
 │                                          ├─ 24h reminder
 │                                          ├─ Expiry reminder
 │                                          ├─ Expired
 │                                          │
 └─ Pay again ─────────────────────────────►│ (extend)
```

**Implementation**: Background task in `src/main.py::subscription_reminder_loop()`

## Database Schema Deep Dive

### User Table
```sql
users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    balance FLOAT DEFAULT 0.0,
    user_uuid VARCHAR(36) UNIQUE,  -- Static UUID for all servers
    trial_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
```

**Key Points**:
- `user_uuid` is generated once and never changes
- Used for ALL keys across ALL servers
- Enables seamless multi-server support

### Subscription Table
```sql
subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    expiry_date TIMESTAMP NOT NULL,
    plan_type VARCHAR(50),  -- "trial", "paid_m1", "paid_m3", "paid_m12"
    notified_24h BOOLEAN DEFAULT FALSE,
    notified_0h BOOLEAN DEFAULT FALSE,
    expired_handled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
```

**Key Points**:
- One active subscription per user (enforced by business logic)
- Notification flags prevent duplicate reminders
- `expired_handled` prevents re-processing expired subscriptions

### Key Table
```sql
keys (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER REFERENCES subscriptions(id),
    server_id INTEGER REFERENCES servers(id),
    key_uuid VARCHAR(36) NOT NULL,  -- Matches user.user_uuid
    email VARCHAR(255) NOT NULL,    -- Unique identifier on 3X-UI panel
    synced_to_panel BOOLEAN DEFAULT FALSE,
    last_sync_at TIMESTAMP,
    sync_error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(subscription_id, server_id)  -- One key per server per subscription
)
```

**Key Points**:
- Constraint ensures one key per server per subscription
- `synced_to_panel` tracks sync status
- `sync_error` for debugging panel issues

### Server Table
```sql
servers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,

    -- 3X-UI API
    api_url VARCHAR(512) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    inbound_id INTEGER DEFAULT 1,

    -- VLESS-Reality Config
    host VARCHAR(255) NOT NULL,
    port INTEGER DEFAULT 443,
    public_key VARCHAR(255) NOT NULL,
    short_ids TEXT NOT NULL,  -- Comma-separated
    domain VARCHAR(255) NOT NULL,  -- SNI

    -- Optional
    security VARCHAR(50) DEFAULT 'reality',
    network_type VARCHAR(50) DEFAULT 'xhttp',
    flow VARCHAR(50) DEFAULT 'xtls-rprx-vision',
    fingerprint VARCHAR(50) DEFAULT 'chrome',
    spider_x VARCHAR(255) DEFAULT '/',
    xhttp_host VARCHAR(255),
    xhttp_path VARCHAR(255),
    xhttp_mode VARCHAR(50),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
```

**Key Points**:
- All config needed to generate VLESS links
- Separate from API credentials (can have multiple panels)
- `is_active` allows soft-delete of servers

## Security Considerations

### 1. Environment Variables
- All secrets in `.env` (never in code)
- `.env` in `.gitignore`
- Different secrets for dev/staging/prod

### 2. Database
- PostgreSQL with secure password
- No direct SQL queries (SQLAlchemy ORM prevents injection)
- Connection pooling with limits

### 3. API Authentication
- 3X-UI: Cookie-based session with auto-refresh
- YooKassa: Basic Auth with shop credentials
- Webhook signature validation (if configured)

### 4. Input Validation
- Pydantic for config validation
- SQLAlchemy for database constraints
- aiogram filters for bot inputs

### 5. Error Handling
- Try-except blocks around external calls
- Retry logic with exponential backoff
- Graceful degradation (if 3X-UI down, queue for retry)

## Monitoring & Observability

### Logs
```python
# Structured logging
logger.info(f"Payment created: {payment_id} for user {telegram_id}")
logger.error(f"3X-UI sync failed: {error}", exc_info=True)
```

### Health Checks
- `/health` endpoint for monitoring
- Database connectivity check
- 3X-UI panel connectivity check (future)

### Metrics (Future)
- Active subscriptions count
- Payment success rate
- 3X-UI sync errors
- Average response time

## Testing Strategy

### Unit Tests (Future)
```python
# Test payment service
async def test_create_payment():
    service = YooKassaService()
    payment_id, url = await service.create_payment(12345, "m1", session)
    assert payment_id
    assert "yookassa.ru" in url

# Test 3X-UI client
async def test_add_client():
    client = ThreeXUIClient(...)
    await client.add_client(uuid, email, expiry_ms)
    clients = await client.list_clients()
    assert any(c["email"] == email for c in clients)
```

### Integration Tests (Future)
- End-to-end payment flow
- Trial activation flow
- Key generation and sync

### Load Tests (Future)
- 100 concurrent webhook requests
- 1000 users activating trial simultaneously

## Migration Strategy

### From Legacy to New System

**Phase 1: Prepare**
1. Deploy new system alongside legacy
2. Configure same 3X-UI panel
3. Run migration script

**Phase 2: Migrate**
1. Migrate users (preserves `telegram_id`, `username`)
2. Migrate subscriptions (preserves expiry dates)
3. Create keys linking to legacy UUID
4. Migrate payment history

**Phase 3: Cutover**
1. Stop legacy bot
2. Point bot token to new system
3. Monitor for 24 hours
4. Archive legacy database

**Rollback Plan**:
- Keep legacy bot ready
- Switch bot token back
- Legacy database untouched until verified

## Future Enhancements

### Short Term (Next 3 months)
- [ ] Admin panel (Django Admin or custom)
- [ ] User referral system
- [ ] Promo codes
- [ ] Multi-language support

### Medium Term (6 months)
- [ ] Traffic usage tracking
- [ ] Speed test integration
- [ ] Custom branding per user
- [ ] Reseller API

### Long Term (1 year)
- [ ] Auto-scaling server orchestration
- [ ] ML-based server selection
- [ ] iOS/Android native apps
- [ ] Blockchain payment support

## Conclusion

SWAGA VPN is architected for:
1. **Scalability**: From 1 VPS to 50k users without refactoring
2. **Maintainability**: Clear separation of concerns, modern patterns
3. **Reliability**: Async architecture, retry logic, graceful degradation
4. **Developer Experience**: Type hints, documentation, clear structure

The federated identity schema and service-oriented design ensure the system can grow with your business without technical debt.
