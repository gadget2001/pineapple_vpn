from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings


ACTION_TITLES = {
    "first_start": "First bot start",
    "registration": "User registration",
    "terms_accepted": "Terms accepted",
    "trial_activated": "Trial activated",
    "wallet_topup": "Wallet top-up",
    "subscription_activated": "Subscription activated",
    "subscription_reminder_sent": "Renewal reminder sent",
    "subscription_expired": "Subscription expired",
    "vpn_disabled": "VPN disabled",
    "vpn_config_created": "VPN config created",
    "vpn_profile_generated_clash": "Clash profile generated",
    "vpn_profile_generated_happ": "Happ profile generated",
    "vpn_profile_generated_hiddify": "Hiddify profile generated",
    "vpn_subscription_opened": "VPN subscription opened",
    "vpn_profile_downloaded": "VPN profile downloaded",
    "vpn_client_selected": "VPN client selected",
    "vpn_platform_config_issued": "Platform config issued",
    "vpn_profile_reused_for_new_device": "VPN profile reused for new device",
    "vpn_profile_reused": "VPN profile reused",
    "vpn_repeat_device_setup_started": "Repeat device setup started",
    "vpn_install_link_generated": "Install link generated",
    "vpn_install_link_opened": "Install link opened",
    "vpn_install_opened": "Install endpoint opened",
    "vpn_install_fallback_opened": "Install fallback opened",
    "vpn_deep_link_redirected": "Deep link redirected",
    "onboarding_platform_selected": "Onboarding platform selected",
    "onboarding_instruction_viewed": "Onboarding instruction viewed",
    "onboarding_app_installed": "Onboarding app installed",
    "onboarding_config_received": "Onboarding config received",
    "onboarding_completed": "Onboarding completed",
    "onboarding_restarted": "Onboarding restarted",
    "payment_error": "Payment error",
    "user_purged": "User purged",
    "daily_limit_reached": "Daily traffic limit reached",
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
        f"Event: {_present_action(action)}",
        "",
        f"User ID: {user_id or 'unknown'}",
        f"Username: @{username}" if username else "Username: unknown",
        f"Date: {timestamp}",
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
