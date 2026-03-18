from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings


ACTION_TITLES = {
    "first_start": "Первый запуск бота",
    "registration": "Регистрация пользователя",
    "terms_accepted": "Согласие с правилами",
    "trial_activated": "Активация пробного периода",
    "wallet_topup": "Пополнение кошелька",
    "subscription_activated": "Активация подписки",
    "subscription_reminder_sent": "Отправлено напоминание о продлении",
    "subscription_expired": "Окончание подписки",
    "vpn_disabled": "Отключение VPN",
    "vpn_config_created": "Создан VPN-конфиг",
    "vpn_profile_generated_clash": "Сгенерирован Clash профиль",
    "vpn_profile_generated_hiddify": "Сгенерирован Hiddify профиль",
    "vpn_subscription_opened": "Открыта ссылка подписки",
    "vpn_profile_downloaded": "Скачан VPN-профиль",
    "vpn_client_selected": "Выбран VPN-клиент",
    "vpn_platform_config_issued": "Выдана платформенная конфигурация",
    "vpn_profile_reused_for_new_device": "Ключ переиспользован для нового устройства",
    "vpn_repeat_device_setup_started": "Запущена повторная настройка устройства",
    "vpn_install_link_generated": "Сгенерирована install-ссылка",
    "vpn_install_link_opened": "Открыта install-ссылка",
    "vpn_install_fallback_opened": "Открыта install fallback-страница",
    "vpn_deep_link_redirected": "Выполнен deep-link редирект",
    "onboarding_platform_selected": "Выбор устройства в onboarding",
    "onboarding_instruction_viewed": "Просмотр инструкции подключения",
    "onboarding_app_installed": "Подтверждена установка приложения",
    "onboarding_config_received": "Получена VPN-конфигурация",
    "onboarding_completed": "Onboarding завершен",
    "onboarding_restarted": "Повторная настройка устройства",
    "payment_error": "Ошибка платежа",
    "user_purged": "Пользователь удален для теста",
    "daily_limit_reached": "Пользователь достиг дневного лимита трафика",
}


def _present_action(action: str) -> str:
    return ACTION_TITLES.get(action, action)


def _present_details(action: str, details: dict[str, Any]) -> list[str]:
    if not details:
        return []

    if action == "vpn_config_created":
        items = [
            ("UUID", details.get("uuid")),
            ("VLESS", details.get("vless_url")),
            ("VPN subscription", details.get("subscription_url")),
            ("Reality key", details.get("reality_public_key")),
        ]
        return [f"{k}: {v}" for k, v in items if v not in (None, "", "None")]

    return [f"{key}: {value}" for key, value in details.items() if value not in (None, "", "None")]


def _build_message(action: str, user_id: int | None, username: str | None, details: dict[str, Any]) -> str:
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


async def send_admin_log(action: str, user_id: int | None, username: str | None, details: dict[str, Any]):
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


def send_admin_log_sync(action: str, user_id: int | None, username: str | None, details: dict[str, Any]):
    if not settings.admin_chat_id or not settings.bot_token:
        return

    text = _build_message(action, user_id, username, details)
    httpx.post(
        f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
        json={"chat_id": settings.admin_chat_id, "text": text, "disable_web_page_preview": True},
        timeout=10,
    )


def _build_bot_main_menu_markup() -> dict:
    return {
        "inline_keyboard": [
            [
                {
                    "text": "Главное меню",
                    "callback_data": "main_menu",
                }
            ]
        ]
    }


async def send_user_bot_message(user_telegram_id: int, text: str, with_main_menu_button: bool = False):
    if not user_telegram_id or not settings.bot_token:
        return

    payload = {
        "chat_id": user_telegram_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if with_main_menu_button:
        payload["reply_markup"] = _build_bot_main_menu_markup()

    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
            json=payload,
        )

