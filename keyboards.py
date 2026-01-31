"""
Клавиатуры Telegram-бота (Reply + Inline).
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from config import PLANS


# ── Reply-клавиатуры ──────────────────────────────────────────────────────────

def main_menu_kb() -> ReplyKeyboardMarkup:
    """Главное меню бота."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔐 Получить доступ"))
    kb.add(
        KeyboardButton("📖 Инструкция"),
        KeyboardButton("👤 Личный кабинет"),
    )
    return kb


# ── Inline-клавиатуры ─────────────────────────────────────────────────────────

def plans_kb(trial_used: bool) -> InlineKeyboardMarkup:
    """
    Выбор тарифного плана.
    Скрывает пробный период, если он уже использован.
    """
    kb = InlineKeyboardMarkup(row_width=1)
    if not trial_used:
        trial = PLANS["trial"]
        kb.add(
            InlineKeyboardButton(
                text=f"🎁 {trial['name']} — {trial['days']} дн. (бесплатно)",
                callback_data="plan_trial",
            )
        )
    for key in ("1m", "3m", "1y"):
        plan = PLANS[key]
        kb.add(
            InlineKeyboardButton(
                text=f"{plan['name']} — {plan['price']} ₽",
                callback_data=f"plan_{key}",
            )
        )
    return kb


def instruction_kb() -> InlineKeyboardMarkup:
    """Клавиатура на экране инструкции."""
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton(
            text="🔐 Получить доступ",
            callback_data="get_access",
        )
    )
    kb.add(
        InlineKeyboardButton(
            text="💬 Техподдержка",
            url="https://t.me/your_support_bot",
        )
    )
    return kb


def quick_connect_kb(vless_link: str) -> InlineKeyboardMarkup:
    """Кнопка быстрого подключения через V2RayTun."""
    kb = InlineKeyboardMarkup()
    v2ray_url = f"v2raytun://install-config?url={vless_link}"
    kb.add(
        InlineKeyboardButton(
            text="⚡ Быстрое подключение (V2RayTun)",
            url=v2ray_url,
        )
    )
    return kb


def cabinet_kb() -> InlineKeyboardMarkup:
    """Клавиатура личного кабинета (продление подписки)."""
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton(
            text="🔄 Продлить подписку",
            callback_data="get_access",
        )
    )
    return kb
