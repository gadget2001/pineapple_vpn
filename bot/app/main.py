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
SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/AMBot_adm")
DOCUMENTS_BASE_URL = os.getenv("DOCUMENTS_BASE_URL", "")
WELCOME_IMAGE = Path(__file__).resolve().parents[1] / "img" / "welcome.png"

_REF_CODE_RE = re.compile(r"^ref_\d{1,20}$")

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

dp = Dispatcher()

HOW_IT_WORKS_TEXT = (
    "\U0001F4D6 \u041a\u0430\u043a \u044d\u0442\u043e \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442\n\n"
    "1. \u041d\u0430\u0436\u043c\u0438\u0442\u0435 \xab\u041e\u0442\u043a\u0440\u044b\u0442\u044c Pineapple VPN\xbb\n"
    "2. \u0412 MiniApp \u043f\u0440\u0438\u043c\u0438\u0442\u0435 \u0443\u0441\u043b\u043e\u0432\u0438\u044f \u0441\u0435\u0440\u0432\u0438\u0441\u0430\n"
    "3. \u0410\u043a\u0442\u0438\u0432\u0438\u0440\u0443\u0439\u0442\u0435 \u043f\u0440\u043e\u0431\u043d\u044b\u0439 \u043f\u0435\u0440\u0438\u043e\u0434\n"
    "4. \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e \u0438 \u0432\u044b\u043f\u043e\u043b\u043d\u0438\u0442\u0435 \u0448\u0430\u0433\u0438 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438\n"
    "5. \u041f\u043e\u043b\u0443\u0447\u0438\u0442\u0435 \u043a\u043e\u043d\u0444\u0438\u0433\u0443\u0440\u0430\u0446\u0438\u044e \u0438 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u0435\u0441\u044c\n\n"
    "\u041e\u0431\u044b\u0447\u043d\u043e \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 \u0437\u0430\u043d\u0438\u043c\u0430\u0435\u0442 \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u043c\u0438\u043d\u0443\u0442."
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


def _trial_used_key(telegram_id: int) -> str:
    return f"trial:used:{telegram_id}"


async def _has_trial_used(telegram_id: int) -> bool:
    return bool(await redis_client.get(_trial_used_key(telegram_id)))


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


def _resolve_docs_base_url() -> str | None:
    source = (DOCUMENTS_BASE_URL or MINIAPP_URL or "").strip()
    if not source:
        return None
    parts = urlsplit(source)
    if not parts.scheme or not parts.netloc:
        return None
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def _build_docs_urls() -> dict[str, str]:
    base = _resolve_docs_base_url()
    if not base:
        return {}
    return {
        "offer": f"{base}/docs/public-offer",
        "privacy": f"{base}/docs/privacy-policy",
        "aup": f"{base}/docs/acceptable-use",
    }


async def send_admin_log(action: str, message: Message, details: dict | None = None):
    if not ADMIN_CHAT_ID:
        return
    details = details or {}
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "[ Pineapple VPN LOG ]",
        "",
        f"\u041d\u043e\u0432\u043e\u0435 \u0441\u043e\u0431\u044b\u0442\u0438\u0435: {action}",
        "",
        f"User ID: {message.from_user.id}",
        f"Username: @{message.from_user.username or 'unknown'}",
        f"\u0414\u0430\u0442\u0430: {timestamp}",
    ]
    for k, v in details.items():
        lines.append(f"{k}: {v}")
    lines.extend(["", f"#user_{message.from_user.id}", f"#{action}"])

    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_CHAT_ID, "text": "\n".join(lines)},
        )


def _build_welcome_caption(is_referral: bool, trial_already_used: bool = False) -> str:
    text = (
        "\U0001F34D <b>Pineapple VPN</b>\n\n"
        "\u041d\u0430\u0434\u0435\u0436\u043d\u044b\u0439 \u0434\u043e\u0441\u0442\u0443\u043f \u043a \u0440\u043e\u0441\u0441\u0438\u0439\u0441\u043a\u0438\u043c \u0441\u0435\u0440\u0432\u0438\u0441\u0430\u043c \u0438\u0437 \u043b\u044e\u0431\u043e\u0439 \u0442\u043e\u0447\u043a\u0438 \u043c\u0438\u0440\u0430.\n\n"
        "\u041f\u043e\u0434\u0445\u043e\u0434\u0438\u0442 \u0434\u043b\u044f:\n"
        "\u2022 \u0431\u0430\u043d\u043a\u043e\u0432\n"
        "\u2022 \u0413\u043e\u0441\u0443\u0441\u043b\u0443\u0433\n"
        "\u2022 \u043e\u043f\u043b\u0430\u0442\u044b \u0416\u041a\u0425\n"
        "\u2022 \u0440\u0430\u0431\u043e\u0447\u0438\u0445 \u0441\u0438\u0441\u0442\u0435\u043c\n\n"
        "\U0001F510 \u0437\u0430\u0449\u0438\u0449\u0435\u043d\u043d\u043e\u0435 \u0441\u043e\u0435\u0434\u0438\u043d\u0435\u043d\u0438\u0435\n"
        "\u26A1 \u0431\u044b\u0441\u0442\u0440\u043e\u0435 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435\n"
        "\U0001F30D \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 \u0437\u0430 \u0433\u0440\u0430\u043d\u0438\u0446\u0435\u0439\n"
    )

    if is_referral:
        if trial_already_used:
            text += (
                "\n\U0001F381 <b>\u0412\u044b \u043f\u0440\u0438\u0448\u043b\u0438 \u043f\u043e \u043f\u0440\u0438\u0433\u043b\u0430\u0448\u0435\u043d\u0438\u044e</b>\n"
                "\u041f\u0440\u043e\u0431\u043d\u044b\u0439 \u043f\u0435\u0440\u0438\u043e\u0434 \u0443\u0436\u0435 \u0431\u044b\u043b \u0430\u043a\u0442\u0438\u0432\u0438\u0440\u043e\u0432\u0430\u043d \u0440\u0430\u043d\u0435\u0435 \u0432 \u0432\u0430\u0448\u0435\u043c \u0430\u043a\u043a\u0430\u0443\u043d\u0442\u0435, \u043f\u043e\u044d\u0442\u043e\u043c\u0443 \u043f\u043e\u0432\u0442\u043e\u0440\u043d\u043e \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d.\n"
            )
        else:
            text += (
                "\n\U0001F381 <b>\u0412\u044b \u043f\u0440\u0438\u0448\u043b\u0438 \u043f\u043e \u043f\u0440\u0438\u0433\u043b\u0430\u0448\u0435\u043d\u0438\u044e</b>\n"
                "\u0414\u043b\u044f \u0432\u0430\u0441 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d \u0443\u0432\u0435\u043b\u0438\u0447\u0435\u043d\u043d\u044b\u0439 \u043f\u0440\u043e\u0431\u043d\u044b\u0439 \u043f\u0435\u0440\u0438\u043e\u0434 \u2014 <b>7 \u0434\u043d\u0435\u0439 \u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e</b>.\n"
            )

    text += "\n\U0001F447 <b>\u041d\u0430\u0447\u043d\u0438\u0442\u0435 \u0437\u0430 \u043f\u0430\u0440\u0443 \u043c\u0438\u043d\u0443\u0442</b>"
    return text


def _build_welcome_keyboard(webapp_url: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if webapp_url:
        rows.append([
            InlineKeyboardButton(
                text="\U0001F680 \u041e\u0442\u043a\u0440\u044b\u0442\u044c Pineapple VPN",
                web_app=WebAppInfo(url=webapp_url),
            )
        ])

    rows.append([InlineKeyboardButton(text="\U0001F4C4 \u0414\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u044b", callback_data="docs_menu")])
    rows.append([InlineKeyboardButton(text="\U0001F4D6 \u041a\u0430\u043a \u044d\u0442\u043e \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442", callback_data="how_it_works")])
    rows.append([InlineKeyboardButton(text="\U0001F4AC \u041f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0430", url=SUPPORT_URL)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_docs_keyboard() -> InlineKeyboardMarkup:
    docs = _build_docs_urls()
    rows: list[list[InlineKeyboardButton]] = []
    if docs.get("offer"):
        rows.append([InlineKeyboardButton(text="\U0001F4DC \u041f\u0443\u0431\u043b\u0438\u0447\u043d\u0430\u044f \u043e\u0444\u0435\u0440\u0442\u0430", url=docs["offer"])])
        rows.append([InlineKeyboardButton(text="\U0001F512 \u041f\u043e\u043b\u0438\u0442\u0438\u043a\u0430 \u043a\u043e\u043d\u0444\u0438\u0434\u0435\u043d\u0446\u0438\u0430\u043b\u044c\u043d\u043e\u0441\u0442\u0438", url=docs["privacy"])])
        rows.append([InlineKeyboardButton(text="\u2696\uFE0F \u041f\u0440\u0430\u0432\u0438\u043b\u0430 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043d\u0438\u044f", url=docs["aup"])])
    rows.append([InlineKeyboardButton(text="\U0001F4AC \u041f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0430", url=SUPPORT_URL)])
    rows.append([InlineKeyboardButton(text="\U0001F3E0 \u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_main_menu_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001F3E0 \u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e", callback_data="main_menu")]
    ])


@dp.message(CommandStart())
async def cmd_start(message: Message):
    start_param = ""
    if message.text and " " in message.text:
        start_param = message.text.split(" ", 1)[1].strip()

    referral_code = _decode_referral_code(start_param)
    trial_already_used = await _has_trial_used(message.from_user.id)

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
            details["trial_already_used"] = "yes" if trial_already_used else "no"
        await send_admin_log("bot_first_start", message, details)

    webapp_url = _build_miniapp_url_with_start(MINIAPP_URL, start_param if referral_code else None)
    caption = _build_welcome_caption(bool(referral_code), trial_already_used=trial_already_used)
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


@dp.callback_query(F.data == "docs_menu")
async def docs_menu(callback: CallbackQuery):
    await callback.answer()
    docs = _build_docs_urls()
    if not docs:
        await callback.message.answer(
            "\U0001F4C4 \u0414\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u044b \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b. "
            "\u041d\u0430\u043f\u0438\u0448\u0438\u0442\u0435 \u0432 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0443, \u0438 \u043c\u044b \u043f\u043e\u043c\u043e\u0436\u0435\u043c.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\U0001F4AC \u041f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0430", url=SUPPORT_URL)]
            ]),
        )
        return

    await callback.message.answer(
        "\U0001F4C4 \u042e\u0440\u0438\u0434\u0438\u0447\u0435\u0441\u043a\u0438\u0435 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u044b Pineapple VPN:\n\n"
        "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043d\u0443\u0436\u043d\u044b\u0439 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442 \u2014 \u043e\u043d \u043e\u0442\u043a\u0440\u043e\u0435\u0442\u0441\u044f \u0432 \u0431\u0440\u0430\u0443\u0437\u0435\u0440\u0435 \u0431\u0435\u0437 \u0437\u0430\u043f\u0443\u0441\u043a\u0430 MiniApp.",
        reply_markup=_build_docs_keyboard(),
    )


@dp.callback_query(F.data == "how_it_works")
async def how_it_works(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(HOW_IT_WORKS_TEXT, reply_markup=_build_main_menu_button())


@dp.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    await callback.answer()
    webapp_url = _build_miniapp_url_with_start(MINIAPP_URL, None)
    caption = _build_welcome_caption(False, trial_already_used=False)
    keyboard = _build_welcome_keyboard(webapp_url)

    if WELCOME_IMAGE.exists():
        await callback.message.answer_photo(
            photo=FSInputFile(str(WELCOME_IMAGE)),
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    else:
        await callback.message.answer(
            caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )


async def main():
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
