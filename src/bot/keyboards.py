"""Inline keyboards for SWAGA VPN bot - Production UX."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..config import settings


class Keyboards:
    """Inline keyboard factory for the bot."""

    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """
        Main menu keyboard (3 buttons, 2 rows).

        Row 1: [🚀 Получить доступ]
        Row 2: [📲 Как подключить?] [🆘 Техподдержка]
        """
        builder = InlineKeyboardBuilder()
        builder.button(text="🚀 Получить доступ", callback_data="menu:access")
        builder.button(text="📲 Как подключить?", callback_data="menu:howto")
        builder.button(text="🆘 Техподдержка", callback_data="menu:support")
        builder.adjust(1, 2)  # Row 1: 1 button, Row 2: 2 buttons
        return builder.as_markup()

    @staticmethod
    def access_menu_no_sub() -> InlineKeyboardMarkup:
        """
        Access menu for users without active subscription.

        Shows pricing plans + trial + promo code.
        """
        builder = InlineKeyboardBuilder()
        builder.button(text=f"💳 1 месяц — {settings.price_m1}₽", callback_data="buy:m1")
        builder.button(text=f"💳 3 месяца — {settings.price_m3}₽", callback_data="buy:m3")
        builder.adjust(2)
        builder.button(text=f"💳 12 месяцев — {settings.price_m12}₽", callback_data="buy:m12")
        builder.button(text="🎁 Попробовать бесплатно", callback_data="trial:get")
        builder.button(text="🎟 Ввести промокод", callback_data="promo:enter")
        builder.button(text="⬅️ Главное меню", callback_data="menu:home")
        builder.adjust(2, 1, 1, 1, 1)
        return builder.as_markup()

    @staticmethod
    def access_menu_active_sub() -> InlineKeyboardMarkup:
        """Access menu for users with active subscription."""
        builder = InlineKeyboardBuilder()
        builder.button(text=f"💳 Продлить на месяц — {settings.price_m1}₽", callback_data="buy:m1")
        builder.button(text=f"💳 Продлить на 3 мес. — {settings.price_m3}₽", callback_data="buy:m3")
        builder.button(text=f"💳 Продлить на год — {settings.price_m12}₽", callback_data="buy:m12")
        builder.button(text="🔑 Показать ключи", callback_data="access:show_keys")
        builder.button(text="⬅️ Главное меню", callback_data="menu:home")
        builder.adjust(2, 1, 1, 1)
        return builder.as_markup()

    @staticmethod
    def success_kb(deeplink_url: str) -> InlineKeyboardMarkup:
        """
        Success keyboard with v2raytun deep link.

        Args:
            deeplink_url: v2raytun://install-config?url=...
        """
        buttons = [
            [InlineKeyboardButton(text="🚀 Быстрое подключение", url=deeplink_url)],
            [InlineKeyboardButton(text="📲 Как подключить?", callback_data="menu:howto")],
            [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu:home")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def support_menu() -> InlineKeyboardMarkup:
        """Support menu with common issues + human support."""
        builder = InlineKeyboardBuilder()
        builder.button(text="📉 Низкая скорость", callback_data="support:speed")
        builder.button(text="💸 Оплата", callback_data="support:payment")
        builder.button(text="📱 Настройка", callback_data="support:setup")
        builder.button(text="👨‍💻 Связь с человеком", url=f"https://t.me/{settings.support_bot_username}")
        builder.button(text="⬅️ Главное меню", callback_data="menu:home")
        builder.adjust(2, 1, 1, 1)
        return builder.as_markup()

    @staticmethod
    def howto_menu() -> InlineKeyboardMarkup:
        """How-to menu with back button."""
        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Главное меню", callback_data="menu:home")
        return builder.as_markup()

    @staticmethod
    def back_home() -> InlineKeyboardMarkup:
        """Simple back to home button."""
        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Главное меню", callback_data="menu:home")
        return builder.as_markup()
