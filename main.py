import logging
import os
from datetime import timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatPermissions, Message
from aiogram.exceptions import TelegramBadRequest
from dotenv import load_dotenv
import asyncio

# Загружаем токен из .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("moderation")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Стартовый хэндлер
@dp.startup()
async def on_startup():
    log.info("✅ Dispatcher готов")

# Основной хэндлер для репостов
@dp.message()
async def guard_external_reply(msg: Message):
    if not msg or msg.chat.type not in ["group", "supergroup"]:
        return

    # Проверка репоста из канала
    ext = getattr(msg, "external_reply", None)
    if not (ext and getattr(ext.origin, "type", None) == "channel"):
        return

    origin_chat = getattr(ext, "chat", {}) or getattr(ext.origin, "chat", {})
    origin_title = getattr(origin_chat, "title", "❓")
    origin_username = getattr(origin_chat, "username", "—")

    user = msg.from_user
    chat = msg.chat

    log.info(
        f"\n================= 🚨 DETECTED 🚨 =================\n"
        f"📌 Чат: {chat.title} (ID: {chat.id})\n"
        f"👤 Пользователь: {user.full_name} @{user.username or '—'} (ID: {user.id})\n"
        f"💬 Сообщение ID: {msg.message_id}\n"
        f"↪️ Репост из канала: {origin_title} @{origin_username}\n"
        "================================================="
    )

    # Проверка статуса пользователя
    try:
        member = await chat.get_member(user.id)
        if hasattr(member, "status") and member.status in ["administrator", "creator"]:
            log.info("⚠️ Отправитель админ — пропускаем.")
            return
    except TelegramBadRequest as e:
        log.error(f"❌ Ошибка при проверке статуса пользователя: {e}")
        return

    # Проверка прав бота
    try:
        me = await chat.get_member(bot.id)
        can_delete = getattr(me, "can_delete_messages", False)
        can_restrict = getattr(me, "can_restrict_members", False)
        if hasattr(me, "privileges") and me.privileges:
            can_delete = can_delete or me.privileges.can_delete_messages
            can_restrict = can_restrict or me.privileges.can_restrict_members
        if not can_delete or not can_restrict:
            log.error("❗️У бота нет прав (Delete/Restrict).")
            return
    except TelegramBadRequest as e:
        log.error(f"❌ Ошибка при проверке прав бота: {e}")
        return

    # Полный мут
    full_mute = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
        can_change_info=False,
        can_invite_users=False,
        can_pin_messages=False,
        can_manage_topics=False
    )

    try:
        until = msg.date + timedelta(hours=1)
        await bot.restrict_chat_member(chat.id, user.id, permissions=full_mute, until_date=until)
        log.info(f"🔇 Пользователю {user.id} выдан ПОЛНЫЙ мут на 1 час")
        await msg.delete()
        log.info(f"🗑 Сообщение {msg.message_id} удалено")
    except TelegramBadRequest as e:
        log.error(f"❌ Ошибка при муте/удалении: {e}")

# Главная функция
async def main():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN не задан в переменных окружения!")
        return
    log.info("✅ Бот запущен и слушает группы")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
