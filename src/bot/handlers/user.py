"""
User handlers for SWAGA VPN bot.

Handles all user interactions including:
- Main menu navigation
- Trial activation
- Subscription management
- Payment processing
"""

import logging
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database.models import Key, Server, Subscription, User
from ...services.payment import YooKassaService
from ...services.xui import ThreeXUIClient
from ..keyboards import Keyboards

logger = logging.getLogger(__name__)

router = Router(name="user_router")

# Text constants
WELCOME_TEXT = """👋 Привет, {name}!
Добро пожаловать в <b>SWAGA VPN</b>

🔐 Безопасный и быстрый VPN
🌍 Несколько серверов • 🚀 Высокая скорость • ❌ Без логов

Выберите пункт меню:"""

HOWTO_TEXT = """📚 <b>Инструкции по использованию</b>

1) 📱 Установите приложение для вашего устройства:
   • 🤖 Android: <a href="https://play.google.com/store/apps/details?id=com.v2raytun.android">V2RayTun</a>
   • 🍎 iPhone: <a href="https://apps.apple.com/ru/app/v2raytun/id6476628951">V2RayTun</a>

2) 🔑 Получите ключ доступа в разделе «Ключ доступа».

3) ➕ Откройте приложение V2RayTun и нажмите на плюсик сверху справа.

4) 🧾 Выберите 'Добавить/импорт из буфера обмена' для добавления ключа.

5) ⏻ Нажмите на кнопку подключения.

💬 Если есть вопросы — пишите в <a href="https://t.me/{support}">поддержку</a>.
👇 Для быстрого перехода используйте кнопки под сообщением."""

RULES_TEXT = """📜 <b>Правила пользования сервисом SWAGA VPN</b>

1. Пользователь обязуется использовать сервис исключительно в законных целях и не нарушать законодательство Российской Федерации.

2. Запрещается использование сервиса для:
   • распространения экстремистских материалов,
   • участия в противоправной деятельности,
   • нарушения авторских прав и интеллектуальной собственности,
   • рассылки спама, мошеннических действий, хакерских атак.

3. Ответственность за действия при использовании сервиса несёт исключительно пользователь. Администрация сервиса не несёт ответственности за контент, передаваемый через VPN.

4. Используя сервис и активируя доступ, пользователь подтверждает, что ознакомился с правилами и обязуется соблюдать законодательство РФ и данные условия."""


# ============== Helper Functions ==============

async def get_or_create_user(telegram_id: int, username: Optional[str], session: AsyncSession) -> User:
    """Get existing user or create new one."""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"Created new user: {telegram_id}")

    return user


async def get_active_subscription(user_id: int, session: AsyncSession) -> Optional[Subscription]:
    """Get user's active subscription if exists and not expired."""
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .where(Subscription.is_active == True)
        .order_by(Subscription.expiry_date.desc())
    )
    subscription = result.scalar_one_or_none()

    if subscription and subscription.expiry_date > datetime.utcnow():
        return subscription

    return None


def build_vless_link(uuid: str, server: Server) -> str:
    """
    Build VLESS deep link for a server.

    Args:
        uuid: User's UUID
        server: Server configuration

    Returns:
        VLESS URL
    """
    params = {
        "encryption": "none",
        "security": server.security,
        "type": server.network_type,
        "pbk": server.public_key,
        "fp": server.fingerprint,
        "sni": server.domain,
        "sid": server.get_first_short_id(),
        "spx": server.spider_x,
        "flow": server.flow,
    }

    # Add xhttp params if available
    if server.xhttp_host:
        params["host"] = server.xhttp_host
    if server.xhttp_path:
        params["path"] = server.xhttp_path
    if server.xhttp_mode:
        params["mode"] = server.xhttp_mode

    # Build query string
    query = "&".join([f"{k}={urllib.parse.quote(str(v), safe='/')}" for k, v in params.items() if v])

    # Build remark (tag)
    remark = f"SWAGA - {server.name}"
    tag = urllib.parse.quote(remark, safe="")

    return f"vless://{uuid}@{server.host}:{server.port}?{query}#{tag}"


def build_v2raytun_deeplink(vless_url: str) -> str:
    """
    Build v2raytun:// deep link for one-click setup.

    Args:
        vless_url: VLESS URL

    Returns:
        v2raytun deeplink
    """
    encoded_url = urllib.parse.quote(vless_url, safe="")
    return f"v2raytun://install-config?url={encoded_url}&name=SWAGA"


async def get_user_keys_text(user: User, subscription: Subscription, session: AsyncSession) -> str:
    """
    Generate text with user's VLESS keys for all servers.

    Args:
        user: User object
        subscription: Active subscription
        session: Database session

    Returns:
        Formatted text with keys
    """
    # Get all keys for this subscription
    result = await session.execute(
        select(Key, Server)
        .join(Server, Key.server_id == Server.id)
        .where(Key.subscription_id == subscription.id)
        .where(Server.is_active == True)
    )
    keys_servers = result.all()

    if not keys_servers:
        return "❌ Ключи не найдены. Обратитесь в поддержку."

    links = []
    for key, server in keys_servers:
        vless_link = build_vless_link(key.key_uuid, server)
        links.append(f"<b>{server.name}</b>:\n<code>{vless_link}</code>")

    expiry_str = subscription.expiry_date.strftime("%d.%m.%Y %H:%M") if subscription.expiry_date else "—"
    days_left = max((subscription.expiry_date - datetime.utcnow()).days, 0) if subscription.expiry_date else 0

    # Build deep link for first server (for v2raytun)
    first_key, first_server = keys_servers[0]
    first_vless = build_vless_link(first_key.key_uuid, first_server)
    deeplink = build_v2raytun_deeplink(first_vless)

    text = (
        f"🔑 <b>Ваши ключи доступа</b>\n\n"
        f"📅 Действует до: <b>{expiry_str}</b>\n"
        f"⏳ Осталось: <b>{days_left} дн.</b>\n\n"
        f"<b>🔗 Ключи для подключения:</b>\n\n"
        + "\n\n".join(links) +
        f"\n\n💡 <b>Быстрое подключение:</b>\n"
        f"<a href=\"{deeplink}\">Нажмите здесь</a> для автоматической настройки в V2RayTun"
    )

    return text


# ============== Command Handlers ==============

@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    """Handle /start command."""
    await get_or_create_user(message.from_user.id, message.from_user.username, session)

    await message.answer(
        WELCOME_TEXT.format(name=message.from_user.full_name),
        reply_markup=Keyboards.main_menu(),
    )


@router.message(Command("buy"))
async def cmd_buy(message: Message, session: AsyncSession):
    """Handle /buy command."""
    await get_or_create_user(message.from_user.id, message.from_user.username, session)

    text = (
        f"🔑 <b>Ключ доступа</b>\n\n"
        f"Тарифы:\n"
        f"• 1 мес — <b>{settings.price_m1}₽</b>\n"
        f"• 3 мес — <b>{settings.price_m3}₽</b>\n"
        f"• 12 мес — <b>{settings.price_m12}₽</b>\n\n"
        f"Либо активируйте 7-дневный пробный период."
    )

    await message.answer(text, reply_markup=Keyboards.keys_menu())


@router.message(Command("support"))
async def cmd_support(message: Message):
    """Handle /support command."""
    await message.answer(
        f"💬 Обратитесь в поддержку: @{settings.support_bot_username}",
        reply_markup=Keyboards.back_home_support(),
    )


@router.message(Command("rules"))
async def cmd_rules(message: Message):
    """Handle /rules command."""
    await message.answer(
        RULES_TEXT,
        reply_markup=Keyboards.back_home_support(),
    )


# ============== Callback Query Handlers ==============

@router.callback_query(F.data.startswith("menu:"))
async def handle_menu(callback: CallbackQuery, session: AsyncSession):
    """Handle menu navigation."""
    await callback.answer()

    action = callback.data.split(":", 1)[1]

    if action == "home":
        text = WELCOME_TEXT.format(name=callback.from_user.full_name)
        markup = Keyboards.main_menu()

    elif action == "keys":
        text = (
            f"🔑 <b>Ключ доступа</b>\n\n"
            f"Выберите тариф ниже или активируйте 7-дневный пробный период.\n\n"
            f"Используя сервис, вы соглашаетесь с <b>Правилами</b> (кнопка ниже)."
        )
        markup = Keyboards.keys_menu()

    elif action == "howto":
        text = HOWTO_TEXT.format(support=settings.support_bot_username)
        markup = Keyboards.howto_menu()

    elif action == "rules":
        text = RULES_TEXT
        markup = Keyboards.back_home_support()

    elif action == "pay":
        text = "Выберите тариф для оплаты:"
        markup = Keyboards.pay_menu()

    else:
        return

    try:
        await callback.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
    except Exception:
        await callback.message.answer(text, reply_markup=markup, disable_web_page_preview=True)


@router.callback_query(F.data.startswith("buy:"))
async def handle_buy(callback: CallbackQuery, session: AsyncSession):
    """Handle payment initiation."""
    await callback.answer()

    plan = callback.data.split(":", 1)[1]

    user = await get_or_create_user(callback.from_user.id, callback.from_user.username, session)

    # Create payment
    payment_service = YooKassaService()

    try:
        payment_id, confirmation_url = await payment_service.create_payment(
            telegram_id=user.telegram_id,
            plan=plan,
            session=session,
        )

        plan_names = {"m1": "1 месяц", "m3": "3 месяца", "m12": "12 месяцев"}
        plan_name = plan_names.get(plan, plan)

        await callback.message.answer(
            f"💳 Перейдите к оплате тарифа <b>{plan_name}</b>:\n\n"
            f"{confirmation_url}\n\n"
            f"После успешной оплаты доступ будет активирован автоматически."
        )

    except Exception as e:
        logger.error(f"Payment creation failed for user {user.telegram_id}: {e}")
        await callback.message.answer(
            f"❌ Ошибка при создании платежа: {e}\n\n"
            f"Попробуйте позже или обратитесь в поддержку.",
            reply_markup=Keyboards.back_home_support(),
        )


@router.callback_query(F.data == "trial:get")
async def handle_trial(callback: CallbackQuery, session: AsyncSession):
    """Handle trial activation."""
    await callback.answer()

    user = await get_or_create_user(callback.from_user.id, callback.from_user.username, session)

    # Check if trial already used
    if user.trial_used:
        await callback.message.answer(
            "⚠️ Пробный период уже активирован ранее.",
            reply_markup=Keyboards.back_home_support(),
        )
        return

    # Calculate expiry
    expiry_date = datetime.utcnow() + timedelta(days=settings.trial_days)
    expiry_ms = int(expiry_date.timestamp() * 1000)

    # Create subscription
    subscription = Subscription(
        user_id=user.id,
        is_active=True,
        expiry_date=expiry_date,
        plan_type="trial",
    )
    session.add(subscription)
    user.trial_used = True
    await session.commit()
    await session.refresh(subscription)

    # Get all active servers
    result = await session.execute(
        select(Server).where(Server.is_active == True)
    )
    servers = result.scalars().all()

    if not servers:
        await callback.message.answer(
            "❌ Нет доступных серверов. Обратитесь в поддержку.",
            reply_markup=Keyboards.back_home_support(),
        )
        return

    # Create keys and sync to panels
    for server in servers:
        email = f"trial-{user.telegram_id}"

        # Create key in database
        key = Key(
            subscription_id=subscription.id,
            server_id=server.id,
            key_uuid=user.user_uuid,
            email=email,
        )
        session.add(key)
        await session.commit()
        await session.refresh(key)

        # Sync to 3X-UI panel
        try:
            xui_client = ThreeXUIClient(
                base_url=server.api_url,
                username=server.username,
                password=server.password,
                inbound_id=server.inbound_id,
                flow=server.flow,
            )

            async with xui_client.session():
                await xui_client.ensure_client(
                    uuid=user.user_uuid,
                    email=email,
                    expiry_ms=expiry_ms,
                )

            key.synced_to_panel = True
            key.last_sync_at = datetime.utcnow()
            await session.commit()

            logger.info(f"Trial key created on server {server.name} for user {user.telegram_id}")

        except Exception as e:
            logger.error(f"Failed to sync trial key to server {server.name}: {e}")
            key.sync_error = str(e)[:500]
            await session.commit()

    # Send keys to user
    text = await get_user_keys_text(user, subscription, session)
    text = f"🎁 <b>Триал активирован!</b>\n\n{text}"

    try:
        await callback.message.edit_text(
            text,
            reply_markup=Keyboards.subscription_menu(),
            disable_web_page_preview=True,
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=Keyboards.subscription_menu(),
            disable_web_page_preview=True,
        )


@router.callback_query(F.data == "access:current")
async def handle_current_access(callback: CallbackQuery, session: AsyncSession):
    """Show current subscription details."""
    await callback.answer()

    user = await get_or_create_user(callback.from_user.id, callback.from_user.username, session)

    subscription = await get_active_subscription(user.id, session)

    if not subscription:
        await callback.message.answer(
            "ℹ️ Ключ ещё не активирован. В «Ключ доступа» выберите «7 дней бесплатно».",
            reply_markup=Keyboards.back_home_support(),
        )
        return

    text = await get_user_keys_text(user, subscription, session)

    try:
        await callback.message.edit_text(
            text,
            reply_markup=Keyboards.subscription_menu(),
            disable_web_page_preview=True,
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=Keyboards.subscription_menu(),
            disable_web_page_preview=True,
        )


@router.callback_query(F.data == "key:copy")
async def handle_key_copy(callback: CallbackQuery):
    """Handle key copy action."""
    await callback.answer("Ключ можно скопировать долгим нажатием в сообщении выше.")
