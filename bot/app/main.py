import asyncio
import base64
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from redis.asyncio import Redis

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
MINIAPP_URL = os.getenv("TELEGRAM_MINIAPP_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:16379/0")
SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/ambot24")
WELCOME_IMAGE = Path(__file__).resolve().parents[1] / "img" / "welcome.png"

_REF_CODE_RE = re.compile(r"^ref_\d{1,20}$")

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

dp = Dispatcher()

HOW_IT_WORKS_TEXT = (
    "📖 Как это работает\n\n"
    "1. Нажмите «Открыть Pineapple VPN»\n"
    "2. В MiniApp примите правила сервиса\n"
    "3. Активируйте пробный период\n"
    "4. Выберите устройство и выполните шаги настройки\n"
    "5. Получите конфигурацию и подключитесь\n\n"
    "Обычно это занимает всего несколько минут."
)


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
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k not in {"startapp", "start"}
    ]
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


def _build_welcome_caption(is_referral: bool) -> str:
    text = (
        "🍍 <b>Pineapple VPN</b>\n\n"
        "Надежный доступ к российским сервисам из любой точки мира.\n\n"
        "Подходит для:\n"
        "• банков\n"
        "• Госуслуг\n"
        "• оплаты ЖКХ\n"
        "• рабочих систем\n\n"
        "🔐 защищенное соединение\n"
        "⚡ быстрое подключение\n"
        "🌍 работает за границей\n"
    )

    if is_referral:
        text += (
            "\n🎁 <b>Вы пришли по приглашению</b>\n"
            "Для вас доступен увеличенный пробный период — <b>7 дней бесплатно</b>.\n"
        )

    text += "\n👇 <b>Начните за пару минут</b>"
    return text


def _build_welcome_keyboard(webapp_url: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if webapp_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🚀 Открыть Pineapple VPN",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ]
        )

    rows.append([InlineKeyboardButton(text="📖 Как это работает", callback_data="how_it_works")])
    rows.append([InlineKeyboardButton(text="💬 Поддержка", url=SUPPORT_URL)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


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
    caption = _build_welcome_caption(bool(referral_code))
    keyboard = _build_welcome_keyboard(webapp_url)

    if WELCOME_IMAGE.exists():
        await message.answer_photo(
            photo=FSInputFile(str(WELCOME_IMAGE)),
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    else:
        await message.answer(
            caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )


@dp.callback_query(F.data == "how_it_works")
async def how_it_works(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(HOW_IT_WORKS_TEXT)


async def main():
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())