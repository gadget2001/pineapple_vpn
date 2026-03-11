import asyncio
import os
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, WebAppInfo
import httpx
from redis.asyncio import Redis

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
MINIAPP_URL = os.getenv("TELEGRAM_MINIAPP_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:16379/0")

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

dp = Dispatcher()


async def send_admin_log(action: str, message: Message, details: dict | None = None):
    if not ADMIN_CHAT_ID:
        return
    details = details or {}
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "[ Pineapple VPN LOG ]",
        "",
        f"New event: {action}",
        "",
        f"User ID: {message.from_user.id}",
        f"Username: @{message.from_user.username or 'unknown'}",
        f"Date: {timestamp}",
    ]
    for k, v in details.items():
        lines.append(f"{k}: {v}")
    lines.extend(["", f"#user_{message.from_user.id}", f"#{action}"])

    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_CHAT_ID, "text": "\n".join(lines)},
        )


@dp.message(CommandStart())
async def cmd_start(message: Message):
    start_param = ""
    if message.text and " " in message.text:
        start_param = message.text.split(" ", 1)[1].strip()

    first_key = f"bot:first_start:{message.from_user.id}"
    is_first_start = await redis_client.set(first_key, "1", nx=True)
    if is_first_start:
        details = {"referral_start": "yes" if start_param.startswith("ref_") else "no"}
        if start_param:
            details["start_param"] = start_param
        await send_admin_log("bot_first_start", message, details)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Open Pineapple VPN", web_app=WebAppInfo(url=MINIAPP_URL))]],
        resize_keyboard=True,
    )

    await message.answer(
        "Pineapple VPN\n"
        "Secure access to Russian IP from abroad.\n\n"
        "Open MiniApp to activate trial, top up wallet, buy subscription and get ready VPN config.",
        reply_markup=keyboard,
    )


async def main():
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())