import base64
import re


_REF_CODE_RE = re.compile(r"^ref_\d{1,20}$")


def normalize_referral_code(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if _REF_CODE_RE.fullmatch(candidate):
        return candidate
    return None


def encode_referral_payload(referral_code: str) -> str:
    normalized = normalize_referral_code(referral_code)
    if not normalized:
        raise ValueError("Invalid referral code")
    payload = base64.urlsafe_b64encode(normalized.encode("utf-8")).decode("ascii")
    return payload.rstrip("=")


def decode_referral_payload(payload: str | None) -> str | None:
    # Backward compatibility: allow legacy raw value (ref_<telegram_id>).
    normalized = normalize_referral_code(payload)
    if normalized:
        return normalized

    if not payload:
        return None
    candidate = payload.strip()
    if not candidate:
        return None

    padding = "=" * ((4 - len(candidate) % 4) % 4)
    try:
        decoded = base64.urlsafe_b64decode(candidate + padding).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    return normalize_referral_code(decoded)


def build_bot_referral_link(
    referral_code: str,
    bot_username: str,
    fallback_miniapp_url: str | None = None,
) -> str:
    payload = encode_referral_payload(referral_code)
    username = (bot_username or "").lstrip("@").strip()
    if username:
        return f"https://t.me/{username}?start={payload}"
    if fallback_miniapp_url:
        return f"{fallback_miniapp_url}?startapp={payload}"
    return payload
