from __future__ import annotations

from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.vpn_profile import VPNProfile
from app.services.vpn_delivery import ensure_profile_metadata, refresh_platform_urls
from app.services.vpn_panel import create_vpn_user
from app.services.vpn_subscription import parse_vless


def _sync_profile_from_panel(profile: VPNProfile, panel_data: dict) -> bool:
    changed = False

    panel_vless = panel_data.get("vless_url") or ""
    panel_subscription = panel_data.get("subscription_url") or ""
    panel_uuid = panel_data.get("uuid") or ""
    panel_pk = panel_data.get("reality_public_key")

    direct_mappings = {
        "uuid": panel_uuid,
        "vless_url": panel_vless,
        "subscription_url": panel_subscription,
        "raw_vless_url": panel_vless,
        "reality_public_key": panel_pk,
    }

    for field, value in direct_mappings.items():
        old = getattr(profile, field)
        if old != value:
            setattr(profile, field, value)
            changed = True

    parsed = parse_vless(panel_vless)
    parsed_updates = {
        "server_host": parsed.get("host") or "",
        "server_port": parsed.get("port") or 443,
        "transport_type": parsed.get("transport") or "tcp",
        "security_type": parsed.get("security") or "reality",
        "reality_short_id": parsed.get("short_id") or None,
        "reality_sni": parsed.get("sni") or None,
    }
    for field, value in parsed_updates.items():
        old = getattr(profile, field)
        if old != value:
            setattr(profile, field, value)
            changed = True

    profile.last_synced_at = datetime.utcnow()
    profile.is_active = True
    return changed


async def get_or_create_vpn_profile(db: Session, user: User) -> tuple[VPNProfile, bool]:
    # Keep live-sync with panel to avoid stale data after user recreation in Marzban.
    profile = db.query(VPNProfile).filter(VPNProfile.user_id == user.id).first()
    preferred_uuid = profile.uuid if profile and profile.uuid else None
    panel_data = await create_vpn_user(user.telegram_id, user.username, preferred_uuid=preferred_uuid)

    if profile:
        changed = _sync_profile_from_panel(profile, panel_data)
        ensure_profile_metadata(profile)
        refresh_platform_urls(profile)
        if changed:
            profile.config_version = int(profile.config_version or 1) + 1

        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile, False

    profile = VPNProfile(
        user_id=user.id,
        uuid=panel_data.get("uuid", ""),
        vless_url=panel_data.get("vless_url", ""),
        raw_vless_url=panel_data.get("vless_url", ""),
        subscription_url=panel_data.get("subscription_url", ""),
        reality_public_key=panel_data.get("reality_public_key"),
        issued_platforms=[],
        config_version=1,
        install_link_version=1,
    )
    ensure_profile_metadata(profile)
    db.add(profile)
    db.flush()
    refresh_platform_urls(profile)

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile, True


def marzban_error(exc: httpx.HTTPStatusError) -> str:
    detail = exc.response.text if exc.response is not None else str(exc)
    return f"Marzban API error: {detail}"

