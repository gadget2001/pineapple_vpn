import uuid
from typing import Any, Dict

import httpx

from app.core.config import settings


async def create_yookassa_payment(amount_rub: int, description: str, return_url: str) -> Dict[str, Any]:
    idempotence_key = str(uuid.uuid4())
    payload = {
        "amount": {"value": f"{amount_rub}.00", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": description,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            "https://api.yookassa.ru/v3/payments",
            auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
            headers={"Idempotence-Key": idempotence_key},
            json=payload,
        )
        response.raise_for_status()
        return response.json()
