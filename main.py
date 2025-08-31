import logging
import os
from datetime import timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatPermissions
from aiogram.filters import BaseFilter
from aiogram.types.message import ContentType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message
from aiogram.types import ChatType
from aiogram.types import Message as Msg
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import CallbackQuery
from aiogram import F
from aiogram.dispatcher.filters import Command
from aiogram.utils import executor

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ----- ЛОГИ -----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("moderation")

# --- Фильтр на группы для Aiogram 3.x ---
class IsGroup(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.chat.type in [types.ChatType.GROUP, types.ChatType.SUPERGROUP]


async def guard_external_reply(message: Message):
    msg = message
    if not msg:
        return

    chat = msg.chat
    user = msg.from_user
    d = msg.to_python()  # Для Aiogram 3.x

    # Проверяем external_reply из канала
    ext = d.get("external_reply")
    if not (ext and ext.get("origin", {}).get("type") == "channel"):
        return

    origin_chat = ext.get("chat", {}) or ext.get("origin", {}).get("chat", {})
    origin_title = origin_chat.get("title", "❓")
    origin_username = origin_chat.get("username", "")

    log.info(
        f"\n================= 🚨 DETECTED 🚨 =================\n"
        f"📌 Чат: {chat.title} (ID: {chat.id})\n"
        f"👤 Пользователь: {user.first_name} @{user.username or '—'} (ID: {user.id})\n"
        f"💬 Сообщение ID: {msg.message_id}\n"
        f"↪️ Репост из канала: {origin_title} @{origin_username or '—'}\n"
        "================================================="
    )

    # Проверка: не админ ли
    try:
        member = await chat.get_member(user.id)
        if member.is_chat_admin() or member.is_chat_creator():
            log.info("⚠️ Отправитель админ — пропускаем.")
            return
    except Exception as e:
        log.error(f"❌ Ошибка при проверке статуса пользователя: {e}")
        return

    # Проверка прав бота
    try:
        me = await chat.get_member((await bot.get_me()).id)
        can_delete = getattr(me, "can_delete_messages", None)
        can_restrict = getattr(me, "can_restrict_members", None)

        if not can_delete or not can_restrict:
            log.error("❗️У бота нет прав (Delete/Restrict).")
            return
    except Exception as e:
        log.error(f"❌ Ошибка при проверке прав бота: {e}")
        return

    # --- Полный мут (запрет вообще на всё)
    full_mute = ChatPermissions(
        can_send_messages=False,
        can_send_audios=False,
        can_send_documents=False,
        can_send_photos=False,
        can_send_videos=False,
        can_send_video_notes=False,
        can_send_voice_notes=False,
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
        await chat.restrict(user.id, permissions=full_mute, until_date=until)
        log.info(f"🔇 Пользователю {user.id} выдан ПОЛНЫЙ мут на 1 час")

        await msg.delete()
        log.info(f"🗑 Сообщение {msg.message_id} удалено")
        log.info("✅ Обработка завершена\n")

    except Exception as e:
        log.error(f"❌ Ошибка при муте/удалении: {e}")


async def main():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN не задан в переменных окружения!")
        return

    global bot
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Добавляем хендлер на сообщения в группах
    dp.message.register(guard_external_reply, IsGroup())

    log.info("✅ Бот запущен и слушает группы")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
