import os
import asyncio
from telethon import TelegramClient, events
from dotenv import load_dotenv
from notifier import send_lead

load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

# Список чатов для мониторинга (юзернеймы IT-чатов фриланса)
TARGET_CHATS = ["freelance_python", "ItGidChat", "PythonAbonent"]
KEYWORDS = ["нужен разработчик", "сделать бота", "написать парсер", "требуется программист", "заказ на сайт"]


async def run_tg_monitor():
    if not API_ID or not API_HASH:
        print("[TG Monitor пропущен] Не заданы TELEGRAM_API_ID или TELEGRAM_API_HASH в .env")
        return

    client = TelegramClient("session_lead_hunter", int(API_ID), API_HASH)

    @client.on(events.NewMessage(chats=TARGET_CHATS))
    async def handler(event):
        text = event.raw_text.lower()
        if any(kw in text for kw in KEYWORDS):
            sender = await event.get_sender()
            username = sender.username if sender and sender.username else "нет_ника"
            chat = await event.get_chat()

            link = f"https://t.me/{chat.username}/{event.id}" if hasattr(chat,
                                                                         'username') and chat.username else "Закрытый чат"

            await send_lead(
                source="Telegram Chat",
                title=event.raw_text[:100] + "...",
                details=f"Автор: @{username}",
                link=link
            )

    await client.start()
    print("🤖 Telegram Monitor запущен и слушает чаты...")
    await client.run_until_disconnected()