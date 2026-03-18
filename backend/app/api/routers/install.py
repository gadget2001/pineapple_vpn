from datetime import datetime
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.subscription import Subscription
from app.models.vpn_profile import VPNProfile
from app.services.vpn_clients import platform_client
from app.services.vpn_install import (
    build_deep_link,
    build_install_fallback_url,
    parse_install_token,
    render_install_landing_html,
    target_subscription_url,
)
from app.utils.audit import log_audit

router = APIRouter(prefix="/install", tags=["VPN Install"])


def _active_subscription(db: Session, user_id: int) -> Subscription | None:
    now = datetime.utcnow()
    return (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id, Subscription.status == "active", Subscription.ends_at > now)
        .order_by(Subscription.ends_at.desc())
        .first()
    )


def _resolve(token: str, db: Session) -> tuple[dict, VPNProfile]:
    payload = parse_install_token(token)
    if not payload:
        raise HTTPException(status_code=403, detail="Install link expired or invalid")

    profile = db.query(VPNProfile).filter(VPNProfile.id == int(payload.get("pid") or 0)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if int(profile.install_link_version or 1) != int(payload.get("ver") or 0):
        raise HTTPException(status_code=403, detail="Install link is outdated")

    if not profile.is_active or not _active_subscription(db, profile.user_id):
        raise HTTPException(status_code=402, detail="Subscription is not active")

    return payload, profile


def _landing(profile: VPNProfile, payload: dict, token: str) -> str:
    platform = str(payload.get("platform") or "windows")
    client = platform_client(platform)
    subscription_url = target_subscription_url(profile, platform)
    deep_link = build_deep_link(platform, subscription_url)
    fallback_url = build_install_fallback_url(token)
    return render_install_landing_html(
        brand=settings.vpn_brand_name,
        platform=platform,
        client_name=client.client_name,
        deep_link=deep_link,
        subscription_url=subscription_url,
        fallback_url=fallback_url,
        title=profile.display_title or settings.vpn_brand_name,
    )


@router.get("", response_class=HTMLResponse)
def install_root(
    token: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    sub: str | None = Query(default=None),
    landing: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    # Compatibility endpoint: /install?platform=...&sub=...
    if platform and sub:
        try:
            client = platform_client(platform)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Unsupported platform") from exc
        deep_link = build_deep_link(platform, sub)
        if not landing and not settings.vpn_enable_install_landing:
            return RedirectResponse(url=deep_link, status_code=302)

        html = render_install_landing_html(
            brand=settings.vpn_brand_name,
            platform=platform,
            client_name=client.client_name,
            deep_link=deep_link,
            subscription_url=sub,
            fallback_url=f"/install?platform={quote_plus(platform)}&sub={quote_plus(sub)}",
            title=settings.vpn_brand_name,
        )
        return HTMLResponse(html)

    if not token:
        raise HTTPException(status_code=400, detail="token or platform/sub must be provided")

    payload, profile = _resolve(token, db)
    profile.last_install_opened_at = datetime.utcnow()
    profile.last_install_platform = str(payload.get("platform") or "")
    db.add(profile)
    db.commit()

    log_audit(db, profile.user_id, "vpn_install_link_opened", {"platform": payload.get("platform")})
    log_audit(db, profile.user_id, "vpn_install_opened", {"platform": payload.get("platform")})
    return HTMLResponse(_landing(profile, payload, token))


@router.get("/open")
def install_open(
    token: str = Query(...),
    landing: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    payload, profile = _resolve(token, db)
    platform = str(payload.get("platform") or "windows")
    subscription_url = target_subscription_url(profile, platform)
    deep_link = build_deep_link(platform, subscription_url)

    profile.last_install_opened_at = datetime.utcnow()
    profile.last_install_platform = platform
    db.add(profile)
    db.commit()

    log_audit(db, profile.user_id, "vpn_install_link_opened", {"platform": platform})
    log_audit(db, profile.user_id, "vpn_install_opened", {"platform": platform})

    if not settings.vpn_enable_install_landing and not landing:
        log_audit(db, profile.user_id, "vpn_deep_link_redirected", {"platform": platform})
        return RedirectResponse(url=deep_link, status_code=302)

    log_audit(db, profile.user_id, "vpn_deep_link_redirected", {"platform": platform, "mode": "landing"})
    return HTMLResponse(_landing(profile, payload, token))


@router.get("/fallback", response_class=HTMLResponse)
def install_fallback(
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    payload, profile = _resolve(token, db)
    log_audit(db, profile.user_id, "vpn_install_fallback_opened", {"platform": payload.get("platform")})
    return HTMLResponse(_landing(profile, payload, token))

