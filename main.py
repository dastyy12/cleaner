import logging
import os
from datetime import timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatPermissions, Message, ChatMemberOwner, ChatMemberAdministrator
from aiogram.exceptions import TelegramBadRequest
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("moderation")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()  # В aiogram 3.x диспетчер без аргументов

@dp.startup()
async def on_startup():
    log.info("✅ Dispatcher готов")

@dp.message()
async def guard_external_reply(msg: Message):
    if not msg or msg.chat.type not in ["group", "supergroup"]:
        return

    chat = msg.chat
    user = msg.from_user
    d = msg.model_dump()  # безопасно для Pydantic V2

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
        f"💬 Сообщение ID: {msg.message_id}\n"
        f"↪️ Репост из канала: {origin_title} @{origin_username or '—'}\n"
        "================================================="
    )

    try:
        member = await chat.get_member(user.id)
        if isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
            log.info("⚠️ Отправитель админ/создатель — пропускаем.")
            return
    except TelegramBadRequest as e:
        log.error(f"❌ Ошибка при проверке статуса пользователя: {e}")
        return

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
        await bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=user.id,
            permissions=full_mute,
            until_date=until
        )
        log.info(f"🔇 Пользователю {user.id} выдан ПОЛНЫЙ мут на 1 час")
        await msg.delete()
        log.info(f"🗑 Сообщение {msg.message_id} удалено")
    except TelegramBadRequest as e:
        log.error(f"❌ Ошибка при муте/удалении: {e}")

async def main():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN не задан в переменных окружения!")
        return
    log.info("✅ Бот запущен и слушает группы")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

