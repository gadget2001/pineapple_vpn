import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from urllib.parse import parse_qsl

from jose import jwt

from app.core.config import settings


def create_access_token(subject: str, is_admin: bool, expires_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload = {
        "sub": subject,
        "is_admin": is_admin,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])


def verify_telegram_init_data(init_data: str, max_age_seconds: int = 86400) -> Dict[str, Any]:
    data = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(settings.bot_token.encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(received_hash, computed_hash):
        raise ValueError("Invalid hash")

    auth_date = int(data.get("auth_date", "0"))
    if auth_date:
        now = int(time.time())
        if now - auth_date > max_age_seconds:
            raise ValueError("Auth data expired")

    return data


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    mac = hmac.new(settings.yookassa_webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, mac)
