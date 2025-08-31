import logging
import os
from datetime import timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatPermissions
from aiogram.utils import executor
from aiogram.dispatcher.filters import ChatTypeFilter
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не задан в переменных окружения!")

# Логи
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("moderation")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Функция обработки сообщений ---
@dp.message_handler(ChatTypeFilter(chat_type=["group", "supergroup"]))
async def guard_external_reply(message: types.Message):
    d = message.to_python()  # аналог .to_dict()
    ext = d.get("external_reply")
    if not (ext and ext.get("origin", {}).get("type") == "channel"):
        return

    chat = message.chat
    user = message.from_user
    origin_chat = ext.get("chat", {}) or ext.get("origin", {}).get("chat", {})
    origin_title = origin_chat.get("title", "❓")
    origin_username = origin_chat.get("username", "")

    log.info(
        f"\n================= 🚨 DETECTED 🚨 =================\n"
        f"📌 Чат: {chat.title} (ID: {chat.id})\n"
        f"👤 Пользователь: {user.first_name} @{user.username or '—'} (ID: {user.id})\n"
        f"💬 Сообщение ID: {message.message_id}\n"
        f"↪️ Репост из канала: {origin_title} @{origin_username or '—'}\n"
        "================================================="
    )

    # Проверка: не админ ли
    try:
        member = await chat.get_member(user.id)
        if member.is_chat_admin():
            log.info("⚠️ Отправитель админ — пропускаем.")
            return
    except Exception as e:
        log.error(f"❌ Ошибка при проверке статуса пользователя: {e}")
        return

    # Проверка прав бота
    try:
        me = await chat.get_member(bot.id)
        if not (me.can_delete_messages or me.can_restrict_members):
            log.error("❗️У бота нет прав (Delete/Restrict).")
            return
    except Exception as e:
        log.error(f"❌ Ошибка при проверке прав бота: {e}")
        return

    # Полный мут на 1 час
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
        await bot.restrict_chat_member(chat.id, user.id, permissions=full_mute, until_date=until)
        log.info(f"🔇 Пользователю {user.id} выдан ПОЛНЫЙ мут на 1 час")

        await message.delete()
        log.info(f"🗑 Сообщение {message.message_id} удалено")
        log.info("✅ Обработка завершена\n")

    except Exception as e:
        log.error(f"❌ Ошибка при муте/удалении: {e}")


if __name__ == "__main__":
    log.info("✅ Бот запущен и слушает группы")
    executor.start_polling(dp, skip_updates=True)
