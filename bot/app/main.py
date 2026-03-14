import asyncio
import base64
import os
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, WebAppInfo
import httpx
from redis.asyncio import Redis

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
MINIAPP_URL = os.getenv("TELEGRAM_MINIAPP_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:16379/0")

_REF_CODE_RE = re.compile(r"^ref_\d{1,20}$")

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

dp = Dispatcher()


def _decode_referral_code(payload: str | None) -> str | None:
    if not payload:
        return None
    candidate = payload.strip()
    if not candidate:
        return None

    if _REF_CODE_RE.fullmatch(candidate):
        return candidate

    padding = "=" * ((4 - len(candidate) % 4) % 4)
    try:
        decoded = base64.urlsafe_b64decode(candidate + padding).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    return decoded if _REF_CODE_RE.fullmatch(decoded) else None


def _build_miniapp_url_with_start(base_url: str | None, start_payload: str | None) -> str | None:
    if not base_url:
        return None
    if not start_payload:
        return base_url

    parts = urlsplit(base_url)
    query_pairs = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k not in {"startapp", "start"}]
    query_pairs.append(("startapp", start_payload))
    updated_query = urlencode(query_pairs)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, updated_query, parts.fragment))


async def send_admin_log(action: str, message: Message, details: dict | None = None):
    if not ADMIN_CHAT_ID:
        return
    details = details or {}
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "[ Pineapple VPN LOG ]",
        "",
        f"Новое событие: {action}",
        "",
        f"User ID: {message.from_user.id}",
        f"Username: @{message.from_user.username or 'unknown'}",
        f"Дата: {timestamp}",
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

    referral_code = _decode_referral_code(start_param)

    first_key = f"bot:first_start:{message.from_user.id}"
    is_first_start = await redis_client.set(first_key, "1", nx=True)
    if is_first_start:
        details = {
            "referral_start": "yes" if referral_code else "no",
            "payload_valid": "yes" if referral_code else "no",
        }
        if start_param:
            details["start_param"] = start_param
        if referral_code:
            details["referral_code"] = referral_code
        await send_admin_log("bot_first_start", message, details)

    webapp_url = _build_miniapp_url_with_start(MINIAPP_URL, start_param if referral_code else None)
    keyboard = None
    if webapp_url:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Открыть Pineapple VPN", web_app=WebAppInfo(url=webapp_url))]],
            resize_keyboard=True,
        )

    referral_note = (
        "\n\nВы пришли по приглашению: для вас доступен расширенный пробный период."
        if referral_code
        else ""
    )

    await message.answer(
        "Pineapple VPN\n"
        "Защищенный удаленный доступ к российским сервисам из-за границы.\n"
        "В MiniApp вы сможете: принять правила, активировать пробный период,\n"
        "пополнить кошелек, оформить подписку и получить настройку VPN." + referral_note,
        reply_markup=keyboard,
    )


async def main():
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
