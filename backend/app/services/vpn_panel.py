from typing import Any, Dict

import httpx

from app.core.config import settings


def _normalize_panel_url() -> str:
    return settings.panel_url.rstrip("/")


def _extract_profile(response_data: Dict[str, Any]) -> Dict[str, Any]:
    links = response_data.get("links", [])
    vless_url = ""
    subscription_url = response_data.get("subscription_url", "")

    if isinstance(links, list) and links:
        vless_url = links[0]

    if not subscription_url:
        subscription_url = response_data.get("sub_updated_at", "")

    return {
        "uuid": response_data.get("proxies", {}).get("vless", {}).get("id", "")
        or response_data.get("uuid", ""),
        "vless_url": vless_url or response_data.get("vless_url", ""),
        "subscription_url": subscription_url,
        "reality_public_key": response_data.get("reality_public_key")
        or response_data.get("proxies", {}).get("vless", {}).get("reality_settings", {}).get("public_key"),
    }


async def create_vpn_user(telegram_id: int, username: str | None) -> Dict[str, Any]:
    inbound_candidates = [settings.panel_inbound_name, "reality", "VLESS TCP REALITY"]
    base_payload = {
        "username": f"tg_{telegram_id}",
        "inbounds": {"vless": []},
        "status": "active",
        "data_limit": 0,
        "expire": 0,
        "note": username or "",
        "on_hold_timeout": "0",
        "on_hold_expire_duration": 0,
        "auto_delete_in_days": 0,
        "proxies": {"vless": {"flow": "xtls-rprx-vision"}},
        "inbound_limit": settings.vpn_max_connections,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        data = None
        last_exc = None
        for inbound_name in inbound_candidates:
            payload = {**base_payload, "inbounds": {"vless": [inbound_name]}}
            try:
                response = await client.post(
                    f"{_normalize_panel_url()}/api/user",
                    headers={"Authorization": f"Bearer {settings.panel_token}"},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                break
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                continue

        if data is None and last_exc:
            raise last_exc

        # Fetch fresh user details to ensure links/subscription are present.
        details = await client.get(
            f"{_normalize_panel_url()}/api/user/tg_{telegram_id}",
            headers={"Authorization": f"Bearer {settings.panel_token}"},
        )
        if details.is_success:
            data = details.json()

        return _extract_profile(data)


async def disable_vpn_user(telegram_id: int):
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(
            f"{_normalize_panel_url()}/api/user/disable/tg_{telegram_id}",
            headers={"Authorization": f"Bearer {settings.panel_token}"},
        )
