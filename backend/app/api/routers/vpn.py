from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import send_admin_log
from app.db.session import get_db
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_profile import VPNProfile
from app.schemas.vpn import VPNConfigOut
from app.services.vpn_delivery import issue_platform_config
from app.services.vpn_profile import get_or_create_vpn_profile, marzban_error
from app.services.vpn_subscription import (
    build_clash_subscription,
    verify_subscription_signature,
)
from app.utils.audit import log_audit

router = APIRouter(prefix="/vpn", tags=["VPN"])


def _active_subscription(db: Session, user_id: int) -> Subscription | None:
    now = datetime.utcnow()
    return (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id, Subscription.status == "active", Subscription.ends_at > now)
        .order_by(Subscription.ends_at.desc())
        .first()
    )


@router.get("/config", response_model=VPNConfigOut)
async def get_config(
    platform: str = Query(default="windows"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _active_subscription(db, user.id):
        raise HTTPException(status_code=402, detail="Для получения конфигурации нужен активный тариф или пробный период.")

    try:
        profile, created = await get_or_create_vpn_profile(db, user)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=marzban_error(exc)) from exc

    bundle = issue_platform_config(db, user=user, profile=profile, platform=platform, created=created)

    if created:
        await send_admin_log(
            "vpn_config_created",
            user.telegram_id,
            user.username,
            {
                "uuid": profile.uuid,
                "vless_url": profile.vless_url,
                "subscription_url": profile.subscription_url,
                "reality_public_key": profile.reality_public_key,
            },
        )

    log_audit(db, user.id, "vpn_config_get", {"uuid": profile.uuid, "platform": bundle.platform})

    return VPNConfigOut(
        uuid=profile.uuid,
        vless_url=profile.vless_url,
        subscription_url=bundle.subscription_url,
        subscription_url_clash=bundle.subscription_url_clash,
        raw_vless_url=bundle.raw_vless_url,
        install_urls=bundle.install_urls,
        display_title=bundle.display_title,
        display_subtitle=bundle.display_subtitle,
        reality_public_key=profile.reality_public_key,
    )


@router.get("/subscription/{kind}")
def get_public_subscription(
    kind: str,
    pid: int = Query(...),
    v: int = Query(...),
    sig: str = Query(...),
    db: Session = Depends(get_db),
):
    normalized_kind = (kind or "").strip().lower()
    if normalized_kind != "clash":
        raise HTTPException(status_code=404, detail="Unknown subscription kind")

    if not verify_subscription_signature(pid, normalized_kind, v, sig):
        raise HTTPException(status_code=403, detail="Invalid signature")

    profile = db.query(VPNProfile).filter(VPNProfile.id == pid).first()
    if not profile or int(profile.config_version or 1) != v:
        raise HTTPException(status_code=404, detail="Profile not found")

    active_sub = _active_subscription(db, profile.user_id)
    if not active_sub:
        raise HTTPException(status_code=402, detail="Subscription is not active")

    log_audit(db, profile.user_id, "vpn_subscription_opened", {"kind": normalized_kind, "profile_id": pid})

    payload = build_clash_subscription(profile)
    log_audit(db, profile.user_id, "vpn_profile_downloaded", {"kind": "clash"})
    return Response(content=payload, media_type="text/yaml; charset=utf-8")

