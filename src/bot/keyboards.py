"""Inline keyboards for SWAGA VPN bot."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..config import settings


class Keyboards:
    """Inline keyboard factory for the bot."""

    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Main menu keyboard."""
        builder = InlineKeyboardBuilder()
        builder.button(text="📖 Инструкция", callback_data="menu:howto")
        builder.button(text="🔑 Ключ доступа", callback_data="menu:keys")
        builder.button(text="📜 Правила", callback_data="menu:rules")
        builder.button(text="💬 Поддержка", url=f"https://t.me/{settings.support_bot_username}")
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def keys_menu() -> InlineKeyboardMarkup:
        """Keys and subscription menu."""
        builder = InlineKeyboardBuilder()
        builder.button(text=f"📅 1 месяц — {settings.price_m1} ₽", callback_data="buy:m1")
        builder.button(text=f"📅 3 месяца — {settings.price_m3} ₽", callback_data="buy:m3")
        builder.adjust(2)
        builder.button(text=f"📅 12 месяцев — {settings.price_m12} ₽", callback_data="buy:m12")
        builder.adjust(2, 1)
        builder.button(text="🎁 7 дней бесплатно", callback_data="trial:get")
        builder.button(text="🧾 Текущий доступ", callback_data="access:current")
        builder.button(text="📜 Правила", callback_data="menu:rules")
        builder.button(text="🏠 На главную", callback_data="menu:home")
        builder.button(text="💬 Поддержка", url=f"https://t.me/{settings.support_bot_username}")
        builder.adjust(2, 1, 1, 2, 2)
        return builder.as_markup()

    @staticmethod
    def pay_menu() -> InlineKeyboardMarkup:
        """Payment options menu."""
        buttons = [
            [InlineKeyboardButton(text=f"💳 1 месяц — {settings.price_m1} ₽", callback_data="buy:m1")],
            [InlineKeyboardButton(text=f"💳 3 месяца — {settings.price_m3} ₽", callback_data="buy:m3")],
            [InlineKeyboardButton(text=f"💳 12 месяцев — {settings.price_m12} ₽", callback_data="buy:m12")],
            [InlineKeyboardButton(text="🏠 На главную", callback_data="menu:home")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def back_home_support() -> InlineKeyboardMarkup:
        """Back, home, and support buttons."""
        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Назад", callback_data="menu:keys")
        builder.button(text="🏠 На главную", callback_data="menu:home")
        builder.button(text="💬 Поддержка", url=f"https://t.me/{settings.support_bot_username}")
        builder.adjust(2, 1)
        return builder.as_markup()

    @staticmethod
    def howto_menu() -> InlineKeyboardMarkup:
        """How-to menu with navigation."""
        builder = InlineKeyboardBuilder()
        builder.button(text="🔑 Ключ доступа", callback_data="menu:keys")
        builder.button(text="📜 Правила", callback_data="menu:rules")
        builder.button(text="🏠 На главную", callback_data="menu:home")
        builder.button(text="💬 Поддержка", url=f"https://t.me/{settings.support_bot_username}")
        builder.adjust(1, 2)
        return builder.as_markup()

    @staticmethod
    def subscription_menu() -> InlineKeyboardMarkup:
        """Subscription info menu."""
        builder = InlineKeyboardBuilder()
        builder.button(text="📝 Скопировать ключ", callback_data="key:copy")
        builder.button(text="💳 Оплата", callback_data="menu:pay")
        builder.button(text="🏠 На главную", callback_data="menu:home")
        builder.button(text="💬 Поддержка", url=f"https://t.me/{settings.support_bot_username}")
        builder.adjust(1, 2, 1)
        return builder.as_markup()
