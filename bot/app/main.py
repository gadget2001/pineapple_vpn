import asyncio
import os
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import httpx

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
MINIAPP_URL = os.getenv("TELEGRAM_MINIAPP_URL")


dp = Dispatcher()


async def send_admin_log(action: str, message: Message):
    if not ADMIN_CHAT_ID:
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    text = (
        "[ Pineapple VPN LOG ]\n\n"
        f"Новое событие: {action}\n\n"
        f"User ID: {message.from_user.id}\n"
        f"Username: @{message.from_user.username or 'unknown'}\n"
        f"Дата: {timestamp}\n\n"
        f"#user_{message.from_user.id}\n"
        f"#{action.replace(' ', '_').lower()}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_CHAT_ID, "text": text},
        )


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await send_admin_log("запуск бота пользователем", message)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Открыть Pineapple VPN", web_app=WebAppInfo(url=MINIAPP_URL))]],
        resize_keyboard=True,
    )
    await message.answer(
        "Pineapple VPN — защищенный доступ к российскому IP из-за границы.\n\n"
        "Возможности:\n"
        "• подписка и оплата\n"
        "• VPN конфигурация\n"
        "• реферальная система\n\n"
        "Нажмите кнопку ниже, чтобы открыть MiniApp.",
        reply_markup=keyboard,
    )


async def main():
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())