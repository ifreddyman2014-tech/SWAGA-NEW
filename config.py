"""
Конфигурация бота SWAGA VPN.
Загрузка переменных окружения и констант.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]

# ── 3X-UI Panel ───────────────────────────────────────────────────────────────
XUI_HOST: str = os.getenv("XUI_HOST", "")
XUI_PORT: str = os.getenv("XUI_PORT", "443")
XUI_WEB_PATH: str = os.getenv("XUI_WEB_PATH", "")
XUI_USER: str = os.getenv("XUI_USER", "")
XUI_PASS: str = os.getenv("XUI_PASS", "")
INBOUND_ID: int = int(os.getenv("INBOUND_ID", "1"))

# ── YooKassa (stub) ──────────────────────────────────────────────────────────
YOOKASSA_ID: str = os.getenv("YOOKASSA_ID", "")
YOOKASSA_KEY: str = os.getenv("YOOKASSA_KEY", "")

# ── VPN connection defaults ───────────────────────────────────────────────────
VPN_HOST: str = "yandex.ru"
VPN_PATH: str = "/adv"
VPN_PORT: int = 443

# ── Subscription plans ────────────────────────────────────────────────────────
PLANS: dict = {
    "trial": {"name": "Пробный", "days": 7, "price": 0},
    "1m":    {"name": "1 месяц", "days": 30, "price": 130},
    "3m":    {"name": "3 месяца", "days": 90, "price": 350},
    "1y":    {"name": "1 год", "days": 365, "price": 800},
}

# ── Paths ─────────────────────────────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "vpn_bot.db")
BACKUP_DIR: str = os.getenv("BACKUP_DIR", "backups")
