import logging
import os
from datetime import timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import ChatTypeFilter
from aiogram.types import ChatPermissions
from aiogram.exceptions import TelegramAPIError
from aiogram.utils.chat_action import ChatAction
from aiogram import F

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("moderation")

async def guard_external_reply(message: types.Message):
    if not message:
        return

    user = message.from_user
    chat = message.chat
    d = message.to_python()
    ext = d.get("external_reply")
    if not (ext and ext.get("origin", {}).get("type") == "channel"):
        return

    origin_chat = ext.get("chat", {}) or ext.get("origin", {}).get("chat", {})
    origin_title = origin_chat.get("title", "❓")
    origin_username = origin_chat.get("username", "")

    log.info(
        f"\n================= 🚨 DETECTED 🚨 =================\n"
        f"📌 Чат: {chat.title} (ID: {chat.id})\n"
        f"👤 Пользователь: {user.full_name} @{user.username or '—'} (ID: {user.id})\n"
        f"💬 Сообщение ID: {message.message_id}\n"
        f"↪️ Репост из канала: {origin_title} @{origin_username or '—'}\n"
        "================================================="
    )

    try:
        member = await chat.get_member(user.id)
        if member.is_chat_admin():
            log.info("⚠️ Отправитель админ — пропускаем.")
            return
    except TelegramAPIError as e:
        log.error(f"❌ Ошибка при проверке статуса пользователя: {e}")
        return

    try:
        me = await chat.get_member(message.bot.id)
        can_delete = getattr(me, "can_delete_messages", False)
        can_restrict = getattr(me, "can_restrict_members", False)
        if not can_delete or not can_restrict:
            log.error("❗️У бота нет прав (Delete/Restrict).")
            return
    except TelegramAPIError as e:
        log.error(f"❌ Ошибка при проверке прав бота: {e}")
        return

    full_mute = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
        can_change_info=False,
        can_invite_users=False,
        can_pin_messages=False
    )

    try:
        until = message.date + timedelta(hours=1)
        await message.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=user.id,
            permissions=full_mute,
            until_date=until
        )
        log.info(f"🔇 Пользователю {user.id} выдан ПОЛНЫЙ мут на 1 час")

        await message.delete()
        log.info(f"🗑 Сообщение {message.message_id} удалено")
        log.info("✅ Обработка завершена\n")

    except TelegramAPIError as e:
        log.error(f"❌ Ошибка при муте/удалении: {e}")

async def main():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN не задан в переменных окружения!")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot)

    # Фильтруем только группы
    dp.message.register(guard_external_reply, ChatTypeFilter(types.ChatType.GROUP))

    log.info("✅ Бот запущен и слушает группы")
    await dp.start_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
