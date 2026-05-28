import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

# ============================ НАСТРОЙКИ ============================

TOKEN = os.getenv("BOT_TOKEN")

# Два админа. Впиши сюда свои реальные Telegram ID (узнать можно у @userinfobot)
ADMINS = [
    6378471773,   # <-- ID первого админа (тебя)
    5708284946,   # <-- ID второго админа
]

# Название бота, для которого работает поддержка
TARGET_BOT = "@manhwcardbot"

# ============================ ИНИЦИАЛИЗАЦИЯ ============================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Карта связей: (chat_id_админа, id_скопированного_сообщения) -> id_пользователя
# Нужна, чтобы понять, кому именно отвечает админ реплаем.
reply_map: dict[tuple[int, int], int] = {}

# ============================ ТЕКСТЫ ============================

GREETING = (
    "👋 <b>Привет! Добро пожаловать в техподдержку</b> {bot}\n\n"
    "Я — твой прямой канал связи с командой. Если в боте {bot} что-то "
    "пошло не так, возникли вопросы, баги или есть идеи — просто напиши сюда. 🛠️\n\n"
    "📩 <b>Как это работает:</b>\n"
    "1️⃣ Опиши проблему максимально подробно\n"
    "2️⃣ Можешь приложить скриншот, видео или файл\n"
    "3️⃣ Дождись ответа — мы свяжемся с тобой прямо здесь\n\n"
    "✨ Мы читаем каждое обращение и постараемся помочь как можно быстрее.\n\n"
    "<i>Пиши прямо сейчас — мы на связи!</i> 💬"
).format(bot=TARGET_BOT)

ADMIN_GREETING = (
    "🛡️ <b>Админ-панель поддержки для брадков</b>\n\n"
    "Ты реальный брад, хахаха бля лан. Сюда будут приходить сообщения от рапов.\n\n"
    "📌 <b>Делай так чтоб ответить:</b>\n"
    "• Свайпни сообщение пользователя (или нажми «Ответить»)\n"
    "• Напиши ответ, он автоматически уйдёт рапу\n"
    "• Можно отвечать текстом, фото, видео, файлами, та и ваще всо можна\n\n"
    "Всё просто брадик. Жди обращений 👇"
).format(bot=TARGET_BOT)

USER_SENT = "✅ <b>Сообщение отправлено в поддержку!</b>\nМы ответим тебе прямо здесь. Ожидай ⏳"

# ============================ ХЭНДЛЕРЫ ============================

@router.message(CommandStart())
async def cmd_start(message: Message):
    if message.from_user.id in ADMINS:
        await message.answer(ADMIN_GREETING)
    else:
        await message.answer(GREETING)

@router.message(Command("help"))
async def cmd_help(message: Message):
    if message.from_user.id in ADMINS:
        await message.answer(ADMIN_GREETING)
    else:
        await message.answer(GREETING)

# --- Ответ администратора (реплай на сообщение пользователя) ---
@router.message(F.from_user.id.in_(ADMINS), F.reply_to_message)
async def admin_reply(message: Message):
    key = (message.chat.id, message.reply_to_message.message_id)
    user_id = reply_map.get(key)

    if user_id is None:
        await message.reply(
            "⚠️ Не могу определить пользователя.\n"
            "Отвечай реплаем именно на пересланное сообщение пользователя."
        )
        return
    try:
        await message.copy_to(chat_id=user_id)
        await message.reply("✅ Ответ отправлен пользователю.")
    except Exception as e:
        await message.reply(f"❌ Не удалось отправить ответ.\nВозможно, пользователь заблокировал бота.\n\n<code>{e}</code>")
# --- Сообщение от админа без реплая (подсказка) ---
@router.message(F.from_user.id.in_(ADMINS))
async def admin_no_reply(message: Message):
    await message.answer(
        "ℹ️ Чтобы ответить пользователю — <b>свайпни его сообщение</b> "
        "(нажми «Ответить») и напиши ответ."
    )

# --- Сообщение от обычного пользователя ---
@router.message(F.chat.type == "private")
async def user_message(message: Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "—"

    header = (
        "📨 <b>Новое обращение в поддержку</b>\n\n"
        f"👤 <b>Имя:</b> {user.full_name}\n"
        f"🔗 <b>Username:</b> {username}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n\n"
        "↩️ <i>Ответь реплаем на сообщение ниже, чтобы написать пользователю.</i>"
    )

    delivered = False
    for admin_id in ADMINS:
        try:
            await bot.send_message(admin_id, header)
            copied = await message.copy_to(chat_id=admin_id)
            reply_map[(admin_id, copied.message_id)] = user.id
            delivered = True
        except Exception as e:
            logging.warning(f"Не удалось доставить сообщение админу {admin_id}: {e}")

    if delivered:
        await message.answer(USER_SENT)
    else:
        await message.answer("⚠️ Не удалось доставить сообщение. Попробуй позже.")

# ============================ ЗАПУСК ============================

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
