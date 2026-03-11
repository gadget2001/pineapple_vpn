from datetime import datetime, timezone
from typing import Any, Dict

import httpx

from app.core.config import settings


async def send_admin_log(action: str, user_id: int | None, username: str | None, details: Dict[str, Any]):
    if not settings.admin_chat_id or not settings.bot_token:
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    user_tag = f"#user_{user_id}" if user_id else "#user_unknown"
    lines = [
        "[ Pineapple VPN LOG ]",
        "",
        f"Новое событие: {action}",
        "",
        f"User ID: {user_id or 'unknown'}",
        f"Username: @{username}" if username else "Username: неизвестно",
        f"Дата: {timestamp}",
        "",
        user_tag,
        f"#{action.replace(' ', '_').lower()}",
    ]

    if details:
        for key, value in details.items():
            lines.insert(-2, f"{key}: {value}")

    text = "\n".join(lines)

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

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    user_tag = f"#user_{user_id}" if user_id else "#user_unknown"
    lines = [
        "[ Pineapple VPN LOG ]",
        "",
        f"Новое событие: {action}",
        "",
        f"User ID: {user_id or 'unknown'}",
        f"Username: @{username}" if username else "Username: неизвестно",
        f"Дата: {timestamp}",
        "",
        user_tag,
        f"#{action.replace(' ', '_').lower()}",
    ]

    if details:
        for key, value in details.items():
            lines.insert(-2, f"{key}: {value}")

    text = "\n".join(lines)

    httpx.post(
        f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
        json={"chat_id": settings.admin_chat_id, "text": text, "disable_web_page_preview": True},
        timeout=10,
    )
