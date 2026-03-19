from __future__ import annotations

import base64
import json
from datetime import datetime
from urllib.parse import quote

from app.core.config import settings
from app.models.vpn_profile import VPNProfile


def _normalize_vless_for_export(raw: str) -> str:
    return (raw or "").strip()


def build_v2raytun_subscription(profile: VPNProfile) -> str:
    raw = _normalize_vless_for_export(profile.raw_vless_url or profile.vless_url)
    return f"{raw}\n"


def resolve_v2raytun_routing_base64() -> str:
    raw = (settings.vpn_v2raytun_routing_base64 or "").strip()
    if not raw:
        raise ValueError("VPN_V2RAYTUN_ROUTING_BASE64 is required for iPhone subscription flow")
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        json.loads(decoded)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("VPN_V2RAYTUN_ROUTING_BASE64 must be valid base64-encoded JSON") from exc
    return raw


def _default_total_bytes() -> int:
    # Expose a sane quota hint to the client without changing subscription business logic.
    gb_per_month_hint = max(int(settings.vpn_daily_data_limit_gb or 40), 1) * 30
    return gb_per_month_hint * 1024 * 1024 * 1024


def build_v2raytun_headers(
    *,
    profile: VPNProfile,
    expire_at: datetime | None,
    total_bytes: int | None = None,
) -> dict[str, str]:
    expire_ts = int(expire_at.timestamp()) if expire_at else 0
    total = int(total_bytes or _default_total_bytes())
    profile_title = profile.display_title or settings.vpn_v2raytun_profile_name

    headers = {
        "profile-title": profile_title,
        "subscription-userinfo": f"upload=0; download=0; total={total}; expire={expire_ts}",
        "profile-update-interval": str(int(settings.vpn_v2raytun_profile_update_interval_hours or 24)),
        "routing": resolve_v2raytun_routing_base64(),
        "update-always": "true" if settings.vpn_v2raytun_update_always else "false",
    }

    announce = (settings.vpn_v2raytun_announce or "").strip()
    announce_url = (settings.vpn_v2raytun_announce_url or "").strip()
    if announce:
        headers["announce"] = announce
    if announce_url:
        headers["announce-url"] = announce_url
    return headers


def build_v2raytun_install_link(subscription_url: str) -> str:
    encoded_url = quote(subscription_url, safe="")
    template = settings.vpn_ios_v2raytun_scheme
    if "{url}" in template:
        return template.replace("{url}", encoded_url)
    if template.endswith("/"):
        return f"{template}{encoded_url}"
    return f"{template}/{encoded_url}"
