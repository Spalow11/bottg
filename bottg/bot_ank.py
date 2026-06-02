import asyncio
import json
import os
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8726993851:AAEhvlW38fO1bbuUPgGn_YPzjFTLciGnL40"
ADMIN_ID = 5934335006
CHAT_LINK = "https://t.me/+PvAJvdinyNYwZDQy"
PAYMENT_LINK = "https://www.donationalerts.com/r/spalow1"

# Функция для экранирования Markdown
def escape_md(text: str) -> str:
    if not text:
        return ""
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', text)

# Информация о сервере
ABOUT_SERVER = """
🏰 О сервере Elysium

✨ Особенности:
• Приватный сервер с дружным комьюнити
• Уникальная экономика и кастомные предметы
• Регулярные ивенты и конкурсы
• Активная администрация

🎮 Версия: 26.1.2
🌍 IP: 94.26.248.5:32401


Присоединяйся к нам и стань частью нашего мира! 🚀
"""

# ========== ЕДИНЫЙ ДОНАТ ==========
DONATION = {
    "name": "💎 Спонсорка",
    "description": "▸ Поддержка сервера\n▸ Доступ на сервер\n▸ Привилегии и бонусы(админу в лс писать)\n▸ Отдельная роль в Discord",
    "price": "499 ₽",
    "type": "месяц",
    "link": "https://www.donationalerts.com/r/spalow1?amount=499"
}
# =================================

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

APPLICATIONS_FILE = "applications.json"
USERS_FILE = "users.json"

# Функции для работы с пользователями
def save_user(user_id: int, username: str = None, first_name: str = None):
    users = load_users()
    for user in users:
        if user["id"] == user_id:
            user["last_seen"] = datetime.now().isoformat()
            save_users(users)
            return
    users.append({
        "id": user_id,
        "username": username or f"user_{user_id}",
        "first_name": first_name or "Unknown",
        "first_seen": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat()
    })
    save_users(users)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_applications():
    if os.path.exists(APPLICATIONS_FILE):
        with open(APPLICATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_application(application_data):
    applications = load_applications()
    applications.append(application_data)
    with open(APPLICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(applications, f, ensure_ascii=False, indent=2)

def update_application_status(application_id, status):
    applications = load_applications()
    for app in applications:
        if app["id"] == application_id:
            app["status"] = status
            app["reviewed_at"] = datetime.now().isoformat()
            break
    with open(APPLICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(applications, f, ensure_ascii=False, indent=2)

# Клавиатуры
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏰 О сервере")],
            [KeyboardButton(text="📝 Заявка")],
            [KeyboardButton(text="💎 Спонсорка")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_donation_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💸 Оплатить {DONATION['price']}", url=DONATION['link'])],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
    ])
    return keyboard

def admin_kb(user_id: int, app_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{user_id}_{app_id}")],
        [InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_{user_id}_{app_id}")],
        [InlineKeyboardButton(text="📋 История", callback_data=f"history_{user_id}")],
        [InlineKeyboardButton(text="📋 Скопировать ник", callback_data=f"copy_nick_{user_id}_{app_id}")]
    ])

class Form(StatesGroup):
    nick = State()
    age = State()
    source = State()
    plans = State()
    about = State()

# ========== ОБРАБОТЧИКИ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        "🎮 Добро пожаловать на сервер Elysium!\n\n"
        "Я помогу тебе подать заявку или узнать информацию о сервере.\n\n"
        "Используй кнопки ниже для навигации:",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "🏰 О сервере")
async def about_server(message: types.Message):
    save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(ABOUT_SERVER, reply_markup=get_main_keyboard())

@dp.message(F.text == "📝 Заявка")
async def start_application(message: types.Message, state: FSMContext):
    await state.clear()
    save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        "📝 Подача заявки\n\n"
        "Чтобы подать заявку, заполните небольшую анкету.\n"
        "Введите ваш никнейм:",
        reply_markup=get_main_keyboard()
    )
    await state.set_state(Form.nick)

@dp.message(F.text == "💎 Спонсорка")
async def show_donation(message: types.Message):
    save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    text = (
        f"💎 *{DONATION['name']}*\n\n"
        f"📦 *Что даёт:*\n{DONATION['description']}\n\n"
        f"💰 *Цена:* {DONATION['price']}\n"
        f"📅 *Тип:* {DONATION['type']}\n\n"
        f"Нажми на кнопку ниже, чтобы поддержать сервер:"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_donation_keyboard())

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "🎮 Главное меню\n\nИспользуй кнопки ниже для навигации:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

# ========== АНКЕТА ==========
@dp.message(Form.nick)
async def get_nick(message: types.Message, state: FSMContext):
    await state.update_data(nick=message.text)
    await message.answer("📅 Укажите ваш возраст (только число):")
    await state.set_state(Form.age)

@dp.message(Form.age)
async def get_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число (ваш возраст):")
        return
    await state.update_data(age=message.text)
    await message.answer("🔍 Откуда узнали о сервере? (реклама, друг, тикток и т.д.):")
    await state.set_state(Form.source)

@dp.message(Form.source)
async def get_source(message: types.Message, state: FSMContext):
    await state.update_data(source=message.text)
    await message.answer("🛠 Чем планируете заниматься на сервере? (строительство, PvP, фермы и т.д.):")
    await state.set_state(Form.plans)

@dp.message(Form.plans)
async def get_plans(message: types.Message, state: FSMContext):
    await state.update_data(plans=message.text)
    await message.answer("📝 Немного о себе (расскажите о своих интересах, опыте игры):")
    await state.set_state(Form.about)

@dp.message(Form.about)
async def get_about(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    data = await state.get_data()
    
    app_id = f"{message.from_user.id}_{datetime.now().timestamp()}"
    username = message.from_user.username or f"user_{message.from_user.id}"
    
    safe_username = escape_md(username)
    safe_nick = escape_md(data['nick'])
    safe_age = escape_md(data['age'])
    safe_source = escape_md(data['source'])
    safe_plans = escape_md(data['plans'])
    safe_about = escape_md(data['about'])
    
    application_record = {
        "id": app_id,
        "user_id": message.from_user.id,
        "username": f"@{username}" if message.from_user.username else str(message.from_user.id),
        "nick": data['nick'],
        "age": int(data['age']),
        "source": data['source'],
        "plans": data['plans'],
        "about": data['about'],
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        "reviewed_at": None
    }
    
    save_application(application_record)
    
    # Отправляем заявку админу
    application_text = (
        f"📬 НОВАЯ ЗАЯВКА!\n"
        f"🆔 ID: `{app_id[:8]}...`\n\n"
        f"👤 Ник: {safe_nick}\n"
        f"🎂 Возраст: {safe_age}\n"
        f"🔍 Откуда узнал: {safe_source}\n"
        f"🛠 Планы: {safe_plans}\n"
        f"📖 О себе: {safe_about}\n\n"
        f"👥 ID игрока: `{message.from_user.id}`\n"
        f"👥 Username: @{username}"
    )
    
    await bot.send_message(
        ADMIN_ID,
        application_text,
        parse_mode="Markdown",
        reply_markup=admin_kb(message.from_user.id, app_id)
    )
    
    await message.answer(
        "✅ Ваша заявка отправлена на рассмотрение!\n"
        "Ожидайте ответа в этом чате.",
        reply_markup=get_main_keyboard()
    )
    await state.clear()

# ========== ОБРАБОТКА РЕШЕНИЙ ==========
@dp.callback_query(F.data.startswith("accept_"))
async def accept_user(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[1])
    app_id = parts[2]
    
    await callback.answer()
    update_application_status(app_id, "accepted")
    
    try:
        await bot.send_message(
            user_id,
            f"🎉 Поздравляем! Вы были приняты на сервер Elysium!\n\n"
            f"Присоединяйтесь к нашему чату: {CHAT_LINK}\n"
            f"Добро пожаловать и приятной игры! 🚀"
        )
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ РЕШЕНИЕ: ПРИНЯТ"
        )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {e}")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_user(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[1])
    app_id = parts[2]
    
    await callback.answer()
    update_application_status(app_id, "rejected")
    
    try:
        await bot.send_message(
            user_id,
            f"😔 Вам было отказано в бесплатном доступе.\n\n"
            f"Но вы можете приобрести проходку на сервер:\n"
            f"👉 {PAYMENT_LINK}\n\n"
            f"После оплаты вы сразу получите доступ."
        )
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ РЕШЕНИЕ: ОТКАЗАНО"
        )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {e}")

@dp.callback_query(F.data.startswith("copy_nick_"))
async def copy_nick(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[2])
    app_id = parts[3]
    
    # Находим заявку
    applications = load_applications()
    nick = None
    for app in applications:
        if app["id"] == app_id:
            nick = app["nick"]
            break
    
    if nick:
        await callback.message.answer(
            f"📋 *Ник для копирования:*\n"
            f"`{nick}`\n\n"
            f"Выделите ник выше и скопируйте (Ctrl+C или долгое нажатие)",
            parse_mode="Markdown"
        )
        await callback.answer("✅ Ник отправлен!")
    else:
        await callback.answer("❌ Ник не найден")

@dp.callback_query(F.data.startswith("history_"))
async def show_user_history(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await callback.answer()
    
    applications = load_applications()
    user_apps = [app for app in applications if app["user_id"] == user_id]
    
    if not user_apps:
        await callback.message.answer("📭 У этого пользователя нет заявок.")
        return
    
    text = f"📋 История заявок:\n\n"
    for app in user_apps[-5:]:
        status_emoji = {"accepted": "✅", "rejected": "❌", "pending": "⏳"}.get(app["status"], "❓")
        created = datetime.fromisoformat(app["created_at"]).strftime("%d.%m.%Y %H:%M")
        text += f"{status_emoji} {app['nick']} ({app['age']} лет)\n"
        text += f"   📅 {created}\n"
        text += f"   Статус: {app['status']}\n\n"
    
    await callback.message.answer(text)

# ========== ЗАПУСК ==========
async def main():
    if not os.path.exists(APPLICATIONS_FILE):
        with open(APPLICATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    
    print("✅ Бот для сервера Elysium запущен!")
    print(f"👑 Админ: {ADMIN_ID}")
    print(f"💬 Чат: {CHAT_LINK}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
