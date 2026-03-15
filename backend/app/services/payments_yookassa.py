import uuid
from typing import Any, Dict

import httpx

from app.core.config import settings


async def create_yookassa_payment(
    amount_rub: int,
    description: str,
    return_url: str,
    idempotence_key: str | None = None,
    metadata: dict[str, str] | None = None,
    receipt: dict[str, Any] | None = None,
) -> Dict[str, Any]:
    payload = {
        "amount": {"value": f"{amount_rub}.00", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": description,
    }
    if metadata:
        payload["metadata"] = metadata
    if receipt:
        payload["receipt"] = receipt

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            "https://api.yookassa.ru/v3/payments",
            auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
            headers={"Idempotence-Key": idempotence_key or str(uuid.uuid4())},
            json=payload,
        )
        response.raise_for_status()
        return response.json()



async def get_yookassa_payment(payment_id: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"https://api.yookassa.ru/v3/payments/{payment_id}",
            auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
        )
        response.raise_for_status()
        return response.json()
