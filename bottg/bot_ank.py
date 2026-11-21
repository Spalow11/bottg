
import asyncio
import sqlite3
import re
from datetime import datetime, timedelta
from urllib.parse import quote

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode


# ==================================================
# НАСТРОЙКИ
# ==================================================

TOKEN = "9187444592:AAEwVWdvMPdQ3x1J9l0fZTfMTplmPxX1NHs"

# Твой Telegram ID (числовой)
ADMIN_ID = 8839415985

OWNER = "ceo_elysium"

SERVER_IP = "elysium.mc-join.me"
SERVER_VERSION = "26.1.2"

DB_NAME = "kvant_shop.db"


# ==================================================
# БОТ И БАЗА
# ==================================================

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())

db = sqlite3.connect(DB_NAME)
db.row_factory = sqlite3.Row


def init_db():
    db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            nickname TEXT,
            plan TEXT,
            price INTEGER,
            status TEXT DEFAULT 'pending',
            created TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan TEXT,
            expires TEXT,
            reminder_sent INTEGER DEFAULT 0
        )
    """)

    db.commit()


# ==================================================
# ТАРИФЫ
# ==================================================

PLANS = {
    "plus": {
        "name": "КВАНТ+",
        "price": 149,
        "description": (
            "🎨 1 кастомный префикс в TAB\n"
            "🌈 Цветной чат\n"
            "✨ Все партиклы\n"
            "🥤 Собственный напиток\n"
            "♻️ 1 откат инвентаря в месяц\n"
            "🎙️ Приоритет в войс-чате"
        )
    },

    "plusplus": {
        "name": "КВАНТ++",
        "price": 299,
        "description": (
            "Всё из Квант+, плюс:\n\n"
            "🗿 1 личный тотем со своим скином\n"
            "👤 1 твинк\n"
            "♻️ 3 отката инвентаря в месяц\n"
            "🎭 Кастомная роль в Discord + Telegram\n"
            "🎙️ Повышенный приоритет в войс-чате"
        )
    },

    "plusplusplus": {
        "name": "КВАНТ+++",
        "price": 499,
        "description": (
            "Всё из Квант++, плюс:\n\n"
            "🗿 До 2 личных тотемов\n"
            "👤 До 2 твинков\n"
            "♻️ 5 откатов инвентаря в месяц\n"
            "🎭 Расширенная кастомная роль\n"
            "🎙️ Максимальный приоритет в войс-чате\n"
            "✨ Дополнительная кастомизация"
        )
    }
}


# ==================================================
# СОСТОЯНИЯ
# ==================================================

class BuyState(StatesGroup):
    nickname = State()


class CustomState(StatesGroup):
    idea = State()


# ==================================================
# КЛАВИАТУРЫ
# ==================================================

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💜 Купить подписку",
                callback_data="catalog"
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
                text="👑 Кастомная привилегия",
                callback_data="custom"
            )
        ],
        [
            InlineKeyboardButton(
                text="♻️ Откат инвентаря",
                callback_data="rollback"
            )
        ],
        [
            InlineKeyboardButton(
                text="🌐 О сервере",
                callback_data="server"
            )
        ]
    ])


def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⬅️ Главное меню",
                callback_data="home"
            )
        ]
    ])


def admin_keyboard(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
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
        ]
    ])


# ==================================================
# РАБОТА С ЗАКАЗАМИ
# ==================================================

def create_order(user_id, username, nickname, plan, price):
    cursor = db.execute("""
        INSERT INTO orders
        (user_id, username, nickname, plan, price, status, created)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (
        user_id,
        username,
        nickname,
        plan,
        price,
        datetime.now().isoformat()
    ))

    db.commit()
    return cursor.lastrowid


def get_orders(user_id):
    return db.execute("""
        SELECT * FROM orders
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 10
    """, (user_id,)).fetchall()


def get_pending_orders():
    return db.execute("""
        SELECT * FROM orders
        WHERE status='pending'
        ORDER BY id DESC
    """).fetchall()


# ==================================================
# АКТИВАЦИЯ ПОДПИСКИ
# ==================================================

def activate_subscription(order):
    now = datetime.now()

    current = db.execute("""
        SELECT * FROM subscriptions
        WHERE user_id=?
        ORDER BY expires DESC
        LIMIT 1
    """, (order["user_id"],)).fetchone()

    if current:
        old_expiry = datetime.fromisoformat(current["expires"])
        start_date = max(now, old_expiry)
        new_expiry = start_date + timedelta(days=30)

        db.execute("""
            UPDATE subscriptions
            SET plan=?, expires=?, reminder_sent=0
            WHERE id=?
        """, (
            order["plan"],
            new_expiry.isoformat(),
            current["id"]
        ))

    else:
        new_expiry = now + timedelta(days=30)

        db.execute("""
            INSERT INTO subscriptions
            (user_id, plan, expires, reminder_sent)
            VALUES (?, ?, ?, 0)
        """, (
            order["user_id"],
            order["plan"],
            new_expiry.isoformat()
        ))

    db.commit()
    return new_expiry


def process_order(order_id, status):
    order = db.execute("""
        SELECT * FROM orders
        WHERE id=?
    """, (order_id,)).fetchone()

    if not order or order["status"] != "pending":
        return None, None

    db.execute("""
        UPDATE orders
        SET status=?
        WHERE id=?
    """, (status, order_id))

    expiry = None

    if status == "paid":
        expiry = activate_subscription(order)

    db.commit()

    return order, expiry


# ==================================================
# СТАРТ
# ==================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "💜 <b>ДОБРО ПОЖАЛОВАТЬ В KVANT SHOP!</b>\n\n"
        "Здесь ты можешь приобрести подписку, "
        "заказать индивидуальную привилегию "
        "и узнать больше о возможностях проекта.\n\n"
        "Выбирай интересующий раздел 👇",
        reply_markup=main_menu()
    )


@dp.callback_query(F.data == "home")
async def home(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text(
        "💜 <b>МАГАЗИН КВАНТА</b>\n\n"
        "Выбирай интересующий раздел:",
        reply_markup=main_menu()
    )

    await callback.answer()


# ==================================================
# КАТАЛОГ
# ==================================================

@dp.callback_query(F.data == "catalog")
async def catalog(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🟢 КВАНТ+ — 149 ₽/мес",
                callback_data="plan_plus"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔵 КВАНТ++ — 299 ₽/мес ⭐",
                callback_data="plan_plusplus"
            )
        ],
        [
            InlineKeyboardButton(
                text="🟣 КВАНТ+++ — 499 ₽/мес",
                callback_data="plan_plusplusplus"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="home"
            )
        ]
    ])

    await callback.message.edit_text(
        "💜 <b>ВЫБЕРИ ПОДПИСКУ</b>\n\n"
        "Все тарифы оформляются на 30 дней.\n\n"
        "Выбери подходящий вариант:",
        reply_markup=keyboard
    )

    await callback.answer()


# ==================================================
# ИНФОРМАЦИЯ О ТАРИФАХ
# ==================================================

@dp.callback_query(F.data.startswith("plan_"))
async def show_plan(callback: CallbackQuery):
    key = callback.data.replace("plan_", "")
    plan = PLANS[key]

    await callback.message.edit_text(
        f"<b>{plan['name']} — {plan['price']} ₽/мес</b>\n\n"
        f"{plan['description']}\n\n"
        "━━━━━━━━━━━━━━\n"
        "📅 Срок действия: 30 дней\n\n"
        "💰 Покупая подписку, ты добровольно "
        "поддерживаешь развитие проекта.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
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
            ]
        ])
    )

    await callback.answer()


# ==================================================
# ПОКУПКА
# ==================================================

@dp.callback_query(F.data.startswith("buy_"))
async def buy(callback: CallbackQuery, state: FSMContext):
    key = callback.data.replace("buy_", "")

    await state.update_data(plan=key)
    await state.set_state(BuyState.nickname)

    await callback.message.edit_text(
        "🛒 <b>ОФОРМЛЕНИЕ ПОКУПКИ</b>\n\n"
        "✏️ Введи свой игровой никнейм Minecraft:",
        reply_markup=back_menu()
    )

    await callback.answer()


@dp.message(BuyState.nickname)
async def get_nickname(message: Message, state: FSMContext):
    nickname = (message.text or "").strip()

    if not re.fullmatch(r"[A-Za-z0-9_]{3,16}", nickname):
        await message.answer(
            "❌ Некорректный никнейм!\n\n"
            "Используй от 3 до 16 символов: "
            "английские буквы, цифры и _."
        )
        return

    data = await state.get_data()
    key = data["plan"]
    plan = PLANS[key]

    order_id = create_order(
        message.from_user.id,
        message.from_user.username or "нет",
        nickname,
        plan["name"],
        plan["price"]
    )

    await state.clear()

    await message.answer(
        f"✅ <b>ЗАКАЗ №{order_id} СОЗДАН!</b>\n\n"
        f"Подписка: {plan['name']}\n"
        f"Цена: {plan['price']} ₽\n"
        f"Никнейм: <code>{nickname}</code>\n\n"
        "Заявка отправлена владельцу.\n"
        "Для согласования оплаты напиши ему:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Написать владельцу",
                    url=f"https://t.me/{OWNER}"
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
            ]
        ])
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            f"🛒 <b>НОВЫЙ ЗАКАЗ №{order_id}</b>\n\n"
            f"Игрок: @{message.from_user.username or 'нет'}\n"
            f"Telegram ID: <code>{message.from_user.id}</code>\n"
            f"Никнейм: <code>{nickname}</code>\n"
            f"Подписка: {plan['name']}\n"
            f"Стоимость: {plan['price']} ₽\n\n"
            "Ожидает подтверждения оплаты.",
            reply_markup=admin_keyboard(order_id)
        )
    except Exception as error:
        print("Не удалось отправить заказ админу:", error)


# ==================================================
# ИСТОРИЯ ПОКУПОК
# ==================================================

@dp.callback_query(F.data == "history")
async def history(callback: CallbackQuery):
    orders = get_orders(callback.from_user.id)

    text = "📋 <b>МОИ ПОКУПКИ</b>\n\n"

    if not orders:
        text += "У тебя пока нет заказов."
    else:
        statuses = {
            "pending": "⏳ Ожидает оплаты",
            "paid": "✅ Оплачено",
            "rejected": "❌ Отклонено"
        }

        for order in orders:
            text += (
                f"🛒 <b>Заказ №{order['id']}</b>\n"
                f"Тариф: {order['plan']}\n"
                f"Цена: {order['price']} ₽\n"
                f"Статус: {statuses.get(order['status'], order['status'])}\n"
                "━━━━━━━━━━━━━━\n"
            )

    subscription = db.execute("""
        SELECT * FROM subscriptions
        WHERE user_id=?
        ORDER BY expires DESC
        LIMIT 1
    """, (callback.from_user.id,)).fetchone()

    if subscription:
        expiry = datetime.fromisoformat(subscription["expires"])

        if expiry > datetime.now():
            text += (
                "\n💜 <b>ТВОЯ ПОДПИСКА</b>\n"
                f"Тариф: {subscription['plan']}\n"
                f"Действует до: {expiry.strftime('%d.%m.%Y %H:%M')}"
            )
        else:
            text += "\n⚠️ Твоя подписка закончилась."

    await callback.message.edit_text(
        text,
        reply_markup=back_menu()
    )

    await callback.answer()


# ==================================================
# КАСТОМНАЯ ПРИВИЛЕГИЯ
# ==================================================

@dp.callback_query(F.data == "custom")
async def custom(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CustomState.idea)

    await callback.message.edit_text(
        "👑 <b>КАСТОМНАЯ ПРИВИЛЕГИЯ</b>\n\n"
        "Хочешь что-то своё?\n\n"
        "Придумай любую реализуемую привилегию. "
        "Мы обсудим возможности, ограничения "
        "и назначим индивидуальную цену.\n\n"
        "✏️ Опиши свою идею одним сообщением:",
        reply_markup=back_menu()
    )

    await callback.answer()


@dp.message(CustomState.idea)
async def custom_idea(message: Message, state: FSMContext):
    idea = (message.text or "").strip()

    if not 5 <= len(idea) <= 1000:
        await message.answer(
            "❌ Напиши идею длиной от 5 до 1000 символов."
        )
        return

    await state.clear()

    await message.answer(
        "✅ <b>ЗАЯВКА ОТПРАВЛЕНА!</b>\n\n"
        "Владелец рассмотрит твою идею и свяжется с тобой.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Написать владельцу",
                    url=f"https://t.me/{OWNER}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="home"
                )
            ]
        ])
    )

    await bot.send_message(
        ADMIN_ID,
        "👑 <b>НОВАЯ КАСТОМНАЯ ЗАЯВКА</b>\n\n"
        f"Игрок: @{message.from_user.username or 'нет'}\n"
        f"Telegram ID: <code>{message.from_user.id}</code>\n\n"
        f"Идея:\n{idea}"
    )


# ==================================================
# ОТКАТ ИНВЕНТАРЯ
# ==================================================

@dp.callback_query(F.data == "rollback")
async def rollback(callback: CallbackQuery):
    await callback.message.edit_text(
        "♻️ <b>ОТКАТ ИНВЕНТАРЯ</b>\n\n"
        "Откат возвращает инвентарь к сохранённому "
        "состоянию и не создаёт копии предметов.\n\n"
        "Лимиты на месяц:\n\n"
        "🟢 Квант+ — 1 откат\n"
        "🔵 Квант++ — 3 отката\n"
        "🟣 Квант+++ — 5 откатов\n\n"
        "Откат входит в соответствующие подписки.",
        reply_markup=back_menu()
    )

    await callback.answer()


# ==================================================
# ИНФОРМАЦИЯ О СЕРВЕРЕ
# ==================================================

@dp.callback_query(F.data == "server")
async def server(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌐 <b>СЕРВЕР КВАНТ</b>\n\n"
        f"IP: <code>{SERVER_IP}</code>\n"
        f"Версия: <code>{SERVER_VERSION}</code>\n\n"
        "💜 Квант — свой стиль. Свой статус. Своя история.\n\n"
        "Покупая подписку, ты добровольно поддерживаешь "
        "развитие проекта.",
        reply_markup=back_menu()
    )

    await callback.answer()


# ==================================================
# КОМАНДА IP В ГРУППАХ И ЛИЧНЫХ СООБЩЕНИЯХ
# ==================================================

@dp.message(
    F.text.regexp(r"^/(?:ip|айпи)(?:@\w+)?(?:\s|$)")
)
async def send_ip(message: Message):
    await message.reply(
        "💜 <b>MINECRAFT СЕРВЕР КВАНТ</b>\n\n"
        f"🌐 IP: <code>{SERVER_IP}</code>\n"
        f"🎮 Версия: <code>{SERVER_VERSION}</code>\n\n"
        "✨ Квант — свой стиль. Свой статус. Своя история."
    )


# ==================================================
# АДМИН-ПАНЕЛЬ
# ==================================================

@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        "👑 <b>АДМИН-ПАНЕЛЬ KVANT SHOP</b>\n\n"
        "Управление заказами:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Ожидающие заказы",
                    callback_data="admin_orders"
                )
            ]
        ])
    )


@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return

    orders = get_pending_orders()

    if not orders:
        await callback.message.answer(
            "📭 Сейчас нет заказов, ожидающих оплаты."
        )
        await callback.answer()
        return

    for order in orders:
        await callback.message.answer(
            f"📦 <b>ЗАКАЗ №{order['id']}</b>\n\n"
            f"Игрок: @{order['username']}\n"
            f"Telegram ID: <code>{order['user_id']}</code>\n"
            f"Никнейм: <code>{order['nickname']}</code>\n"
            f"Тариф: {order['plan']}\n"
            f"Цена: {order['price']} ₽\n"
            f"Дата: {order['created']}",
            reply_markup=admin_keyboard(order["id"])
        )

    await callback.answer()


# ==================================================
# ПОДТВЕРЖДЕНИЕ ОПЛАТЫ
# ==================================================

@dp.callback_query(F.data.startswith("paid_"))
async def paid(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return

    order_id = int(callback.data.split("_")[1])

    order, expiry = process_order(order_id, "paid")

    if not order:
        await callback.answer(
            "Заказ уже обработан или не найден.",
            show_alert=True
        )
        return

    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        f"✅ Заказ №{order_id} успешно подтверждён!\n"
        f"Подписка действует до {expiry.strftime('%d.%m.%Y %H:%M')}."
    )

    try:
        await bot.send_message(
            order["user_id"],
            "🎉 <b>ОПЛАТА ПОДТВЕРЖДЕНА!</b>\n\n"
            f"Заказ №{order_id}\n"
            f"Подписка: {order['plan']}\n"
            f"Действует до: {expiry.strftime('%d.%m.%Y %H:%M')}\n\n"
            "Спасибо за поддержку Кванта! 💜"
        )
    except Exception as error:
        print("Не удалось уведомить игрока:", error)

    await callback.answer("Оплата подтверждена!")


# ==================================================
# ОТКЛОНЕНИЕ ЗАКАЗА
# ==================================================

@dp.callback_query(F.data.startswith("reject_"))
async def reject(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return

    order_id = int(callback.data.split("_")[1])

    order, _ = process_order(order_id, "rejected")

    if not order:
        await callback.answer(
            "Заказ уже обработан или не найден.",
            show_alert=True
        )
        return

    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        f"❌ Заказ №{order_id} отклонён."
    )

    try:
        await bot.send_message(
            order["user_id"],
            "❌ <b>ЗАКАЗ ОТКЛОНЁН</b>\n\n"
            f"Номер заказа: {order_id}\n\n"
            "Если возникла ошибка, свяжись с владельцем:\n"
            f"@{OWNER}"
        )
    except Exception as error:
        print("Не удалось уведомить игрока:", error)

    await callback.answer("Заказ отклонён.")


# ==================================================
# НАПОМИНАНИЯ О ПОДПИСКАХ
# ==================================================

async def subscription_reminders():
    while True:
        try:
            now = datetime.now()

            subscriptions = db.execute("""
                SELECT * FROM subscriptions
                WHERE reminder_sent=0
            """).fetchall()

            for sub in subscriptions:
                expiry = datetime.fromisoformat(sub["expires"])
                remaining = expiry - now

                if timedelta(0) < remaining <= timedelta(days=3):
                    try:
                        await bot.send_message(
                            sub["user_id"],
                            "⏰ <b>ПОДПИСКА СКОРО ЗАКОНЧИТСЯ!</b>\n\n"
                            f"Твоя подписка {sub['plan']} закончится "
                            f"{expiry.strftime('%d.%m.%Y %H:%M')}.\n\n"
                            "Чтобы продлить её, открой магазин:\n"
                            "/start"
                        )

                        db.execute("""
                            UPDATE subscriptions
                            SET reminder_sent=1
                            WHERE id=?
                        """, (sub["id"],))

                        db.commit()

                    except Exception as error:
                        print(
                            f"Ошибка уведомления пользователя "
                            f"{sub['user_id']}: {error}"
                        )

        except Exception as error:
            print("Ошибка системы напоминаний:", error)

        await asyncio.sleep(3600)


# ==================================================
# ЗАПУСК
# ==================================================

async def main():
    init_db()

    print("================================")
    print("💜 KVANT SHOP ЗАПУЩЕН")
    print(f"IP: {SERVER_IP}")
    print(f"Версия: {SERVER_VERSION}")
    print("================================")

    reminder_task = asyncio.create_task(
        subscription_reminders()
    )

    try:
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
