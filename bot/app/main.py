import asyncio
import base64
import os
import re
from datetime import datetime, timezone
from html import escape
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
    MenuButtonCommands,
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
    "📖 Как это работает\n\n"
    "1. Нажмите \xabОткрыть Pineapple VPN\xbb\n"
    "2. В MiniApp примите условия сервиса\n"
    "3. Активируйте пробный период\n"
    "4. Выберите устройство и выполните шаги настройки\n"
    "5. Получите конфигурацию и подключитесь\n\n"
    "Обычно настройка занимает несколько минут."
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
    title = "Первый запуск бота" if action == "bot_first_start" else action
    safe_user = escape(message.from_user.username or "unknown")
    safe_title = escape(title)
    lines = [
        "<b>Pineapple VPN | Админ-лог</b>",
        "",
        f"<b>Событие:</b> <b>{safe_title}</b>",
        "<b>Уровень:</b> <b>Инфо</b>",
        f"<b>Пользователь:</b> <code>{message.from_user.id}</code> | @{safe_user}",
        f"<b>UTC:</b> <code>{timestamp}</code>",
    ]
    if details:
        lines.extend(["", "<b>Детали:</b>"])
        for k, v in details.items():
            lines.append(f"- <b>{escape(str(k))}:</b> <code>{escape(str(v))}</code>")
    lines.extend(["", f"#user_{message.from_user.id} #{action}"])

    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": ADMIN_CHAT_ID,
                "text": "\n".join(lines),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )

def _build_welcome_caption(is_referral: bool, trial_already_used: bool = False) -> str:
    text = (
        "🍍 <b>Pineapple</b>\n\n"
        "Стабильный доступ к российским сервисам из-за границы.\n\n"
        "Если не открываются:\n"
        "• корпоративные системы\n"
        "• RDP / удалённый рабочий стол\n"
        "• внутренние сервисы компании\n"
        "• рабочие инструменты\n\n"
        "🔐 защищённое подключение\n"
        "⚡ запуск за пару минут\n"
        "🌍 работает из любой страны\n"
    )

    if is_referral:
        if trial_already_used:
            text += (
                "\n🎁 <b>Вы пришли по приглашению</b>\n"
                "Пробный период уже был активирован ранее в вашем аккаунте, поэтому повторно недоступен.\n"
            )
        else:
            text += (
                "\n🎁 <b>Вы пришли по приглашению</b>\n"
                "Для вас доступен увеличенный пробный период — <b>7 дней бесплатно</b>.\n"
            )

    text += "\n👇 <b>Начните за пару минут</b>"
    return text


def _build_welcome_keyboard(webapp_url: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if webapp_url:
        rows.append([
            InlineKeyboardButton(
                text="🚀 Открыть Pineapple VPN",
                web_app=WebAppInfo(url=webapp_url),
            )
        ])

    rows.append([InlineKeyboardButton(text="📄 Документы", callback_data="docs_menu")])
    rows.append([InlineKeyboardButton(text="📖 Как это работает", callback_data="how_it_works")])
    rows.append([InlineKeyboardButton(text="💬 Поддержка", url=SUPPORT_URL)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_docs_keyboard() -> InlineKeyboardMarkup:
    docs = _build_docs_urls()
    rows: list[list[InlineKeyboardButton]] = []
    if docs.get("offer"):
        rows.append([InlineKeyboardButton(text="📜 Публичная оферта", url=docs["offer"])])
        rows.append([InlineKeyboardButton(text="🔒 Политика конфиденциальности", url=docs["privacy"])])
        rows.append([InlineKeyboardButton(text="⚖️ Правила использования", url=docs["aup"])])
    rows.append([InlineKeyboardButton(text="💬 Поддержка", url=SUPPORT_URL)])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_main_menu_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
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
        first_start_at_key = f"bot:first_start_at:{message.from_user.id}"
        await redis_client.set(first_start_at_key, str(int(datetime.now(timezone.utc).timestamp())), nx=True)
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
            "📄 Документы временно недоступны. "
            "Напишите в поддержку, и мы поможем.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Поддержка", url=SUPPORT_URL)]
            ]),
        )
        return

    await callback.message.answer(
        "📄 Юридические документы Pineapple VPN:\n\n"
        "Выберите нужный документ — он откроется в браузере без запуска MiniApp.",
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
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
