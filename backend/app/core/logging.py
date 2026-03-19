from datetime import datetime, timezone
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.core.config import settings


ACTION_TITLES = {
    "first_start": "Первый запуск бота",
    "registration": "Регистрация пользователя",
    "terms_accepted": "Приняты условия",
    "trial_activated": "Активирован пробный период",
    "wallet_topup": "Пополнение кошелька",
    "subscription_activated": "Подписка активирована",
    "subscription_reminder_sent": "Отправлено напоминание о продлении",
    "subscription_expired": "Подписка истекла",
    "vpn_disabled": "VPN отключен",
    "vpn_config_created": "VPN-конфиг создан",
    "vpn_profile_generated_clash": "Сгенерирован Clash-профиль",
    "vpn_profile_generated_android_hiddify": "Сгенерирован Android Hiddify-профиль",
    "vpn_subscription_opened": "Открыта ссылка подписки VPN",
    "vpn_profile_downloaded": "Профиль VPN скачан",
    "vpn_client_selected": "Выбран VPN-клиент",
    "vpn_platform_config_issued": "Выдан платформенный конфиг",
    "vpn_profile_reused_for_new_device": "Профиль переиспользован для нового устройства",
    "vpn_profile_reused": "Профиль переиспользован",
    "vpn_repeat_device_setup_started": "Запущена повторная настройка устройства",
    "vpn_install_link_generated": "Сгенерирована ссылка автонастройки",
    "vpn_install_link_opened": "Открыта ссылка автонастройки",
    "vpn_install_opened": "Открыт install endpoint",
    "vpn_install_fallback_opened": "Открыта fallback-страница установки",
    "vpn_deep_link_redirected": "Выполнен редирект в deep link",
    "vpn_install_link_generated_ios": "Сгенерирована iOS-ссылка автонастройки",
    "vpn_install_link_opened_ios": "Открыта iOS-ссылка автонастройки",
    "vpn_install_fallback_opened_ios": "Открыта iOS fallback-страница",
    "vpn_hiddify_install_link_generated": "Сгенерирована Hiddify-ссылка автонастройки",
    "vpn_hiddify_install_opened": "Открыта Hiddify-ссылка автонастройки",
    "vpn_hiddify_fallback_opened": "Открыт Hiddify fallback",
    "onboarding_platform_selected": "Выбрана платформа в онбординге",
    "onboarding_instruction_viewed": "Открыта инструкция онбординга",
    "onboarding_app_installed": "Подтверждена установка приложения",
    "onboarding_config_received": "Получена конфигурация онбординга",
    "onboarding_completed": "Онбординг завершен",
    "onboarding_restarted": "Онбординг перезапущен",
    "payment_error": "Ошибка платежа",
    "user_purged": "Пользователь удален",
    "daily_limit_reached": "Достигнут дневной лимит трафика",
}

DETAIL_TITLES = {
    "uuid": "UUID",
    "vless_url": "VLESS URL",
    "subscription_url": "Ссылка подписки",
    "reality_public_key": "Reality public key",
    "os": "Платформа",
    "platform": "Платформа",
    "client_type": "Тип клиента",
    "flow": "Сценарий",
    "step": "Шаг",
    "kind": "Тип",
    "profile_id": "ID профиля",
    "install_url": "Install URL",
    "mode": "Режим",
    "subscription_id": "ID подписки",
    "plan": "Тариф",
    "reminder": "Напоминание",
    "ends_at": "Окончание",
    "ended_at": "Окончание",
    "completed_at": "Завершено",
    "profile_reused": "Профиль переиспользован",
    "generated_at": "Сгенерировано",
    "total_mb": "Лимит (МБ)",
    "expire_at": "Истекает",
    "reason": "Причина",
    "deleted_from_panel": "Удален в панели",
    "panel_disable_ok": "Disable в панели",
    "panel_delete_ok": "Delete в панели",
    "panel_username": "Пользователь панели",
    "date": "Дата",
    "used_gb": "Использовано (ГБ)",
    "limit_gb": "Лимит (ГБ)",
    "used_bytes": "Использовано (байт)",
    "limit_bytes": "Лимит (байт)",
}

PLATFORM_LABELS = {
    "windows": "Windows",
    "android": "Android",
    "iphone": "iPhone",
    "ios": "iOS",
    "macos": "macOS",
    "linux": "Linux",
}

SEVERITY_MAP = {
    "red": {
        "label": "Критично",
        "icon": "🔴",
    },
    "yellow": {
        "label": "Внимание",
        "icon": "🟡",
    },
    "green": {
        "label": "Инфо",
        "icon": "🟢",
    },
}

ACTION_SEVERITY = {
    # Critical events
    "payment_error": "red",
    "subscription_expired": "red",
    "vpn_disabled": "red",
    "daily_limit_reached": "red",
    "user_purged": "red",
    # Warning / requires attention
    "subscription_reminder_sent": "yellow",
    "vpn_install_fallback_opened": "yellow",
    "vpn_install_fallback_opened_ios": "yellow",
    "vpn_hiddify_fallback_opened": "yellow",
    # Info events by default below
}


def _present_action(action: str) -> str:
    return ACTION_TITLES.get(action, action)


def _resolve_severity(action: str) -> dict[str, str]:
    level = ACTION_SEVERITY.get(action, "green")
    return SEVERITY_MAP[level]


def _present_bool(value: bool) -> str:
    return "Да" if value else "Нет"


def _present_value(key: str, value: Any) -> str:
    if isinstance(value, bool):
        return _present_bool(value)
    if key in {"platform", "os"}:
        return PLATFORM_LABELS.get(str(value).lower(), str(value))
    return str(value)


def _present_details(action: str, details: dict[str, Any]) -> list[tuple[str, str]]:
    if not details:
        return []

    if action == "vpn_config_created":
        items = [
            ("uuid", details.get("uuid")),
            ("vless_url", details.get("vless_url")),
            ("subscription_url", details.get("subscription_url")),
            ("reality_public_key", details.get("reality_public_key")),
        ]
        return [
            (DETAIL_TITLES.get(k, k), _present_value(k, v))
            for k, v in items
            if v not in (None, "", "None")
        ]

    rows: list[tuple[str, str]] = []
    for key, value in details.items():
        if value in (None, "", "None"):
            continue
        rows.append((DETAIL_TITLES.get(key, key), _present_value(key, value)))
    return rows


def _fmt_detail_value(value: str) -> str:
    raw = str(value)
    if len(raw) > 900:
        raw = f"{raw[:900]}..."
    return f"<code>{escape(raw)}</code>"


def _now_labels() -> tuple[str, str]:
    now_utc = datetime.now(timezone.utc)
    try:
        local_tz = ZoneInfo(settings.sched_tz or "Europe/Moscow")
    except Exception:
        local_tz = timezone.utc
    now_local = now_utc.astimezone(local_tz)
    local_tz_name = now_local.tzname() or str(local_tz)
    local_label = now_local.strftime(f"%d.%m.%Y %H:%M:%S {local_tz_name}")
    utc_label = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    return local_label, utc_label


def _build_message(action: str, user_id: int | None, username: str | None, details: dict[str, Any]) -> str:
    local_ts, utc_ts = _now_labels()
    severity = _resolve_severity(action)
    event_name = escape(_present_action(action))
    safe_username = escape(username) if username else "unknown"
    action_tag = action.replace(" ", "_").lower()
    user_tag = f"#user_{user_id}" if user_id else "#user_unknown"
    detail_rows = _present_details(action, details)

    lines = [
        f"{severity['icon']} <b>Pineapple VPN • Админ-лог</b>",
        "",
        f"<b>Событие:</b> <b>{event_name}</b>",
        f"<b>Уровень:</b> <b>{severity['label']}</b>",
        f"<b>Пользователь:</b> <code>{user_id or 'unknown'}</code> • @{safe_username}",
        f"<b>Время:</b> <code>{escape(local_ts)}</code>",
        f"<b>UTC:</b> <code>{escape(utc_ts)}</code>",
    ]

    if detail_rows:
        lines.extend(["", "<b>Детали:</b>"])
        for title, value in detail_rows:
            lines.append(f"• <b>{escape(title)}:</b> {_fmt_detail_value(value)}")

    lines.extend(["", f"{user_tag} #{action_tag}"])
    return "\n".join(lines)


def _admin_log_payload(text: str) -> dict[str, Any]:
    return {
        "chat_id": settings.admin_chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }


async def send_admin_log(action: str, user_id: int | None, username: str | None, details: dict[str, Any]):
    if not settings.admin_chat_id or not settings.bot_token:
        return

    text = _build_message(action, user_id, username, details)
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
            json=_admin_log_payload(text),
        )


def send_admin_log_sync(action: str, user_id: int | None, username: str | None, details: dict[str, Any]):
    if not settings.admin_chat_id or not settings.bot_token:
        return

    text = _build_message(action, user_id, username, details)
    httpx.post(
        f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
        json=_admin_log_payload(text),
        timeout=10,
    )


def _build_bot_main_menu_markup() -> dict:
    return {
        "inline_keyboard": [
            [
                {
                    "text": "Main menu",
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
