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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== НАСТРОЙКИ ==========
# Токен берется из переменных окружения (настройки Render)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# ТВОИ ДАННЫЕ (оставь как есть, они уже правильные):
ADMIN_ID = 6313154469
CHAT_LINK = "https://t.me/elysiumchatick"
PAYMENT_LINK = "https://www.donationalerts.com/r/spalow1"
# ================================

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

APPLICATIONS_FILE = "applications.json"

def escape_markdown(text: str) -> str:
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', text)

class Form(StatesGroup):
    nick = State()
    age = State()
    source = State()
    plans = State()
    about = State()

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

def admin_kb(user_id: int, app_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{user_id}_{app_id}")],
        [InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_{user_id}_{app_id}")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🎮 Добро пожаловать на сервер Elysium!\n\n"
        "Чтобы подать заявку, заполните небольшую анкету.\n"
        "Введите ваш никнейм:"
    )
    await state.set_state(Form.nick)

@dp.message(Form.nick)
async def get_nick(message: types.Message, state: FSMContext):
    await state.update_data(nick=escape_markdown(message.text))
    await message.answer("📅 Укажите ваш возраст (только число):")
    await state.set_state(Form.age)

@dp.message(Form.age)
async def get_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число (ваш возраст):")
        return
    await state.update_data(age=escape_markdown(message.text))
    await message.answer("🔍 Откуда узнали о сервере? (реклама, друг, тикток и т.д.):")
    await state.set_state(Form.source)

@dp.message(Form.source)
async def get_source(message: types.Message, state: FSMContext):
    await state.update_data(source=escape_markdown(message.text))
    await message.answer("🛠 Чем планируете заниматься на сервере? (строительство, PvP, фермы и т.д.):")
    await state.set_state(Form.plans)

@dp.message(Form.plans)
async def get_plans(message: types.Message, state: FSMContext):
    await state.update_data(plans=escape_markdown(message.text))
    await message.answer("📝 Немного о себе (расскажите о своих интересах, опыте игры):")
    await state.set_state(Form.about)

@dp.message(Form.about)
async def get_about(message: types.Message, state: FSMContext):
    await state.update_data(about=escape_markdown(message.text))
    data = await state.get_data()
    
    app_id = f"{message.from_user.id}_{datetime.now().timestamp()}"
    username = message.from_user.username or f"user_{message.from_user.id}"
    
    application_record = {
        "id": app_id,
        "user_id": message.from_user.id,
        "username": f"@{username}" if message.from_user.username else str(message.from_user.id),
        "nick": data['nick'],
        "age": data['age'],
        "source": data['source'],
        "plans": data['plans'],
        "about": data['about'],
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        "reviewed_at": None
    }
    
    save_application(application_record)
    
    application_text = (
        f"📬 НОВАЯ ЗАЯВКА!\n"
        f"🆔 ID заявки: {app_id[:8]}...\n\n"
        f"👤 Ник: {data['nick']}\n"
        f"🎂 Возраст: {data['age']}\n"
        f"🔍 Откуда узнал: {data['source']}\n"
        f"🛠 Планы: {data['plans']}\n"
        f"📖 О себе: {data['about']}\n\n"
        f"👥 Инфо: {application_record['username']} | ID: {message.from_user.id}"
    )
    
    await bot.send_message(
        ADMIN_ID,
        application_text,
        reply_markup=admin_kb(message.from_user.id, app_id)
    )
    
    await message.answer(
        "✅ Ваша заявка отправлена на рассмотрение!\n"
        "Ожидайте ответа в этом чате."
    )
    await state.clear()

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
            callback.message.text + "\n\n✅ Решение: ПРИНЯТ"
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
            f"Но вы можете приобрести проходку на сервер за 50р:\n"
            f"👉 {PAYMENT_LINK}\n\n"
            f"После оплаты вы сразу получите доступ."
        )
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ Решение: ОТКАЗАНО"
        )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет прав для этой команды.")
        return
    
    applications = load_applications()
    total = len(applications)
    accepted = len([a for a in applications if a["status"] == "accepted"])
    rejected = len([a for a in applications if a["status"] == "rejected"])
    pending = len([a for a in applications if a["status"] == "pending"])
    
    await message.answer(
        f"📊 Статистика заявок на сервер Elysium:\n\n"
        f"📝 Всего заявок: {total}\n"
        f"✅ Принято: {accepted}\n"
        f"❌ Отказано: {rejected}\n"
        f"⏳ В ожидании: {pending}"
    )

@dp.message(Command("list"))
async def list_applications(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет прав для этой команды.")
        return
    
    applications = load_applications()
    if not applications:
        await message.answer("📭 Пока нет ни одной заявки.")
        return
    
    recent = applications[-10:][::-1]
    text = "📋 Последние 10 заявок:\n\n"
    for app in recent:
        status_emoji = {"accepted": "✅", "rejected": "❌", "pending": "⏳"}.get(app["status"], "❓")
        text += f"{status_emoji} *{app['nick']}* (ID: {app['id'][:8]})\n"
        text += f"   Возраст: {app['age']}\n"
        text += f"   Статус: {app['status']}\n"
        text += f"   Дата: {datetime.fromisoformat(app['created_at']).strftime('%d.%m.%Y %H:%M')}\n\n"
    
    await message.answer(text, parse_mode="Markdown")

async def main():
    if not os.path.exists(APPLICATIONS_FILE):
        with open(APPLICATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    
    print("✅ Бот для сервера Elysium запущен!")
    print(f"👤 Админ: {ADMIN_ID}")
    print(f"💬 Чат: {CHAT_LINK}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())