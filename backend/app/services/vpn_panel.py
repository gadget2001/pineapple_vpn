from typing import Any, Dict

import httpx

from app.core.config import settings


_cached_panel_token: str = settings.panel_token or ""


def _normalize_panel_url() -> str:
    return settings.panel_url.rstrip("/")


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _refresh_panel_token(client: httpx.AsyncClient) -> str:
    global _cached_panel_token

    if not settings.panel_username or not settings.panel_password:
        raise httpx.HTTPStatusError(
            "Could not validate credentials. Configure PANEL_TOKEN or PANEL_USERNAME/PANEL_PASSWORD.",
            request=httpx.Request("POST", f"{_normalize_panel_url()}/api/admin/token"),
            response=httpx.Response(401, text="Missing panel credentials"),
        )

    response = await client.post(
        f"{_normalize_panel_url()}/api/admin/token",
        data={
            "username": settings.panel_username,
            "password": settings.panel_password,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    response.raise_for_status()

    payload = response.json() if response.content else {}
    token = payload.get("access_token") or payload.get("token")
    if not token:
        raise httpx.HTTPStatusError(
            "Marzban token response does not contain access_token",
            request=response.request,
            response=httpx.Response(401, text=str(payload)),
        )

    _cached_panel_token = str(token)
    return _cached_panel_token


async def _request_with_auth(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    retry_on_401: bool = True,
    **kwargs,
) -> httpx.Response:
    global _cached_panel_token

    token = _cached_panel_token or settings.panel_token
    response = await client.request(method, f"{_normalize_panel_url()}{path}", headers=_auth_headers(token), **kwargs)
    if response.status_code != 401 or not retry_on_401:
        return response

    token = await _refresh_panel_token(client)
    return await client.request(method, f"{_normalize_panel_url()}{path}", headers=_auth_headers(token), **kwargs)


def _extract_profile(response_data: Dict[str, Any]) -> Dict[str, Any]:
    links = response_data.get("links", [])
    vless_url = ""
    subscription_url = response_data.get("subscription_url", "")

    if isinstance(links, list) and links:
        vless_url = links[0]

    if not subscription_url:
        subscription_url = response_data.get("subscription_url", "")
    if subscription_url and subscription_url.startswith("/"):
        subscription_url = f"{_normalize_panel_url()}{subscription_url}"

    return {
        "uuid": response_data.get("proxies", {}).get("vless", {}).get("id", "")
        or response_data.get("uuid", ""),
        "vless_url": vless_url or response_data.get("vless_url", ""),
        "subscription_url": subscription_url,
        "reality_public_key": response_data.get("reality_public_key")
        or response_data.get("proxies", {}).get("vless", {}).get("reality_settings", {}).get("public_key"),
    }


async def _get_existing_user(client: httpx.AsyncClient, username: str) -> Dict[str, Any] | None:
    response = await _request_with_auth(client, "GET", f"/api/user/{username}")
    if response.is_success:
        return response.json()
    return None


async def _get_vless_inbounds(client: httpx.AsyncClient) -> list[str]:
    response = await _request_with_auth(client, "GET", "/api/inbounds")
    if not response.is_success:
        return []

    data = response.json()
    names: list[str] = []

    if isinstance(data, list):
        for inbound in data:
            if not isinstance(inbound, dict):
                continue
            tag = inbound.get("tag") or inbound.get("name")
            protocol = str(inbound.get("protocol") or "").lower()
            if tag and protocol == "vless":
                names.append(str(tag))
        return names

    if not isinstance(data, dict):
        return names

    inbounds = data.get("inbounds")
    if isinstance(inbounds, list):
        for inbound in inbounds:
            if not isinstance(inbound, dict):
                continue
            tag = inbound.get("tag") or inbound.get("name")
            protocol = str(inbound.get("protocol") or "").lower()
            if tag and protocol == "vless":
                names.append(str(tag))

    vless_block = data.get("vless")
    if isinstance(vless_block, list):
        for item in vless_block:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                tag = item.get("tag") or item.get("name")
                if tag:
                    names.append(str(tag))
    elif isinstance(vless_block, dict):
        for key, value in vless_block.items():
            if isinstance(value, dict):
                tag = value.get("tag") or value.get("name") or key
                if tag:
                    names.append(str(tag))
            elif isinstance(key, str):
                names.append(key)

    return list(dict.fromkeys([n for n in names if n]))


async def create_vpn_user(telegram_id: int, username: str | None) -> Dict[str, Any]:
    uname = f"tg_{telegram_id}"

    async with httpx.AsyncClient(timeout=20) as client:
        existing = await _get_existing_user(client, uname)
        if existing:
            return _extract_profile(existing)

        discovered_inbounds = await _get_vless_inbounds(client)
        inbound_candidates = [settings.panel_inbound_name]
        inbound_candidates.extend(discovered_inbounds)
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
            response = await _request_with_auth(client, "POST", "/api/user", json=payload)
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
        await _request_with_auth(client, "POST", f"/api/user/disable/tg_{telegram_id}")
