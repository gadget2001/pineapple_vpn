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
        subscription_url = response_data.get("subscription_url", "")

    return {
        "uuid": response_data.get("proxies", {}).get("vless", {}).get("id", "")
        or response_data.get("uuid", ""),
        "vless_url": vless_url or response_data.get("vless_url", ""),
        "subscription_url": subscription_url,
        "reality_public_key": response_data.get("reality_public_key")
        or response_data.get("proxies", {}).get("vless", {}).get("reality_settings", {}).get("public_key"),
    }


async def _get_existing_user(client: httpx.AsyncClient, username: str) -> Dict[str, Any] | None:
    response = await client.get(
        f"{_normalize_panel_url()}/api/user/{username}",
        headers={"Authorization": f"Bearer {settings.panel_token}"},
    )
    if response.is_success:
        return response.json()
    return None


async def _get_vless_inbounds(client: httpx.AsyncClient) -> list[str]:
    response = await client.get(
        f"{_normalize_panel_url()}/api/inbounds",
        headers={"Authorization": f"Bearer {settings.panel_token}"},
    )
    if not response.is_success:
        return []

    data = response.json()
    inbounds = data if isinstance(data, list) else data.get("inbounds", [])

    names: list[str] = []
    for inbound in inbounds:
        tag = inbound.get("tag") or inbound.get("name")
        protocol = (inbound.get("protocol") or "").lower()
        if tag and protocol == "vless":
            names.append(tag)
    return names


async def create_vpn_user(telegram_id: int, username: str | None) -> Dict[str, Any]:
    uname = f"tg_{telegram_id}"

    async with httpx.AsyncClient(timeout=20) as client:
        existing = await _get_existing_user(client, uname)
        if existing:
            return _extract_profile(existing)

        discovered_inbounds = await _get_vless_inbounds(client)
        inbound_candidates = [settings.panel_inbound_name]
        inbound_candidates.extend(discovered_inbounds)

        # Remove duplicates while preserving order
        unique_inbounds = list(dict.fromkeys([i for i in inbound_candidates if i]))

        base_payload = {
            "username": uname,
            "note": username or "",
            "status": "active",
            "expire": 0,
            "data_limit": 0,
            "data_limit_reset_strategy": "no_reset",
            "inbounds": {"vless": []},
            "proxies": {"vless": {}},
        }

        last_error: str | None = None
        for inbound_name in unique_inbounds:
            payload = {**base_payload, "inbounds": {"vless": [inbound_name]}}
            response = await client.post(
                f"{_normalize_panel_url()}/api/user",
                headers={"Authorization": f"Bearer {settings.panel_token}"},
                json=payload,
            )
            if response.is_success:
                details = await _get_existing_user(client, uname)
                return _extract_profile(details or response.json())
            last_error = response.text

        available = ", ".join(discovered_inbounds) if discovered_inbounds else "не удалось получить список inbound из панели"
        configured = settings.panel_inbound_name
        raise httpx.HTTPStatusError(
            (
                "Failed to create Marzban user. "
                f"Configured PANEL_INBOUND_NAME='{configured}'. "
                f"Discovered VLESS inbounds: {available}. "
                f"Last response: {last_error}"
            ),
            request=httpx.Request("POST", f"{_normalize_panel_url()}/api/user"),
            response=httpx.Response(422, text=last_error or "Unprocessable Entity"),
        )


async def disable_vpn_user(telegram_id: int):
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(
            f"{_normalize_panel_url()}/api/user/disable/tg_{telegram_id}",
            headers={"Authorization": f"Bearer {settings.panel_token}"},
        )
