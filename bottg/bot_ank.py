import asyncio
import html
import re
import sqlite3
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = "9187444592:AAEwVWdvMPdQ3x1J9l0fZTfMTplmPxX1NHs"
ADMIN_ID = 8839415985

OWNER_USERNAME = "ceo_elysium"

SERVER_NAME = "Elysium"
SERVER_IP = "elysium.mc-join.me"
SERVER_VERSION = "26.1.2"

DATABASE_FILE = "elysium_shop.db"
SUBSCRIPTION_DAYS = 30
ROLLBACK_PRICE = 40
ROLLBACK_PRODUCT_NAME = "1 дополнительный откат"


# ============================================================
# ТАРИФЫ
# ============================================================

PLANS = {
    "plus": {
        "name": "ЭЛИЗИУМ+",
        "price": 149,
        "description": (
            "🎨 1 кастомный префикс в TAB\n"
            "🌈 Цветной чат\n"
            "✨ Все партиклы\n"
            "🥤 Собственный напиток\n"
            "♻️ 1 откат инвентаря в месяц\n"
            "🎙️ Приоритет в войс-чате"
        ),
    },

    "plusplus": {
        "name": "ЭЛИЗИУМ++",
        "price": 299,
        "description": (
            "Всё из ЭЛИЗИУМ+, плюс:\n\n"
            "🗿 1 личный тотем со своим скином\n"
            "👤 1 твинк\n"
            "♻️ 3 отката инвентаря в месяц\n"
            "🎭 Кастомная роль в Discord + Telegram\n"
            "🎙️ Повышенный приоритет в войс-чате"
        ),
    },

    "plusplusplus": {
        "name": "ЭЛИЗИУМ+++",
        "price": 499,
        "description": (
            "Всё из ЭЛИЗИУМ++, плюс:\n\n"
            "🗿 До 2 личных тотемов\n"
            "👤 До 2 твинков\n"
            "♻️ 5 откатов инвентаря в месяц\n"
            "🎭 Расширенная кастомная роль\n"
            "🎙️ Максимальный приоритет в войс-чате\n"
            "✨ Дополнительная кастомизация"
        ),
    },
}


# ============================================================
# БОТ И БАЗА ДАННЫХ
# ============================================================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher(storage=MemoryStorage())

db = sqlite3.connect(DATABASE_FILE)
db.row_factory = sqlite3.Row


def init_db():
    db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            nickname TEXT NOT NULL,
            product TEXT NOT NULL,
            price INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            reminder_sent INTEGER NOT NULL DEFAULT 0
        )
    """)

    db.commit()


# ============================================================
# СОСТОЯНИЯ
# ============================================================

class BuyState(StatesGroup):
    nickname = State()


class CustomState(StatesGroup):
    idea = State()


# ============================================================
# КЛАВИАТУРЫ
# ============================================================

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💜 Купить подписку",
                    callback_data="catalog"
                )
            ],
            [
                InlineKeyboardButton(
                    text="♻️ Купить откат — 40 ₽",
                    callback_data="buy_rollback"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👑 Кастомная привилегия",
                    callback_data="custom"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Мои покупки",
                    callback_data="history"
                )
            ],
            [
                InlineKeyboardButton(
                    text="♻️ Об откатах",
                    callback_data="rollback_info"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌐 Об Элизиуме",
                    callback_data="server"
                )
            ],
        ]
    )


def back_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Главное меню",
                    callback_data="home"
                )
            ]
        ]
    )


def admin_order_keyboard(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить оплату",
                    callback_data=f"paid_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отклонить заказ",
                    callback_data=f"reject_{order_id}"
                )
            ],
        ]
    )


# ============================================================
# ЗАКАЗЫ
# ============================================================

def create_order(user_id, username, nickname, product, price):
    cursor = db.execute("""
        INSERT INTO orders
        (user_id, username, nickname, product, price, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (
        user_id,
        username,
        nickname,
        product,
        price,
        datetime.now().isoformat(timespec="seconds"),
    ))

    db.commit()
    return cursor.lastrowid


def get_user_orders(user_id):
    return db.execute("""
        SELECT * FROM orders
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 10
    """, (user_id,)).fetchall()


def get_pending_orders():
    return db.execute("""
        SELECT * FROM orders
        WHERE status = 'pending'
        ORDER BY id DESC
    """).fetchall()


# ============================================================
# АКТИВАЦИЯ ПОДПИСКИ
# ============================================================

def activate_subscription(order):
    now = datetime.now()

    current = db.execute("""
        SELECT * FROM subscriptions
        WHERE user_id = ?
        ORDER BY expires_at DESC
        LIMIT 1
    """, (order["user_id"],)).fetchone()

    if current:
        current_expiry = datetime.fromisoformat(
            current["expires_at"]
        )

        start_date = max(now, current_expiry)

        new_expiry = start_date + timedelta(
            days=SUBSCRIPTION_DAYS
        )

        db.execute("""
            UPDATE subscriptions
            SET plan = ?, expires_at = ?, reminder_sent = 0
            WHERE id = ?
        """, (
            order["product"],
            new_expiry.isoformat(timespec="seconds"),
            current["id"],
        ))

    else:
        new_expiry = now + timedelta(days=SUBSCRIPTION_DAYS)

        db.execute("""
            INSERT INTO subscriptions
            (user_id, plan, expires_at, reminder_sent)
            VALUES (?, ?, ?, 0)
        """, (
            order["user_id"],
            order["product"],
            new_expiry.isoformat(timespec="seconds"),
        ))

    db.commit()
    return new_expiry


def process_order(order_id, new_status):
    db.execute("BEGIN IMMEDIATE")

    try:
        order = db.execute("""
            SELECT * FROM orders
            WHERE id = ?
        """, (order_id,)).fetchone()

        if not order or order["status"] != "pending":
            db.rollback()
            return None, None

        db.execute("""
            UPDATE orders
            SET status = ?
            WHERE id = ?
        """, (new_status, order_id))

        expiry = None

        if (
            new_status == "paid"
            and order["product"] in {
                plan["name"] for plan in PLANS.values()
            }
        ):
            expiry = activate_subscription(order)

        db.commit()
        return order, expiry

    except Exception:
        db.rollback()
        raise


# ============================================================
# УВЕДОМЛЕНИЯ ВЛАДЕЛЬЦУ
# ============================================================

async def notify_admin_about_order(
    message,
    order_id,
    nickname,
    product,
    price
):
    username = message.from_user.username or "нет"

    admin_text = (
        f"🛒 <b>НОВЫЙ ЗАКАЗ №{order_id}</b>\n\n"
        f"Игрок: @{html.escape(username)}\n"
        f"Telegram ID: <code>{message.from_user.id}</code>\n"
        f"Никнейм: <code>{html.escape(nickname)}</code>\n"
        f"Товар: {html.escape(product)}\n"
        f"Стоимость: {price} ₽\n\n"
        "Статус: ⏳ ожидает оплаты.\n"
        "Проверь поступление денег перед подтверждением."
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=admin_order_keyboard(order_id),
        )

    except Exception as error:
        print(
            f"Не удалось отправить заказ администратору: {error}"
        )


# ============================================================
# START
# ============================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "💜 <b>ДОБРО ПОЖАЛОВАТЬ В МАГАЗИН ЭЛИЗИУМА!</b>\n\n"
        "Здесь ты можешь приобрести подписку, купить "
        "дополнительный откат инвентаря или предложить "
        "собственную привилегию.\n\n"
        "Выбирай интересующий раздел 👇",
        reply_markup=main_menu(),
    )


@dp.callback_query(F.data == "home")
async def go_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text(
        "💜 <b>МАГАЗИН ЭЛИЗИУМА</b>\n\n"
        "Выбирай интересующий раздел:",
        reply_markup=main_menu(),
    )

    await callback.answer()


# ============================================================
# КАТАЛОГ ПОДПИСОК
# ============================================================

@dp.callback_query(F.data == "catalog")
async def catalog(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 ЭЛИЗИУМ+ — 149 ₽/мес",
                    callback_data="plan_plus"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔵 ЭЛИЗИУМ++ — 299 ₽/мес ⭐",
                    callback_data="plan_plusplus"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🟣 ЭЛИЗИУМ+++ — 499 ₽/мес",
                    callback_data="plan_plusplusplus"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="home"
                )
            ],
        ]
    )

    await callback.message.edit_text(
        "💜 <b>ПОДПИСКИ ЭЛИЗИУМА</b>\n\n"
        "Выбери подходящий тариф. "
        "Все подписки действуют 30 дней:",
        reply_markup=keyboard,
    )

    await callback.answer()


# ============================================================
# ОПИСАНИЕ ТАРИФОВ
# ============================================================

@dp.callback_query(F.data.startswith("plan_"))
async def show_plan(callback: CallbackQuery):
    key = callback.data.removeprefix("plan_")
    plan = PLANS.get(key)

    if not plan:
        await callback.answer(
            "Тариф не найден.",
            show_alert=True
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Купить подписку",
                    callback_data=f"buy_{key}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К тарифам",
                    callback_data="catalog"
                )
            ],
        ]
    )

    await callback.message.edit_text(
        f"<b>{plan['name']} — {plan['price']} ₽/мес</b>\n\n"
        f"{plan['description']}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"📅 Срок действия: {SUBSCRIPTION_DAYS} дней\n\n"
        "Покупая подписку, ты добровольно "
        "поддерживаешь развитие проекта.",
        reply_markup=keyboard,
    )

    await callback.answer()


# ============================================================
# НАЧАЛО ПОКУПКИ
# ============================================================

@dp.callback_query(F.data.startswith("buy_"))
async def begin_purchase(
    callback: CallbackQuery,
    state: FSMContext
):
    product_key = callback.data.removeprefix("buy_")

    if product_key == "rollback":
        await state.update_data(
            product=ROLLBACK_PRODUCT_NAME,
            price=ROLLBACK_PRICE,
        )

    elif product_key in PLANS:
        plan = PLANS[product_key]

        await state.update_data(
            product=plan["name"],
            price=plan["price"],
        )

    else:
        await callback.answer(
            "Товар не найден.",
            show_alert=True
        )
        return

    await state.set_state(BuyState.nickname)

    await callback.message.edit_text(
        "🛒 <b>ОФОРМЛЕНИЕ ЗАКАЗА</b>\n\n"
        "Введи свой игровой никнейм Minecraft:",
        reply_markup=back_menu(),
    )

    await callback.answer()


# ============================================================
# СОЗДАНИЕ ЗАКАЗА
# ============================================================

@dp.message(BuyState.nickname)
async def receive_nickname(
    message: Message,
    state: FSMContext
):
    nickname = (message.text or "").strip()

    if not re.fullmatch(r"[A-Za-z0-9_]{3,16}", nickname):
        await message.answer(
            "❌ Некорректный никнейм.\n"
            "Укажи от 3 до 16 символов: "
            "английские буквы, цифры или _."
        )
        return

    data = await state.get_data()

    product = data["product"]
    price = data["price"]

    order_id = create_order(
        user_id=message.from_user.id,
        username=message.from_user.username or "нет",
        nickname=nickname,
        product=product,
        price=price,
    )

    await state.clear()

    await message.answer(
        f"✅ <b>ЗАКАЗ №{order_id} СОЗДАН!</b>\n\n"
        f"Товар: {html.escape(product)}\n"
        f"Стоимость: {price} ₽\n"
        f"Никнейм: <code>{html.escape(nickname)}</code>\n\n"
        "Заявка отправлена владельцу. "
        "Для согласования оплаты напиши ему:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Написать владельцу",
                        url=f"https://t.me/{OWNER_USERNAME}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 Мои покупки",
                        callback_data="history"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏠 Главное меню",
                        callback_data="home"
                    )
                ],
            ]
        ),
    )

    await notify_admin_about_order(
        message,
        order_id,
        nickname,
        product,
        price,
    )


# ============================================================
# ИСТОРИЯ ПОКУПОК
# ============================================================

@dp.callback_query(F.data == "history")
async def history(callback: CallbackQuery):
    orders = get_user_orders(callback.from_user.id)

    lines = ["📋 <b>МОИ ПОКУПКИ</b>\n"]

    if not orders:
        lines.append("У тебя пока нет заказов.")

    else:
        status_names = {
            "pending": "⏳ Ожидает оплаты",
            "paid": "✅ Оплачено",
            "rejected": "❌ Отклонено",
        }

        for order in orders:
            lines.append(
                f"🛒 <b>Заказ №{order['id']}</b>\n"
                f"Товар: {html.escape(order['product'])}\n"
                f"Цена: {order['price']} ₽\n"
                f"Статус: {status_names.get(order['status'], order['status'])}\n"
                "━━━━━━━━━━━━━━"
            )

    subscription = db.execute("""
        SELECT * FROM subscriptions
        WHERE user_id = ?
        ORDER BY expires_at DESC
        LIMIT 1
    """, (callback.from_user.id,)).fetchone()

    if subscription:
        expiry = datetime.fromisoformat(
            subscription["expires_at"]
        )

        if expiry > datetime.now():
            lines.append(
                "\n💜 <b>ТВОЯ ПОДПИСКА</b>\n"
                f"Тариф: {html.escape(subscription['plan'])}\n"
                f"Действует до: {expiry.strftime('%d.%m.%Y %H:%M')}"
            )

        else:
            lines.append(
                "\n⚠️ Срок действия подписки закончился."
            )

    await callback.message.edit_text(
        "\n\n".join(lines),
        reply_markup=back_menu()
    )

    await callback.answer()


# ============================================================
# КАСТОМНАЯ ПРИВИЛЕГИЯ
# ============================================================

@dp.callback_query(F.data == "custom")
async def custom_start(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.set_state(CustomState.idea)

    await callback.message.edit_text(
        "👑 <b>КАСТОМНАЯ ПРИВИЛЕГИЯ</b>\n\n"
        "Придумай собственную реализуемую привилегию. "
        "Мы обсудим возможности, ограничения "
        "и индивидуальную цену.\n\n"
        "✏️ Опиши свою идею сообщением:",
        reply_markup=back_menu(),
    )

    await callback.answer()


@dp.message(CustomState.idea)
async def custom_idea(
    message: Message,
    state: FSMContext
):
    idea = (message.text or "").strip()

    if not 5 <= len(idea) <= 1000:
        await message.answer(
            "❌ Опиши идею от 5 до 1000 символов."
        )
        return

    await state.clear()

    await message.answer(
        "✅ <b>ЗАЯВКА ОТПРАВЛЕНА!</b>\n\n"
        "Владелец рассмотрит твою идею. "
        "Для обсуждения можешь написать ему:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Написать владельцу",
                        url=f"https://t.me/{OWNER_USERNAME}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏠 Главное меню",
                        callback_data="home"
                    )
                ],
            ]
        ),
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            "👑 <b>НОВАЯ КАСТОМНАЯ ЗАЯВКА</b>\n\n"
            f"Игрок: @{html.escape(message.from_user.username or 'нет')}\n"
            f"Telegram ID: <code>{message.from_user.id}</code>\n\n"
            f"Идея:\n{html.escape(idea)}",
        )

    except Exception as error:
        print(
            f"Не удалось отправить кастомную заявку владельцу: {error}"
        )


# ============================================================
# ИНФОРМАЦИЯ ОБ ОТКАТАХ
# ============================================================

@dp.callback_query(F.data == "rollback_info")
async def rollback_info(callback: CallbackQuery):
    await callback.message.edit_text(
        "♻️ <b>ОТКАТ ИНВЕНТАРЯ</b>\n\n"
        "Откат возвращает инвентарь к сохранённому "
        "состоянию и не создаёт копии предметов.\n\n"
        "<b>Лимиты подписок:</b>\n"
        "🟢 ЭЛИЗИУМ+ — 1 откат в месяц\n"
        "🔵 ЭЛИЗИУМ++ — 3 отката в месяц\n"
        "🟣 ЭЛИЗИУМ+++ — 5 откатов в месяц\n\n"
        "━━━━━━━━━━━━━━\n"
        "💰 <b>Дополнительный откат</b>\n"
        f"♻️ 1 откат — {ROLLBACK_PRICE} ₽\n\n"
        "Его можно приобрести отдельно, без подписки.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"🛒 Купить откат — {ROLLBACK_PRICE} ₽",
                        callback_data="buy_rollback"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Главное меню",
                        callback_data="home"
                    )
                ],
            ]
        ),
    )

    await callback.answer()


# ============================================================
# ИНФОРМАЦИЯ О СЕРВЕРЕ
# ============================================================

@dp.callback_query(F.data == "server")
async def server_info(callback: CallbackQuery):
    await callback.message.edit_text(
        f"💜 <b>СЕРВЕР {SERVER_NAME}</b>\n\n"
        f"🌐 IP: <code>{SERVER_IP}</code>\n"
        f"🎮 Версия: <code>{SERVER_VERSION}</code>\n\n"
        "💜 Элизиум — свой стиль. Свой статус. Своя история.",
        reply_markup=back_menu(),
    )

    await callback.answer()


# ============================================================
# IP И ВЕРСИЯ В ЛИЧКЕ И ГРУППАХ
# ============================================================

@dp.message(
    F.text.regexp(r"^/(?:ip|айпи)(?:@\w+)?(?:\s|$)")
)
async def send_server_ip(message: Message):
    await message.reply(
        f"💜 <b>MINECRAFT СЕРВЕР {SERVER_NAME}</b>\n\n"
        f"🌐 IP: <code>{SERVER_IP}</code>\n"
        f"🎮 Версия: <code>{SERVER_VERSION}</code>\n\n"
        "✨ Элизиум — свой стиль. Свой статус. Своя история."
    )


# ============================================================
# АДМИН-ПАНЕЛЬ
# ============================================================

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        "👑 <b>АДМИН-ПАНЕЛЬ ЭЛИЗИУМА</b>\n\n"
        "Управление заказами:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📦 Ожидающие заказы",
                        callback_data="admin_orders"
                    )
                ]
            ]
        ),
    )


@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "Нет доступа!",
            show_alert=True
        )
        return

    orders = get_pending_orders()

    if not orders:
        await callback.message.answer(
            "📭 Нет заказов, ожидающих оплаты."
        )

        await callback.answer()
        return

    for order in orders:
        await callback.message.answer(
            f"📦 <b>ЗАКАЗ №{order['id']}</b>\n\n"
            f"Игрок: @{html.escape(order['username'] or 'нет')}\n"
            f"Telegram ID: <code>{order['user_id']}</code>\n"
            f"Никнейм: <code>{html.escape(order['nickname'])}</code>\n"
            f"Товар: {html.escape(order['product'])}\n"
            f"Цена: {order['price']} ₽\n"
            f"Дата: {html.escape(order['created_at'])}\n\n"
            "Перед подтверждением проверь поступление оплаты.",
            reply_markup=admin_order_keyboard(order["id"]),
        )

    await callback.answer()


# ============================================================
# ПОДТВЕРЖДЕНИЕ ОПЛАТЫ
# ============================================================

@dp.callback_query(F.data.startswith("paid_"))
async def confirm_payment(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "Нет доступа!",
            show_alert=True
        )
        return

    order_id = int(
        callback.data.removeprefix("paid_")
    )

    order, expiry = process_order(
        order_id,
        "paid"
    )

    if not order:
        await callback.answer(
            "Заказ уже обработан или не найден.",
            show_alert=True
        )
        return

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    if order["product"] == ROLLBACK_PRODUCT_NAME:

        user_text = (
            "♻️ <b>ОПЛАТА ЗА ДОПОЛНИТЕЛЬНЫЙ ОТКАТ ПОДТВЕРЖДЕНА!</b>\n\n"
            f"Заказ №{order_id}\n"
            f"Товар: {ROLLBACK_PRODUCT_NAME}\n"
            f"Стоимость: {ROLLBACK_PRICE} ₽\n\n"
            "Для согласования выдачи отката "
            "свяжись с администрацией:\n"
            f"@{OWNER_USERNAME}"
        )

    else:

        user_text = (
            "🎉 <b>ОПЛАТА ПОДТВЕРЖДЕНА!</b>\n\n"
            f"Заказ №{order_id}\n"
            f"Подписка: {html.escape(order['product'])}\n"
            f"Действует до: {expiry.strftime('%d.%m.%Y %H:%M')}\n\n"
            "Спасибо за поддержку Элизиума! 💜"
        )

    try:
        await bot.send_message(
            order["user_id"],
            user_text
        )

    except Exception as error:
        print(
            f"Не удалось уведомить покупателя: {error}"
        )

    await callback.message.answer(
        f"✅ Заказ №{order_id} подтверждён."
    )

    await callback.answer(
        "Оплата подтверждена!"
    )


# ============================================================
# ОТКЛОНЕНИЕ ЗАКАЗА
# ============================================================

@dp.callback_query(F.data.startswith("reject_"))
async def reject_order(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "Нет доступа!",
            show_alert=True
        )
        return

    order_id = int(
        callback.data.removeprefix("reject_")
    )

    order, _ = process_order(
        order_id,
        "rejected"
    )

    if not order:
        await callback.answer(
            "Заказ уже обработан или не найден.",
            show_alert=True
        )
        return

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    try:
        await bot.send_message(
            order["user_id"],
            "❌ <b>ЗАКАЗ ОТКЛОНЁН</b>\n\n"
            f"Номер заказа: {order_id}\n\n"
            "Если возникла ошибка, свяжись с владельцем:\n"
            f"@{OWNER_USERNAME}",
        )

    except Exception as error:
        print(
            f"Не удалось уведомить покупателя: {error}"
        )

    await callback.message.answer(
        f"❌ Заказ №{order_id} отклонён."
    )

    await callback.answer(
        "Заказ отклонён."
    )


# ============================================================
# НАПОМИНАНИЯ ОБ ОКОНЧАНИИ ПОДПИСКИ
# ============================================================

async def subscription_reminders():
    while True:
        try:
            now = datetime.now()

            subscriptions = db.execute("""
                SELECT * FROM subscriptions
                WHERE reminder_sent = 0
            """).fetchall()

            for subscription in subscriptions:
                expiry = datetime.fromisoformat(
                    subscription["expires_at"]
                )

                remaining = expiry - now

                if (
                    timedelta(0)
                    < remaining
                    <= timedelta(days=3)
                ):

                    try:
                        await bot.send_message(
                            subscription["user_id"],
                            "⏰ <b>ПОДПИСКА СКОРО ЗАКОНЧИТСЯ!</b>\n\n"
                            f"Твоя подписка "
                            f"{html.escape(subscription['plan'])} "
                            f"закончится "
                            f"{expiry.strftime('%d.%m.%Y %H:%M')}.\n\n"
                            "Чтобы продлить её, открой магазин "
                            "командой /start.",
                        )

                        db.execute("""
                            UPDATE subscriptions
                            SET reminder_sent = 1
                            WHERE id = ?
                        """, (
                            subscription["id"],
                        ))

                        db.commit()

                    except Exception as error:
                        print(
                            f"Ошибка отправки напоминания: {error}"
                        )

        except Exception as error:
            print(
                f"Ошибка проверки подписок: {error}"
            )

        await asyncio.sleep(3600)


# ============================================================
# ЗАПУСК
# ============================================================

async def main():

    if BOT_TOKEN == "ВСТАВЬ_СЮДА_ТОКЕН_БОТА":
        raise RuntimeError(
            "Сначала вставь токен Telegram-бота в BOT_TOKEN."
        )

    if ADMIN_ID == 123456789:
        raise RuntimeError(
            "Сначала укажи свой числовой Telegram ID в ADMIN_ID."
        )

    init_db()

    print("====================================")
    print("💜 МАГАЗИН ЭЛИЗИУМА ЗАПУЩЕН")
    print(f"IP: {SERVER_IP}")
    print(f"Версия: {SERVER_VERSION}")
    print(f"Дополнительный откат: {ROLLBACK_PRICE} ₽")
    print("====================================")

    reminder_task = asyncio.create_task(
        subscription_reminders()
    )

    try:
        # Запускай только один экземпляр бота.
        await dp.start_polling(bot)

    finally:
        reminder_task.cancel()

        try:
            await reminder_task

        except asyncio.CancelledError:
            pass

        await bot.session.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
