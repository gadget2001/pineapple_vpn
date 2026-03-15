import hashlib
import ipaddress
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
        raise ValueError("Отсутствует параметр hash в данных Telegram.")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    # Telegram MiniApp verification:
    # secret_key = HMAC_SHA256("WebAppData", bot_token)
    # (not SHA256(bot_token), that is for other auth flows).
    secret_key = hmac.new(
        b"WebAppData",
        settings.bot_token.encode(),
        hashlib.sha256,
    ).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(received_hash, computed_hash):
        if settings.telegram_debug_auth:
            raise ValueError(
                f"Неверная подпись Telegram. received={received_hash} computed={computed_hash} "
                f"data_check_string={data_check_string}"
            )
        raise ValueError("Не удалось проверить подпись Telegram. Откройте MiniApp заново.")

    auth_date = int(data.get("auth_date", "0"))
    if auth_date:
        now = int(time.time())
        if now - auth_date > max_age_seconds:
            raise ValueError("Данные авторизации устарели. Перезапустите MiniApp в Telegram.")

    return data


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    mac = hmac.new(settings.yookassa_webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, mac)



def is_ip_allowed(source_ip: str, allowed_ranges: str) -> bool:
    """Validate source IP against comma-separated CIDR/IP allowlist."""
    if not source_ip:
        return False

    allowlist = (allowed_ranges or "").strip()
    if not allowlist or allowlist == "*":
        return True

    ip_candidate = source_ip.strip()
    if ip_candidate.startswith("[") and "]" in ip_candidate:
        ip_candidate = ip_candidate[1:ip_candidate.index("]")]
    if ":" in ip_candidate and ip_candidate.count(":") == 1 and ip_candidate.rsplit(":", 1)[1].isdigit():
        # IPv4 with optional port.
        ip_candidate = ip_candidate.rsplit(":", 1)[0]

    try:
        ip_obj = ipaddress.ip_address(ip_candidate)
    except ValueError:
        return False

    for item in [x.strip() for x in allowlist.split(",") if x.strip()]:
        try:
            if "/" in item:
                if ip_obj in ipaddress.ip_network(item, strict=False):
                    return True
            else:
                if ip_obj == ipaddress.ip_address(item):
                    return True
        except ValueError:
            continue

    return False
