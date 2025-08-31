import logging
import os
from datetime import timedelta
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ----- ЛОГИ -----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("moderation")


async def guard_external_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return

    chat = msg.chat
    user = msg.from_user
    d = msg.to_dict()

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
        if member.status in ("administrator", "creator"):
            log.info("⚠️ Отправитель админ — пропускаем.")
            return
    except TelegramError as e:
        log.error(f"❌ Ошибка при проверке статуса пользователя: {e}")
        return

    # Проверка прав бота
    try:
        me = await chat.get_member(context.bot.id)
        can_delete = getattr(me, "can_delete_messages", None)
        can_restrict = getattr(me, "can_restrict_members", None)
        if hasattr(me, "privileges") and me.privileges:
            can_delete = can_delete or me.privileges.can_delete_messages
            can_restrict = can_restrict or me.privileges.can_restrict_members

        if not can_delete or not can_restrict:
            log.error("❗️У бота нет прав (Delete/Restrict).")
            return
    except TelegramError as e:
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
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=user.id,
            permissions=full_mute,
            until_date=until
        )
        log.info(f"🔇 Пользователю {user.id} выдан ПОЛНЫЙ мут на 1 час")

        await msg.delete()
        log.info(f"🗑 Сообщение {msg.message_id} удалено")
        log.info("✅ Обработка завершена\n")

    except TelegramError as e:
        log.error(f"❌ Ошибка при муте/удалении: {e}")


async def main():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN не задан в переменных окружения!")
        return

    # Создаем приложение (новый синтаксис)
    app = Application.builder().token(BOT_TOKEN).build()

    # Добавляем хендлер на сообщения в группах
    app.add_handler(
        MessageHandler(filters.ChatType.GROUPS & filters.ALL, guard_external_reply)
    )

    log.info("✅ Бот запущен и слушает группы")
    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
