"""
User handlers for SWAGA VPN bot - Production version.

Marketing-focused flows with energetic, problem-solving tone.
"""

import logging
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database.models import Key, Server, Subscription, User
from ...services.payment import YooKassaService
from ...services.xui import ThreeXUIClient
from ..keyboards import Keyboards

logger = logging.getLogger(__name__)

router = Router(name="user_router")

# ============== Marketing Copywriting (Russian) ==============

WELCOME_TEXT = """🔥 <b>SwagaVPN: Твоя свобода в один клик</b>

YouTube в 4K, Instagram без лагов, ChatGPT без блокировок.

<b>Жми кнопку ниже и начни прямо сейчас!</b>"""

TRIAL_SUCCESS_TEXT = """🎁 <b>Твои {days} дня свободы активированы!</b>

✅ Доступ до: <b>{expiry_date}</b>

Жми кнопку внизу и подключайся за 10 секунд!

<i>Никаких настроек — всё работает из коробки.</i>"""

PAID_SUCCESS_TEXT = """💎 <b>Подписка активирована!</b>

✅ Доступ до: <b>{expiry_date}</b>
📦 Тариф: <b>{plan_name}</b>

Жми кнопку внизу для мгновенного подключения!

<i>YouTube 4K, Instagram, TikTok — всё летает.</i>"""

HOWTO_TEXT = """📲 <b>Как подключить SwagaVPN?</b>

<b>Шаг 1:</b> Скачай приложение для твоего устройства

📱 <b>Android:</b>
• V2RayTun (рекомендуем): <a href="https://play.google.com/store/apps/details?id=com.v2raytun.android">Google Play</a>
• v2rayNG: <a href="https://play.google.com/store/apps/details?id=com.v2ray.ang">Google Play</a>

🍎 <b>iPhone/iPad:</b>
• V2RayTun: <a href="https://apps.apple.com/ru/app/v2raytun/id6476628951">App Store</a>

💻 <b>Windows:</b>
• v2rayN: <a href="https://github.com/2dust/v2rayN/releases">Скачать</a>
• Hiddify: <a href="https://github.com/hiddify/hiddify-next/releases">Скачать</a>

<b>Шаг 2:</b> Вернись в бота

<b>Шаг 3:</b> Нажми "🚀 Получить доступ"

<b>Шаг 4:</b> Нажми "🚀 Быстрое подключение"

<b>Готово!</b> Наслаждайся свободным интернетом 🚀"""

SUPPORT_SPEED_TEXT = """📉 <b>Низкая скорость? Решаем за 2 минуты!</b>

<b>1. Попробуй другой сервер</b>
В приложении выбери другую локацию из списка.

<b>2. Смени протокол</b>
Попробуй переключиться между TCP и UDP в настройках.

<b>3. Перезагрузи приложение</b>
Полностью закрой и открой заново.

Не помогло? Жми "Связь с человеком" — разберёмся вместе! 👨‍💻"""

SUPPORT_PAYMENT_TEXT = """💸 <b>Вопросы по оплате</b>

<b>Безопасно ли?</b>
Да! Платежи через ЮKassa — официальный партнёр Сбербанка.

<b>Какие способы оплаты?</b>
• Банковские карты (Visa, MasterCard, МИР)
• СБП
• Электронные кошельки

<b>Когда активируется подписка?</b>
Мгновенно после оплаты! Автоматически.

<b>Можно вернуть деньги?</b>
Да, в течение 7 дней. Жми "Связь с человеком". 💬"""

SUPPORT_SETUP_TEXT = """📱 <b>Помощь с настройкой</b>

<b>Приложение не подключается?</b>
1. Убедись, что у тебя активная подписка (меню "Получить доступ")
2. Попробуй удалить и заново добавить ключ
3. Перезагрузи смартфон

<b>Ключ не копируется?</b>
Долго нажми на текст ключа — появится меню "Копировать".

<b>V2RayTun показывает ошибку?</b>
Переустанови приложение из магазина приложений.

Всё ещё не работает? Жми "Связь с человеком" — поможем! 🛠"""

ACCESS_ACTIVE_SUB_TEXT = """✅ <b>Твоя подписка активна!</b>

📅 Активна до: <b>{expiry_date}</b>
⏱ Осталось: <b>{days_left} дн.</b>

Продли сейчас — получи скидку на следующий период! 💰"""

ACCESS_NO_SUB_TEXT = """🚀 <b>Получи доступ к SwagaVPN</b>

Выбери тариф или попробуй бесплатно {trial_days} дня!

<b>Почему SwagaVPN?</b>
• YouTube 4K без буферизации
• Instagram, TikTok, ChatGPT работают
• Никаких логов и слежки
• Быстрое подключение за 10 секунд"""

PROMO_ENTER_TEXT = """🎟 <b>Введи промокод</b>

Отправь мне промокод следующим сообщением.

<i>Пример: SWAGA2024</i>"""


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
        .where(Subscription.expiry_date > datetime.utcnow())
        .order_by(Subscription.expiry_date.desc())
    )
    return result.scalar_one_or_none()


def format_date(dt: datetime) -> str:
    """Format datetime as DD.MM.YYYY."""
    return dt.strftime("%d.%m.%Y")


def build_vless_link(uuid: str, server: Server) -> str:
    """Build VLESS deep link for a server."""
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

    if server.xhttp_host:
        params["host"] = server.xhttp_host
    if server.xhttp_path:
        params["path"] = server.xhttp_path
    if server.xhttp_mode:
        params["mode"] = server.xhttp_mode

    query = "&".join([f"{k}={urllib.parse.quote(str(v), safe='/')}" for k, v in params.items() if v])
    remark = f"SWAGA - {server.name}"
    tag = urllib.parse.quote(remark, safe="")

    return f"vless://{uuid}@{server.host}:{server.port}?{query}#{tag}"


def build_v2raytun_deeplink(vless_url: str) -> str:
    """Build v2raytun:// deep link for one-click setup."""
    encoded_url = urllib.parse.quote(vless_url, safe="")
    return f"v2raytun://install-config?url={encoded_url}&name=SWAGA"


async def generate_keys_for_subscription(
    user: User,
    subscription: Subscription,
    expiry: datetime,
    session: AsyncSession,
) -> list[str]:
    """
    Generate and sync keys for all active servers.

    Returns list of VLESS URLs.
    """
    result = await session.execute(
        select(Server).where(Server.is_active == True)
    )
    servers = result.scalars().all()

    if not servers:
        raise RuntimeError("No active servers found")

    expiry_ms = int(expiry.timestamp() * 1000)
    vless_links = []

    for server in servers:
        # Check if key exists
        result = await session.execute(
            select(Key)
            .where(Key.subscription_id == subscription.id)
            .where(Key.server_id == server.id)
        )
        key = result.scalar_one_or_none()

        email = f"user-{user.telegram_id}"

        if not key:
            key = Key(
                subscription_id=subscription.id,
                server_id=server.id,
                key_uuid=user.user_uuid,
                email=email,
                synced_to_panel=False,
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
            key.sync_error = None
            await session.commit()

            logger.info(f"Key synced to server {server.name} for user {user.telegram_id}")

        except Exception as e:
            logger.error(f"Failed to sync key to server {server.name}: {e}")
            key.synced_to_panel = False
            key.sync_error = str(e)[:500]
            await session.commit()
            continue

        # Generate VLESS link
        vless_links.append(build_vless_link(user.user_uuid, server))

    return vless_links


# ============== Command Handlers ==============

@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    """Handle /start command."""
    await get_or_create_user(message.from_user.id, message.from_user.username, session)

    await message.answer(
        WELCOME_TEXT,
        reply_markup=Keyboards.main_menu(),
    )


@router.message(Command("reset_me"))
async def cmd_reset_me(message: Message, session: AsyncSession):
    """
    DEBUG: Reset user's trial and subscription.

    Only for development/testing.
    """
    user = await get_or_create_user(message.from_user.id, message.from_user.username, session)

    # Reset trial_used
    user.trial_used = False

    # Deactivate all subscriptions
    await session.execute(
        update(Subscription)
        .where(Subscription.user_id == user.id)
        .values(is_active=False)
    )

    await session.commit()

    await message.answer(
        "✅ <b>Сброс выполнен!</b>\n\n"
        "• Триал сброшен\n"
        "• Подписки деактивированы\n\n"
        "Теперь ты можешь заново активировать пробный период.",
        reply_markup=Keyboards.main_menu(),
    )
    logger.info(f"User {user.telegram_id} reset via /reset_me")


# ============== Callback Query Handlers ==============

@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery):
    """Handle home menu navigation."""
    await callback.answer()

    try:
        await callback.message.edit_text(
            WELCOME_TEXT,
            reply_markup=Keyboards.main_menu(),
        )
    except Exception:
        await callback.message.answer(
            WELCOME_TEXT,
            reply_markup=Keyboards.main_menu(),
        )


@router.callback_query(F.data == "menu:access")
async def menu_access(callback: CallbackQuery, session: AsyncSession):
    """Handle access menu (Get Access)."""
    await callback.answer()

    user = await get_or_create_user(callback.from_user.id, callback.from_user.username, session)
    subscription = await get_active_subscription(user.id, session)

    if subscription:
        # Has active subscription
        expiry_date = format_date(subscription.expiry_date)
        days_left = max((subscription.expiry_date - datetime.utcnow()).days, 0)

        text = ACCESS_ACTIVE_SUB_TEXT.format(
            expiry_date=expiry_date,
            days_left=days_left,
        )
        markup = Keyboards.access_menu_active_sub()
    else:
        # No active subscription
        text = ACCESS_NO_SUB_TEXT.format(trial_days=settings.trial_days)
        markup = Keyboards.access_menu_no_sub()

    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except Exception:
        await callback.message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "menu:howto")
async def menu_howto(callback: CallbackQuery):
    """Handle how-to menu."""
    await callback.answer()

    try:
        await callback.message.edit_text(
            HOWTO_TEXT,
            reply_markup=Keyboards.howto_menu(),
            disable_web_page_preview=True,
        )
    except Exception:
        await callback.message.answer(
            HOWTO_TEXT,
            reply_markup=Keyboards.howto_menu(),
            disable_web_page_preview=True,
        )


@router.callback_query(F.data == "menu:support")
async def menu_support(callback: CallbackQuery):
    """Handle support menu."""
    await callback.answer()

    try:
        await callback.message.edit_text(
            "🆘 <b>Техподдержка</b>\n\nВыбери, с чем нужна помощь:",
            reply_markup=Keyboards.support_menu(),
        )
    except Exception:
        await callback.message.answer(
            "🆘 <b>Техподдержка</b>\n\nВыбери, с чем нужна помощь:",
            reply_markup=Keyboards.support_menu(),
        )


@router.callback_query(F.data == "support:speed")
async def support_speed(callback: CallbackQuery):
    """Handle speed support."""
    await callback.answer()
    await callback.message.answer(
        SUPPORT_SPEED_TEXT,
        reply_markup=Keyboards.support_menu(),
    )


@router.callback_query(F.data == "support:payment")
async def support_payment(callback: CallbackQuery):
    """Handle payment support."""
    await callback.answer()
    await callback.message.answer(
        SUPPORT_PAYMENT_TEXT,
        reply_markup=Keyboards.support_menu(),
    )


@router.callback_query(F.data == "support:setup")
async def support_setup(callback: CallbackQuery):
    """Handle setup support."""
    await callback.answer()
    await callback.message.answer(
        SUPPORT_SETUP_TEXT,
        reply_markup=Keyboards.support_menu(),
    )


@router.callback_query(F.data == "promo:enter")
async def promo_enter(callback: CallbackQuery):
    """Handle promo code entry."""
    await callback.answer()
    await callback.message.answer(
        PROMO_ENTER_TEXT,
        reply_markup=Keyboards.back_home(),
    )
    # TODO: Implement promo code state handler


@router.callback_query(F.data == "trial:get")
async def trial_get(callback: CallbackQuery, session: AsyncSession):
    """Handle trial activation."""
    await callback.answer()

    user = await get_or_create_user(callback.from_user.id, callback.from_user.username, session)

    # Check if trial already used
    if user.trial_used:
        await callback.message.answer(
            "⚠️ <b>Пробный период уже использован</b>\n\n"
            "Но ты можешь купить подписку со скидкой! Выбери тариф:",
            reply_markup=Keyboards.access_menu_no_sub(),
        )
        return

    # Create subscription
    expiry_date = datetime.utcnow() + timedelta(days=settings.trial_days)

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

    # Generate keys
    try:
        vless_links = await generate_keys_for_subscription(user, subscription, expiry_date, session)

        if not vless_links:
            raise RuntimeError("No VLESS links generated")

        # Build deeplink
        deeplink = build_v2raytun_deeplink(vless_links[0])

        # Send success message
        await callback.message.answer(
            TRIAL_SUCCESS_TEXT.format(
                days=settings.trial_days,
                expiry_date=format_date(expiry_date),
            ),
            reply_markup=Keyboards.success_kb(deeplink),
        )

        logger.info(f"Trial activated for user {user.telegram_id}")

    except Exception as e:
        logger.error(f"Trial activation failed for user {user.telegram_id}: {e}")
        await callback.message.answer(
            "❌ <b>Ошибка активации</b>\n\n"
            "Что-то пошло не так. Попробуй позже или свяжись с поддержкой.",
            reply_markup=Keyboards.support_menu(),
        )


@router.callback_query(F.data.startswith("buy:"))
async def buy_plan(callback: CallbackQuery, session: AsyncSession):
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
            f"💳 <b>Оплата — {plan_name}</b>\n\n"
            f"Переходи по ссылке для оплаты:\n{confirmation_url}\n\n"
            f"После оплаты доступ активируется автоматически! ⚡",
        )

    except Exception as e:
        logger.error(f"Payment creation failed for user {user.telegram_id}: {e}")
        await callback.message.answer(
            "❌ <b>Ошибка создания платежа</b>\n\n"
            "Попробуй позже или свяжись с поддержкой.",
            reply_markup=Keyboards.support_menu(),
        )


@router.callback_query(F.data == "access:show_keys")
async def access_show_keys(callback: CallbackQuery, session: AsyncSession):
    """Show user's active keys."""
    await callback.answer()

    user = await get_or_create_user(callback.from_user.id, callback.from_user.username, session)
    subscription = await get_active_subscription(user.id, session)

    if not subscription:
        await callback.message.answer(
            "⚠️ <b>Нет активной подписки</b>\n\n"
            "Активируй триал или купи подписку!",
            reply_markup=Keyboards.access_menu_no_sub(),
        )
        return

    # Get keys
    result = await session.execute(
        select(Key, Server)
        .join(Server, Key.server_id == Server.id)
        .where(Key.subscription_id == subscription.id)
        .where(Server.is_active == True)
    )
    keys_servers = result.all()

    if not keys_servers:
        await callback.message.answer(
            "❌ <b>Ключи не найдены</b>\n\n"
            "Обратись в поддержку.",
            reply_markup=Keyboards.support_menu(),
        )
        return

    # Build VLESS links
    vless_links = []
    for key, server in keys_servers:
        vless_links.append(build_vless_link(key.key_uuid, server))

    # Build deeplink
    deeplink = build_v2raytun_deeplink(vless_links[0])

    # Format message
    expiry_str = format_date(subscription.expiry_date)
    days_left = max((subscription.expiry_date - datetime.utcnow()).days, 0)

    links_text = "\n\n".join([f"<code>{link}</code>" for link in vless_links])

    text = (
        f"🔑 <b>Твои ключи доступа</b>\n\n"
        f"📅 Активно до: <b>{expiry_str}</b>\n"
        f"⏱ Осталось: <b>{days_left} дн.</b>\n\n"
        f"{links_text}\n\n"
        f"<i>Нажми кнопку ниже для быстрого подключения</i>"
    )

    await callback.message.answer(
        text,
        reply_markup=Keyboards.success_kb(deeplink),
    )
