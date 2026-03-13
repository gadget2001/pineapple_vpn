from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import unquote

import httpx

from app.core.config import settings


ACTION_TITLES = {
    "first_start": "Первый запуск бота",
    "registration": "Регистрация пользователя",
    "trial_activated": "Активация пробного периода",
    "wallet_topup": "Пополнение кошелька",
    "subscription_activated": "Активация подписки",
    "subscription_expired": "Окончание подписки",
    "vpn_disabled": "Отключение VPN",
    "vpn_config_created": "Создан VPN-конфиг",
    "payment_error": "Ошибка платежа",
}


def _present_action(action: str) -> str:
    return ACTION_TITLES.get(action, action)


def _present_details(action: str, details: Dict[str, Any]) -> list[str]:
    if not details:
        return []

    if action == "vpn_config_created":
        vless_url = details.get("vless_url") or ""
        try:
            vless_url = unquote(str(vless_url))
        except Exception:
            vless_url = str(vless_url)

        items = [
            ("UUID", details.get("uuid")),
            ("VLESS", vless_url),
            ("Конфигурация VPN", details.get("subscription_url")),
            ("Reality key", details.get("reality_public_key")),
        ]
        return [f"{k}: {v}" for k, v in items if v not in (None, "", "None")]

    pretty_lines: list[str] = []
    for key, value in details.items():
        if value in (None, "", "None"):
            continue
        pretty_lines.append(f"{key}: {value}")
    return pretty_lines


def _build_message(action: str, user_id: int | None, username: str | None, details: Dict[str, Any]) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    user_tag = f"#user_{user_id}" if user_id else "#user_unknown"
    lines = [
        "[ Pineapple VPN LOG ]",
        "",
        f"Новое событие: {_present_action(action)}",
        "",
        f"User ID: {user_id or 'unknown'}",
        f"Username: @{username}" if username else "Username: неизвестно",
        f"Дата: {timestamp}",
        "",
        user_tag,
        f"#{action.replace(' ', '_').lower()}",
    ]

    for line in _present_details(action, details):
        lines.insert(-2, line)

    return "\n".join(lines)


async def send_admin_log(action: str, user_id: int | None, username: str | None, details: Dict[str, Any]):
    if not settings.admin_chat_id or not settings.bot_token:
        return

    text = _build_message(action, user_id, username, details)
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
            json={
                "chat_id": settings.admin_chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
        )


def send_admin_log_sync(action: str, user_id: int | None, username: str | None, details: Dict[str, Any]):
    if not settings.admin_chat_id or not settings.bot_token:
        return

    text = _build_message(action, user_id, username, details)
    httpx.post(
        f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
        json={"chat_id": settings.admin_chat_id, "text": text, "disable_web_page_preview": True},
        timeout=10,
    )


