
import logging
import sqlite3
import os

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= НАСТРОЙКИ =================

BOT_TOKEN = os.getenv("BOT_TOKEN", "9187444592:AAFjbwPjET4hAK8CEp8UlWJw7CUYy45ZvTU")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6313154469"))

CHANNEL = "@elysiumvanila"
CHANNEL_URL = "https://t.me/elysiumvanila"
GROUP_URL = "https://t.me/+B5tj8rpwYVZiY2My"
DONATE_URL = "https://www.donationalerts.com/r/spalow1"

SERVER_IP = "elysium.mc-join.me"
SERVER_VERSION = "26.1.2"
PASS_PRICE = "50 ₽"

DB_NAME = "applications.db"

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ================= БАЗА ДАННЫХ =================


def init_db():
    with sqlite3.connect(DB_NAME) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                answers TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            )
        """)


# ================= ВОПРОСЫ =================

QUESTIONS = [
    "🎮 **Какой у тебя ник в Minecraft?**",
    "🎂 **Сколько тебе лет?**",
    "📢 **Откуда ты узнал о сервере ELYSIUM?**",
    "📜 **Ты ознакомился с правилами сервера?**",
    "🌌 **Почему ты хочешь играть именно на ELYSIUM?**",
]

RULES_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✅ Да", callback_data="rules_yes"),
        InlineKeyboardButton("❌ Нет", callback_data="rules_no"),
    ]
])


# ================= ПОДПИСКА =================


async def is_subscribed(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )
    except Exception:
        logger.exception("Не удалось проверить подписку")
        return False


def subscription_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "📢 Подписаться на канал",
            url=CHANNEL_URL
        )],
        [InlineKeyboardButton(
            "🔄 Проверить подписку",
            callback_data="check_subscription"
        )],
    ])


# ================= СТАРТ =================


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    context.user_data.clear()

    await update.message.reply_text(
        "🌌 **ELYSIUM — заявка на сервер**\n\n"
        "Добро пожаловать!\n"
        "Чтобы попасть на сервер, заполни небольшую анкету.\n\n"
        "Сначала подпишись на наш Telegram-канал:",
        reply_markup=subscription_keyboard(),
        parse_mode="Markdown",
    )


async def check_subscription(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    if not await is_subscribed(
        context.bot, query.from_user.id
    ):
        await query.message.reply_text(
            "❌ Подписка не найдена.\n"
            "Подпишись на канал и нажми проверку ещё раз.",
            reply_markup=subscription_keyboard(),
        )
        return

    await query.message.reply_text(
        "✅ Подписка подтверждена!\n\n"
        "Начинаем заполнение анкеты.\n"
        "Отвечай на вопросы по очереди.\n\n"
        + QUESTIONS[0],
        parse_mode="Markdown",
    )

    context.user_data["answers"] = []
    context.user_data["question"] = 0
    context.user_data["stage"] = "answer"


# ================= ОТВЕТЫ =================


async def handle_answer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    text = update.message.text.strip()

    if context.user_data.get("stage") != "answer":
        await update.message.reply_text(
            "Нажми /start, чтобы начать заполнение анкеты."
        )
        return

    index = context.user_data["question"]

    if not text:
        await update.message.reply_text(
            "Пожалуйста, введи ответ текстом."
        )
        return

    if index == 0 and len(text) > 32:
        await update.message.reply_text(
            "Ник слишком длинный. Введи ник Minecraft ещё раз."
        )
        return

    if index == 1:
        try:
            age = int(text)
            if not 1 <= age <= 99:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "Укажи возраст числом."
            )
            return

    context.user_data["answers"].append(text)
    index += 1

    if index < len(QUESTIONS):
        context.user_data["question"] = index

        if index == 3:
            await update.message.reply_text(
                QUESTIONS[index],
                reply_markup=RULES_KEYBOARD,
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            QUESTIONS[index],
            parse_mode="Markdown",
        )
        return

    await submit_application(update, context)


async def rules_answer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    if context.user_data.get("stage") != "answer":
        await query.message.reply_text(
            "Эта анкета уже не активна. Нажми /start."
        )
        return

    choice = query.data

    if choice == "rules_no":
        await query.message.reply_text(
            "Сначала ознакомься с правилами сервера. "
            "После этого можешь начать анкету заново: /start"
        )
        context.user_data.clear()
        return

    context.user_data["answers"].append("Да, ознакомился")
    context.user_data["question"] = 4

    await query.message.reply_text(
        QUESTIONS[4],
        parse_mode="Markdown",
    )


# ================= ОТПРАВКА ЗАЯВКИ =================


async def submit_application(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    answers = context.user_data.get("answers", [])

    if len(answers) != len(QUESTIONS):
        await update.effective_message.reply_text(
            "Анкета заполнена не полностью. Нажми /start."
        )
        return

    username = (
        f"@{user.username}" if user.username
        else "Нет username"
    )

    with sqlite3.connect(DB_NAME) as db:
        cursor = db.execute(
            """
            INSERT INTO applications
            (user_id, username, answers, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (user.id, username, "\n".join(answers)),
        )
        app_id = cursor.lastrowid

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Одобрить",
                callback_data=f"approve:{app_id}",
            ),
            InlineKeyboardButton(
                "❌ Отказать",
                callback_data=f"reject:{app_id}",
            ),
        ]
    ])

    admin_text = (
        f"📩 НОВАЯ ЗАЯВКА ELYSIUM №{app_id}\n\n"
        f"👤 Telegram: {username}\n"
        f"🆔 Telegram ID: {user.id}\n"
        f"🔗 Профиль: tg://user?id={user.id}\n\n"
        f"🎮 Ник Minecraft: {answers[0]}\n"
        f"🎂 Возраст: {answers[1]}\n"
        f"📢 Источник: {answers[2]}\n"
        f"📜 Правила: {answers[3]}\n"
        f"🌌 Почему ELYSIUM: {answers[4]}\n"
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=keyboard,
        )
    except Exception:
        logger.exception("Не удалось отправить заявку админу")
        with sqlite3.connect(DB_NAME) as db:
            db.execute(
                "UPDATE applications SET status='delivery_error' WHERE id=?",
                (app_id,),
            )
        await update.effective_message.reply_text(
            "Не удалось передать заявку администрации. "
            "Попробуй позже через /start."
        )
        context.user_data.clear()
        return

    context.user_data.clear()

    await update.effective_message.reply_text(
        "🎉 Анкета успешно отправлена!\n\n"
        "Администрация рассмотрит её и пришлёт ответ сюда.\n"
        "Пока ожидаешь, можешь оставаться на связи с ELYSIUM."
    )


# ================= РЕШЕНИЕ АДМИНА =================


async def review_application(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "У тебя нет прав для этого действия.",
            show_alert=True,
        )
        return

    await query.answer()

    action, app_id_text = query.data.split(":")
    app_id = int(app_id_text)

    with sqlite3.connect(DB_NAME) as db:
        row = db.execute(
            """
            SELECT user_id, status
            FROM applications WHERE id=?
            """,
            (app_id,),
        ).fetchone()

        if row is None:
            await query.message.reply_text(
                "Заявка не найдена в базе."
            )
            return

        user_id, status = row

        if status != "pending":
            await query.message.reply_text(
                f"Заявка уже обработана: {status}"
            )
            return

        new_status = (
            "approved" if action == "approve" else "rejected"
        )

        db.execute(
            "UPDATE applications SET status=? WHERE id=?",
            (new_status, app_id),
        )

    if action == "approve":
        message = (
            "🎉 **Твоя заявка на ELYSIUM одобрена!**\n\n"
            "Добро пожаловать на сервер!\n\n"
            f"🎮 IP: `{SERVER_IP}`\n"
            f"🧩 Версия: `{SERVER_VERSION}`\n\n"
            f"💬 Вступай в чат: {GROUP_URL}\n\n"
            "Удачной игры!"
        )
    else:
        message = (
            "К сожалению, твоя заявка на ELYSIUM отклонена.\n\n"
            f"Стоимость проходки — {PASS_PRICE}.\n"
            "Если хочешь поддержать сервер и узнать о "
            "возможности приобретения проходки, перейди сюда:\n"
            f"{DONATE_URL}"
        )

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except Exception:
        logger.exception(
            "Не удалось сообщить решение пользователю %s",
            user_id,
        )
        await query.message.reply_text(
            "Решение сохранено, но бот не смог написать игроку. "
            "Возможно, он не запускал бота или заблокировал его."
        )
        return

    await query.edit_message_reply_markup(
        reply_markup=None
    )

    await query.message.reply_text(
        f"✅ Заявка №{app_id}: "
        f"{'одобрена' if action == 'approve' else 'отклонена'}."
    )


# ================= ЗАПУСК =================


def main():
    if BOT_TOKEN == "ВСТАВЬ_ТОКЕН_ОТ_BOTFATHER":
        raise RuntimeError(
            "Вставь токен бота в BOT_TOKEN."
        )

    if ADMIN_ID == 123456789:
        raise RuntimeError(
            "Укажи свой Telegram ID в ADMIN_ID."
        )

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        CallbackQueryHandler(
            check_subscription,
            pattern="^check_subscription$",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            rules_answer,
            pattern="^rules_(yes|no)$",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            review_application,
            pattern="^(approve|reject):\\d+$",
        )
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_answer,
        )
    )

    print("ELYSIUM Bot запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
