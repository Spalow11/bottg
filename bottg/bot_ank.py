import asyncio
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from mcipc.rcon import Client

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.environ.get("8726993851:AAEhvlW38fO1bbuUPgGn_YPzjFTLciGnL40")

ADMIN_ID = 6313154469
CHAT_LINK = "https://t.me/elysiumchatick"
PAYMENT_LINK = "https://www.donationalerts.com/r/spalow1"

# ========== RCON НАСТРОЙКИ (ЗАМЕНИ НА СВОИ) ==========
RCON_HOST = "nyx.minecraft-hosting.net:25831"           # IP твоего Minecraft сервера
RCON_PORT = 25575                  # Порт из server.properties
RCON_PASSWORD = "spalow123123"      # Пароль из server.properties
# =====================================================

# Информация о сервере
ABOUT_SERVER = """
🏰 О сервере Elysium

✨ Особенности:
• Приватный сервер с дружным комьюнити
• Уникальная экономика и кастомные предметы
• Регулярные ивенты и конкурсы
• Активная администрация

🎮 Версия: 1.20.4
🌍 IP: elysium.minecraft.ru

Присоединяйся к нам и стань частью нашего мира! 🚀
"""

# ПОЛНАЯ СИСТЕМА ДОНАТОВ
DONATIONS = {
    "gold_month": {
        "name": "💛 Золотая спонсорка (Месяц)",
        "description": "▸ Анимированный префикс [✨ Золотой ✨]\n▸ Скрытие себя с онлайн-карты\n▸ /co i (режим инспектора, без rollback)",
        "price": "249 ₽",
        "type": "месяц",
        "link": "https://www.donationalerts.com/r/spalow1?amount=249"
    },
    "gold_forever": {
        "name": "💛 Золотая спонсорка (Навсегда)",
        "description": "▸ Анимированный префикс [✨ Золотой ✨]\n▸ Скрытие себя с онлайн-карты\n▸ /co i (режим инспектора, без rollback)",
        "price": "1 290 ₽",
        "type": "навсегда",
        "link": "https://www.donationalerts.com/r/spalow1?amount=1290"
    },
    "diamond_month": {
        "name": "💎 Алмазная спонсорка (Месяц)",
        "description": "▸ Анимированный префикс [💎 Алмазный 💎]\n▸ Скрытие себя + животных с карты\n▸ /co i\n▸ Значок спонсора в табе 💎\n▸ Слабая синяя аура сияния\n▸ /hat\n▸ Скидка 10% на ремонт\n▸ Роль в Discord + отдельный канал",
        "price": "399 ₽",
        "type": "месяц",
        "link": "https://www.donationalerts.com/r/spalow1?amount=399"
    },
    "diamond_forever": {
        "name": "💎 Алмазная спонсорка (Навсегда)",
        "description": "▸ Анимированный префикс [💎 Алмазный 💎]\n▸ Скрытие себя + животных с карты\n▸ /co i\n▸ Значок спонсора в табе 💎\n▸ Слабая синяя аура сияния\n▸ /hat\n▸ Скидка 10% на ремонт\n▸ Роль в Discord + отдельный канал",
        "price": "2 190 ₽",
        "type": "навсегда",
        "link": "https://www.donationalerts.com/r/spalow1?amount=2190"
    },
    "emerald_month": {
        "name": "💚 Изумрудная спонсорка (Месяц)",
        "description": "▸ Анимированный префикс [🌿 Изумрудный 🌿]\n▸ Значок спонсора в табе ✨\n▸ Аура сияния (усиленная)\n▸ Скрытие себя + животных + маркеров\n▸ /dynmap hide/show\n▸ /co i /hat /workbench\n▸ Скидка 35% на ремонт\n▸ Магнит на опыт (15 блоков)\n▸ Автосбор дропа (10 блоков)\n▸ Разноцветный текст в чате\n▸ 1 кастомный напиток\n▸ Тотем с вашим скином",
        "price": "699 ₽",
        "type": "месяц",
        "link": "https://www.donationalerts.com/r/spalow1?amount=699"
    },
    "emerald_forever": {
        "name": "💚 Изумрудная спонсорка (Навсегда)",
        "description": "▸ Анимированный префикс [🌿 Изумрудный 🌿]\n▸ Значок спонсора в табе ✨\n▸ Аура сияния (усиленная)\n▸ Скрытие себя + животных + маркеров\n▸ /dynmap hide/show\n▸ /co i /hat /workbench\n▸ Скидка 35% на ремонт\n▸ Магнит на опыт (15 блоков)\n▸ Автосбор дропа (10 блоков)\n▸ Разноцветный текст в чате\n▸ 1 кастомный напиток\n▸ Тотем с вашим скином",
        "price": "3 890 ₽",
        "type": "навсегда",
        "link": "https://www.donationalerts.com/r/spalow1?amount=3890"
    },
    "netherite_month": {
        "name": "🖤 Незеритовая спонсорка (Месяц)",
        "description": "▸ Анимированный префикс [⚡ Незеритовый ⚡]\n▸ Свой значок в табе\n▸ Аура сияния\n▸ Абсолютное скрытие с карты\n▸ /co i /hat /workbench\n▸ Бесплатный ремонт\n▸ Магнит на опыт (25 блоков)\n▸ Автосбор дропа (15 блоков)\n▸ Разноцветный текст в чате\n▸ 10 напитков\n▸ Тотем + статуя\n▸ Свой префикс\n▸ Свой эмодзи в Discord\n▸ Мут игрока/в Discord\n▸ Доступ в правительственный чат\n▸ Твинк-аккаунт",
        "price": "999 ₽",
        "type": "месяц",
        "link": "https://www.donationalerts.com/r/spalow1?amount=999"
    },
    "netherite_forever": {
        "name": "🖤 Незеритовая спонсорка (Навсегда)",
        "description": "▸ Анимированный префикс [⚡ Незеритовый ⚡]\n▸ Свой значок в табе\n▸ Аура сияния\n▸ Абсолютное скрытие с карты\n▸ /co i /hat /workbench\n▸ Бесплатный ремонт\n▸ Магнит на опыт (25 блоков)\n▸ Автосбор дропа (15 блоков)\n▸ Разноцветный текст в чате\n▸ 10 напитков\n▸ Тотем + статуя\n▸ Свой префикс\n▸ Свой эмодзи в Discord\n▸ Мут игрока/в Discord\n▸ Доступ в правительственный чат\n▸ Твинк-аккаунт",
        "price": "6 990 ₽",
        "type": "навсегда",
        "link": "https://www.donationalerts.com/r/spalow1?amount=6990"
    },
    "rollback": {
        "name": "🔄 Откат ресурсов",
        "description": "▸ Администратор откатывает блоки в радиусе до 50 блоков\n▸ Период отката — до 7 дней назад",
        "price": "50 ₽",
        "type": "разово",
        "link": "https://www.donationalerts.com/r/spalow1?amount=50"
    },
    "unban_1": {
        "name": "🔓 Разбан (1-й раз)",
        "description": "Первый разбан на сервере",
        "price": "200 ₽",
        "type": "разбан",
        "link": "https://www.donationalerts.com/r/spalow1?amount=200"
    },
    "unban_2": {
        "name": "🔓 Разбан (2-й раз)",
        "description": "Второй разбан на сервере",
        "price": "300 ₽",
        "type": "разбан",
        "link": "https://www.donationalerts.com/r/spalow1?amount=300"
    },
    "unban_3": {
        "name": "🔓 Разбан (3-й раз)",
        "description": "Третий разбан на сервере",
        "price": "400 ₽",
        "type": "разбан",
        "link": "https://www.donationalerts.com/r/spalow1?amount=400"
    },
    "unban_4": {
        "name": "🔓 Разбан (4-й раз)",
        "description": "Четвертый разбан на сервере",
        "price": "500 ₽",
        "type": "разбан",
        "link": "https://www.donationalerts.com/r/spalow1?amount=500"
    },
    "all_included": {
        "name": "👑 ПАКЕТ «ВСЁ ВКЛЮЧЕНО»",
        "description": "▸ Все спонсорки навсегда\n▸ 10 откатов ресурсов\n▸ 1 бесплатный разбан\n▸ Роль в Discord\n▸ Имя в Зале Славы\n▸ Приоритет в поддержке\n\nЭкономия: 3 070 ₽",
        "price": "11 990 ₽",
        "type": "навсегда",
        "link": "https://www.donationalerts.com/r/spalow1?amount=11990"
    }
}
# ================================

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

APPLICATIONS_FILE = "applications.json"

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏰 О сервере")],
            [KeyboardButton(text="📝 Заявка")],
            [KeyboardButton(text="💎 Донат")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_donations_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💛 Золотая (Месяц) - 249₽", callback_data="donate_gold_month")],
        [InlineKeyboardButton(text="💛 Золотая (Навсегда) - 1 290₽", callback_data="donate_gold_forever")],
        [InlineKeyboardButton(text="💎 Алмазная (Месяц) - 399₽", callback_data="donate_diamond_month")],
        [InlineKeyboardButton(text="💎 Алмазная (Навсегда) - 2 190₽", callback_data="donate_diamond_forever")],
        [InlineKeyboardButton(text="💚 Изумрудная (Месяц) - 699₽", callback_data="donate_emerald_month")],
        [InlineKeyboardButton(text="💚 Изумрудная (Навсегда) - 3 890₽", callback_data="donate_emerald_forever")],
        [InlineKeyboardButton(text="🖤 Незеритовая (Месяц) - 999₽", callback_data="donate_netherite_month")],
        [InlineKeyboardButton(text="🖤 Незеритовая (Навсегда) - 6 990₽", callback_data="donate_netherite_forever")],
        [InlineKeyboardButton(text="🔄 Откат ресурсов - 50₽", callback_data="donate_rollback")],
        [InlineKeyboardButton(text="🔓 Разбан (1-й) - 200₽", callback_data="donate_unban_1")],
        [InlineKeyboardButton(text="🔓 Разбан (2-й) - 300₽", callback_data="donate_unban_2")],
        [InlineKeyboardButton(text="🔓 Разбан (3-й) - 400₽", callback_data="donate_unban_3")],
        [InlineKeyboardButton(text="🔓 Разбан (4-й) - 500₽", callback_data="donate_unban_4")],
        [InlineKeyboardButton(text="👑 ПАКЕТ «ВСЁ ВКЛЮЧЕНО» - 11 990₽", callback_data="donate_all_included")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
    ])
    return keyboard

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
        [InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_{user_id}_{app_id}")],
        [InlineKeyboardButton(text="📋 Посмотреть историю", callback_data=f"history_{user_id}")]
    ])

# ========== ФУНКЦИЯ RCON ДЛЯ ДОБАВЛЕНИЯ В ВАЙТЛИСТ ==========
async def add_to_whitelist(player_nickname: str) -> tuple:
    """
    Добавляет игрока в белый список Minecraft-сервера через RCON
    Возвращает (успех, сообщение)
    """
    try:
        # Используем asyncio.to_thread для синхронного RCON в асинхронном контексте
        def sync_add():
            with Client(RCON_HOST, RCON_PORT, passwd=RCON_PASSWORD) as client:
                response = client.run(f"whitelist add {player_nickname}")
                return response
        
        response = await asyncio.to_thread(sync_add)
        print(f"RCON ответ: {response}")
        return True, response
    except Exception as e:
        error_msg = str(e)
        print(f"Ошибка RCON: {error_msg}")
        return False, error_msg
# ============================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🎮 Добро пожаловать на сервер Elysium!\n\n"
        "Я помогу тебе подать заявку или узнать информацию о сервере.\n\n"
        "Используй кнопки ниже для навигации:",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "🏰 О сервере")
async def about_server(message: types.Message):
    await message.answer(ABOUT_SERVER, reply_markup=get_main_keyboard())

@dp.message(F.text == "📝 Заявка")
async def start_application(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📝 Подача заявки\n\n"
        "Чтобы подать заявку, заполните небольшую анкету.\n"
        "Введите ваш никнейм:",
        reply_markup=get_main_keyboard()
    )
    await state.set_state(Form.nick)

@dp.message(F.text == "💎 Донат")
async def show_donations(message: types.Message):
    text = (
        "💎 Поддержать сервер Elysium\n\n"
        "Выбери подходящий тебе донат-пакет:\n\n"
        "СПОНСОРКИ:\n"
        "💛 Золотая — 249₽/мес или 1 290₽ навсегда\n"
        "💎 Алмазная — 399₽/мес или 2 190₽ навсегда\n"
        "💚 Изумрудная — 699₽/мес или 3 890₽ навсегда\n"
        "🖤 Незеритовая — 999₽/мес или 6 990₽ навсегда\n\n"
        "ОТДЕЛЬНЫЕ УСЛУГИ:\n"
        "🔄 Откат ресурсов — 50₽\n"
        "🔓 Разбан — от 200₽\n\n"
        "ПАКЕТ «ВСЁ ВКЛЮЧЕНО» — 11 990₽\n"
        "(Экономия 3 070₽)\n\n"
        "Нажми на кнопку ниже, чтобы выбрать пакет:"
    )
    await message.answer(text, reply_markup=get_donations_keyboard())

@dp.callback_query(F.data.startswith("donate_"))
async def process_donation(callback: types.CallbackQuery):
    donate_key = callback.data.split("_", 1)[1]
    donate = DONATIONS.get(donate_key)
    
    if donate:
        emoji_map = {
            "gold": "💛", "diamond": "💎", "emerald": "💚",
            "netherite": "🖤", "rollback": "🔄", "unban": "🔓", "all_included": "👑"
        }
        emoji = "✨"
        for key, e in emoji_map.items():
            if key in donate_key:
                emoji = e
                break
        
        text = (
            f"{emoji} {donate['name']}\n\n"
            f"Что даёт:\n{donate['description']}\n\n"
            f"Цена: {donate['price']}\n"
            f"Тип: {donate['type']}\n\n"
            f"Нажми на кнопку ниже, чтобы перейти к оплате:"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💸 Оплатить {donate['price']}", url=donate['link'])],
            [InlineKeyboardButton(text="🔙 Назад к списку донатов", callback_data="back_to_donations")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.answer("Ошибка: пакет не найден")
    
    await callback.answer()

@dp.callback_query(F.data == "back_to_donations")
async def back_to_donations(callback: types.CallbackQuery):
    text = (
        "💎 Поддержать сервер Elysium\n\n"
        "Выбери подходящий тебе донат-пакет:\n\n"
        "СПОНСОРКИ:\n"
        "💛 Золотая — 249₽/мес или 1 290₽ навсегда\n"
        "💎 Алмазная — 399₽/мес или 2 190₽ навсегда\n"
        "💚 Изумрудная — 699₽/мес или 3 890₽ навсегда\n"
        "🖤 Незеритовая — 999₽/мес или 6 990₽ навсегда\n\n"
        "ОТДЕЛЬНЫЕ УСЛУГИ:\n"
        "🔄 Откат ресурсов — 50₽\n"
        "🔓 Разбан — от 200₽\n\n"
        "ПАКЕТ «ВСЁ ВКЛЮЧЕНО» — 11 990₽\n\n"
        "Нажми на кнопку ниже, чтобы выбрать пакет:"
    )
    await callback.message.edit_text(text, reply_markup=get_donations_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "🎮 Главное меню\n\nИспользуй кнопки ниже для навигации:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

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
        f"📊 Статистика заявок\n\n"
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
    text = "📋 Последние заявки:\n\n"
    for app in recent:
        status_emoji = {"accepted": "✅", "rejected": "❌", "pending": "⏳"}.get(app["status"], "❓")
        text += f"{status_emoji} {app['nick']} (ID: {app['id'][:8]})\n"
        text += f"   От: {app['username']}\n"
        text += f"   Статус: {app['status']}\n\n"
    
    await message.answer(text)

# Шаг 1: Ник
@dp.message(Form.nick)
async def get_nick(message: types.Message, state: FSMContext):
    await state.update_data(nick=message.text)
    await message.answer("📅 Укажите ваш возраст (только число):")
    await state.set_state(Form.age)

# Шаг 2: Возраст
@dp.message(Form.age)
async def get_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число (ваш возраст):")
        return
    await state.update_data(age=message.text)
    await message.answer("🔍 Откуда узнали о сервере? (реклама, друг, тикток и т.д.):")
    await state.set_state(Form.source)

# Шаг 3: Источник
@dp.message(Form.source)
async def get_source(message: types.Message, state: FSMContext):
    await state.update_data(source=message.text)
    await message.answer("🛠 Чем планируете заниматься на сервере? (строительство, PvP, фермы и т.д.):")
    await state.set_state(Form.plans)

# Шаг 4: Планы
@dp.message(Form.plans)
async def get_plans(message: types.Message, state: FSMContext):
    await state.update_data(plans=message.text)
    await message.answer("📝 Немного о себе (расскажите о своих интересах, опыте игры):")
    await state.set_state(Form.about)

# Шаг 5: О себе и сохранение заявки
@dp.message(Form.about)
async def get_about(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    data = await state.get_data()
    
    app_id = f"{message.from_user.id}_{datetime.now().timestamp()}"
    username = message.from_user.username or f"user_{message.from_user.id}"
    
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
        "Ожидайте ответа в этом чате.",
        reply_markup=get_main_keyboard()
    )
    await state.clear()

# ========== ОБРАБОТКА РЕШЕНИЯ АДМИНА (С RCON) ==========
@dp.callback_query(F.data.startswith("accept_"))
async def accept_user(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[1])
    app_id = parts[2]
    
    await callback.answer()
    
    # Получаем ник из сохранённой заявки
    applications = load_applications()
    application = None
    for app in applications:
        if app["id"] == app_id:
            application = app
            break
    
    nick = None
    if application:
        nick = application['nick']
        
        # Добавляем в вайтлист Minecraft через RCON
        success, response = await add_to_whitelist(nick)
        
        if success:
            await callback.message.answer(f"✅ Игрок {nick} добавлен в вайтлист сервера!")
        else:
            await callback.message.answer(f"❌ Ошибка RCON: {response}\nИгрок {nick} НЕ добавлен в вайтлист. Проверь настройки.")
    
    # Обновляем статус в файле
    update_application_status(app_id, "accepted")
    
    # Отправляем сообщение игроку
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
            f"Но вы можете приобрести проходку на сервер:\n"
            f"👉 {PAYMENT_LINK}\n\n"
            f"После оплаты вы сразу получите доступ."
        )
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ Решение: ОТКАЗАНО"
        )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {e}")

@dp.callback_query(F.data.startswith("history_"))
async def show_user_history(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await callback.answer()
    
    applications = load_applications()
    user_apps = [app for app in applications if app["user_id"] == user_id]
    
    if not user_apps:
        await callback.message.answer("📭 У этого пользователя нет заявок.")
        return
    
    text = f"📋 История заявок пользователя ID {user_id}:\n\n"
    for app in user_apps[-5:]:
        status_emoji = {"accepted": "✅", "rejected": "❌", "pending": "⏳"}.get(app["status"], "❓")
        created = datetime.fromisoformat(app["created_at"]).strftime("%d.%m.%Y %H:%M")
        text += f"{status_emoji} {app['nick']} ({app['age']} лет)\n"
        text += f"   📅 {created}\n"
        text += f"   Статус: {app['status']}\n\n"
    
    await callback.message.answer(text)

async def main():
    if not os.path.exists(APPLICATIONS_FILE):
        with open(APPLICATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    
    print("✅ Бот для сервера Elysium запущен!")
    print(f"👤 Админ: {ADMIN_ID}")
    print(f"💬 Чат: {CHAT_LINK}")
    print(f"🔌 RCON: {RCON_HOST}:{RCON_PORT}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
