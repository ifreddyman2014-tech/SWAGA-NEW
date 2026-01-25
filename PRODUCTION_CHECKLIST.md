# 🚀 SWAGA VPN - Production Deployment Checklist

## ⚠️ CRITICAL: Manual Configuration Required

Before deploying to production, you **MUST** replace all placeholder values in configuration files.

---

## 📋 Step-by-Step Checklist

### 1. Configure Environment Variables (.env)

Open `.env` file and replace these **8 values**:

```bash
# ============================================================
# 1. DATABASE PASSWORD
# ============================================================
POSTGRES_PASSWORD=REPLACE_WITH_SECURE_PASSWORD
DATABASE_URL=postgresql+asyncpg://swaga_user:REPLACE_WITH_SECURE_PASSWORD@postgres:5432/swaga

# Generate secure password:
# openssl rand -base64 32

# ============================================================
# 2. TELEGRAM BOT TOKEN
# ============================================================
BOT_TOKEN=REPLACE_WITH_BOT_TOKEN

# Get from: https://t.me/BotFather
# Create new bot or use existing

# ============================================================
# 3. ADMIN CHAT ID
# ============================================================
ADMIN_CHAT_ID=REPLACE_WITH_ADMIN_CHAT_ID

# Get your Telegram ID from: https://t.me/userinfobot

# ============================================================
# 4. 3X-UI CREDENTIALS
# ============================================================
XUI_USERNAME=REPLACE_WITH_ADMIN_LOGIN
XUI_PASSWORD=REPLACE_WITH_ADMIN_PASS

# Use your 3X-UI panel admin credentials
# Panel URL is already set: http://150.241.77.138:2055/JXmOAqpCBtH14wRJ2t

# ============================================================
# 5. YOOKASSA CREDENTIALS
# ============================================================
YOOKASSA_SHOP_ID=REPLACE_WITH_SHOP_ID
YOOKASSA_SECRET=REPLACE_WITH_SECRET_KEY
YOOKASSA_WEBHOOK_SECRET=REPLACE_WITH_WEBHOOK_SECRET

# Get from: https://yookassa.ru/my/shop/settings
# Generate webhook secret: openssl rand -hex 32
```

---

### 2. Configure Server (seed.sql)

Open `seed.sql` and replace these **4 values** in the INSERT statement:

```sql
-- ============================================================
# 1. 3X-UI ADMIN USERNAME
-- ============================================================
username: 'REPLACE_WITH_ADMIN_LOGIN'

# Same as XUI_USERNAME in .env
# Example: 'admin'

-- ============================================================
# 2. 3X-UI ADMIN PASSWORD
-- ============================================================
password: 'REPLACE_WITH_ADMIN_PASS'

# Same as XUI_PASSWORD in .env
# Example: 'MySecurePassword123'

-- ============================================================
# 3. REALITY PUBLIC KEY
-- ============================================================
public_key: 'REPLACE_WITH_REALITY_PUB_KEY'

# Get from 3X-UI panel:
# Inbound Settings → Reality Settings → Public Key
# Example: 'tQHZFOZvXzXXXXXXXXXXXXXXXXXXXXX'

-- ============================================================
# 4. REALITY SHORT IDS
-- ============================================================
short_ids: 'REPLACE_WITH_SHORT_ID'

# Get from 3X-UI panel:
# Inbound Settings → Reality Settings → Short IDs
# Example: 'a1b2c3d4'
# Multiple IDs: 'a1b2c3d4,e5f6g7h8' (comma-separated)
```

---

## 🔍 How to Get Reality Parameters from 3X-UI Panel

### Access Your Panel

```bash
# Open in browser:
http://150.241.77.138:2055/JXmOAqpCBtH14wRJ2t

# Login with your admin credentials
```

### Get Public Key & Short IDs

1. Go to **Inbounds** (left sidebar)
2. Click **Settings** (⚙️) on your VLESS inbound
3. Find **Reality Settings** section:
   - **Public Key**: Copy the long base64 string
   - **Short IDs**: Copy the short hex string(s)
4. Paste into `seed.sql`

---

## ✅ Final Verification Checklist

Before running `docker compose up`:

### .env File (8 replacements)
- [ ] `POSTGRES_PASSWORD` - Generated secure password
- [ ] `DATABASE_URL` - Contains same password
- [ ] `BOT_TOKEN` - From @BotFather
- [ ] `ADMIN_CHAT_ID` - Your Telegram ID
- [ ] `XUI_USERNAME` - 3X-UI admin username
- [ ] `XUI_PASSWORD` - 3X-UI admin password
- [ ] `YOOKASSA_SHOP_ID` - From YooKassa dashboard
- [ ] `YOOKASSA_SECRET` - From YooKassa dashboard
- [ ] `YOOKASSA_WEBHOOK_SECRET` - Generated with openssl

### seed.sql File (4 replacements)
- [ ] `username` - Same as XUI_USERNAME
- [ ] `password` - Same as XUI_PASSWORD
- [ ] `public_key` - From 3X-UI Reality settings
- [ ] `short_ids` - From 3X-UI Reality settings

### Double-Check
- [ ] No "REPLACE_" strings remain in `.env`
- [ ] No "REPLACE_" strings remain in `seed.sql`
- [ ] XUI_BASE in `.env` matches: `http://150.241.77.138:2055/JXmOAqpCBtH14wRJ2t`
- [ ] WEBHOOK_BASE_URL in `.env` is: `https://swaga-vpn.ru`
- [ ] Server host in `seed.sql` is: `sub.swaga-vpn.ru`
- [ ] Server domain in `seed.sql` is: `swaga-vpn.ru`

---

## 🚀 Deployment Commands

After completing ALL replacements above:

```bash
# 1. Start services
docker compose up -d --build

# 2. Wait for PostgreSQL (15 seconds)
docker compose logs -f postgres
# Wait for: "database system is ready to accept connections"
# Press Ctrl+C

# 3. Seed database
docker compose exec -T postgres psql -U swaga_user -d swaga < seed.sql

# 4. Verify bot startup
docker compose logs -f bot

# Expected logs:
# ✅ Database initialized successfully
# ✅ 3X-UI authentication successful
# ✅ Bot commands set successfully
# ✅ Bot polling started
# ✅ SWAGA VPN Bot started successfully
```

---

## 🔐 Security Reminders

### Passwords
- Use **strong, unique** passwords (32+ characters)
- Never reuse passwords across services
- Store credentials in secure password manager

### Webhook Secret
- Generate with: `openssl rand -hex 32`
- Keep it secret (never commit to git)
- Configure in YooKassa dashboard

### Database
- Backup database regularly
- Use firewall to restrict PostgreSQL access
- Never expose port 5432 publicly

---

## 📞 Support

If you encounter issues during deployment:

1. **Check logs**: `docker compose logs -f bot`
2. **Verify configuration**: Re-read this checklist
3. **Test 3X-UI connection**: Login to panel manually
4. **Contact**: @swagasupport_bot (Telegram)

---

## 🎉 Post-Deployment

After successful deployment:

1. **Test bot**: Send `/start` to your bot in Telegram
2. **Test trial**: Activate 3-day trial
3. **Verify keys**: Check that VLESS links are generated
4. **Test payment**: Create test payment (YooKassa test mode)
5. **Configure webhook**: Add webhook URL to YooKassa dashboard
   - URL: `https://swaga-vpn.ru/webhook/yookassa`
   - Events: `payment.succeeded`, `payment.canceled`, `refund.succeeded`

---

## 📊 Summary

**Total manual replacements required**: **12**

- `.env`: 8 values (including 2 password instances)
- `seed.sql`: 4 values

**Estimated setup time**: 15-20 minutes

**Deployment time** (after config): ~30 seconds

---

**Status**: Ready for production deployment after completing this checklist! 🚀
