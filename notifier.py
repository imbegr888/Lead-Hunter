import os
import logging
from aiogram import Bot
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

bot = Bot(token=TOKEN) if TOKEN else None

async def send_lead(source: str, title: str, details: str, link: str):
    """Универсальная функция отправки лида в Telegram"""
    if not bot or not CHAT_ID:
        logging.info(f"[{source}] Лид: {title} | {link}")
        return

    message = (
        f"🔥 **Новый лид [{source}]!**\n\n"
        f"📌 **Задача/Компания:** {title}\n"
        f"🔍 **Детали:** {details}\n"
        f"🔗 **Ссылка / Контакт:** {link}"
    )

    try:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка отправки уведомления: {e}")