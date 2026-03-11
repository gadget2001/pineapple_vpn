from typing import Any, Dict

import httpx

from app.core.config import settings


async def create_vpn_user(telegram_id: int, username: str | None) -> Dict[str, Any]:
    payload = {
        "username": f"tg_{telegram_id}",
        "inbounds": {"vless": ["reality"]},
        "data_limit": settings.vpn_limit_mbps * 1024 * 1024,
        "expire": 0,
        "note": username or "",
        "max_ip": settings.vpn_max_connections,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{settings.panel_url}/api/user",
            headers={"Authorization": f"Bearer {settings.panel_token}"},
            json=payload,
        )
        response.raise_for_status()
        return response.json()


async def disable_vpn_user(telegram_id: int):
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(
            f"{settings.panel_url}/api/user/disable/tg_{telegram_id}",
            headers={"Authorization": f"Bearer {settings.panel_token}"},
        )
