from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
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
    build_hiddify_subscription,
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


def _pending_trial_subscription(db: Session, user_id: int) -> Subscription | None:
    return (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id, Subscription.plan == "trial", Subscription.status == "pending")
        .order_by(Subscription.created_at.desc())
        .first()
    )


def _eligible_subscription_for_config(db: Session, user: User) -> Subscription | None:
    active = _active_subscription(db, user.id)
    if active:
        return active
    return _pending_trial_subscription(db, user.id)


def _activate_pending_trial_if_needed(db: Session, user: User, sub: Subscription | None) -> None:
    if not sub or sub.plan != "trial" or sub.status != "pending":
        return
    now = datetime.utcnow()
    sub.status = "active"
    sub.starts_at = now
    sub.ends_at = now + timedelta(days=user.trial_days)
    user.trial_activated_at = now
    db.add(sub)
    db.add(user)
    db.commit()


def _build_subscription_headers(profile: VPNProfile, active_sub: Subscription | None) -> dict[str, str]:
    title = (profile.display_title or "Pineapple VPN").strip()
    daily_limit_gb = int(settings.vpn_daily_data_limit_gb or 40)
    total_bytes = max(daily_limit_gb, 1) * 1024 * 1024 * 1024
    expire_ts = int(active_sub.ends_at.timestamp()) if active_sub and active_sub.ends_at else 0
    userinfo = f"upload=0; download=0; total={total_bytes}; expire={expire_ts}"
    dns_header = ",".join([x.strip() for x in (settings.vpn_primary_dns or "77.88.8.8,1.1.1.1").split(",") if x.strip()])
    return {
        "Profile-Title": title,
        "profile-update-interval": "24",
        "subscription-userinfo": userinfo,
        "DNS": dns_header or "77.88.8.8,1.1.1.1",
    }


@router.get("/config", response_model=VPNConfigOut)
async def get_config(
    platform: str = Query(default="windows"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    eligible_sub = _eligible_subscription_for_config(db, user)
    if not eligible_sub:
        raise HTTPException(status_code=402, detail="Active plan or trial is required to issue VPN config.")
    _activate_pending_trial_if_needed(db, user, eligible_sub)

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
    if normalized_kind not in {"clash", "hiddify"}:
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

    if normalized_kind == "hiddify":
        payload = build_hiddify_subscription(profile)
        if not payload:
            raise HTTPException(status_code=422, detail="Profile does not contain valid v2ray sublink")
        log_audit(db, profile.user_id, "vpn_profile_downloaded", {"kind": "hiddify"})
        return Response(
            content=payload,
            media_type="text/plain",
        )

    payload = build_clash_subscription(profile)
    log_audit(db, profile.user_id, "vpn_profile_downloaded", {"kind": "clash"})
    return Response(
        content=payload,
        media_type="text/yaml; charset=utf-8",
        headers=_build_subscription_headers(profile, active_sub),
    )

