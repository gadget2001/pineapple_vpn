from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import send_admin_log
from app.db.session import get_db
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_profile import VPNProfile
from app.schemas.vpn import VPNConfigOut
from app.services.vpn_panel import create_vpn_user
from app.utils.audit import log_audit

router = APIRouter(prefix="/vpn", tags=["vpn"])


@router.get("/config", response_model=VPNConfigOut)
async def get_config(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.status == "active")
        .order_by(Subscription.ends_at.desc())
        .first()
    )
    if not sub:
        raise HTTPException(status_code=402, detail="Subscription required")

    profile = db.query(VPNProfile).filter(VPNProfile.user_id == user.id).first()
    if not profile:
        panel_data = await create_vpn_user(user.telegram_id, user.username)
        profile = VPNProfile(
            user_id=user.id,
            uuid=panel_data.get("uuid", ""),
            vless_url=panel_data.get("vless_url", ""),
            subscription_url=panel_data.get("subscription_url", ""),
            reality_public_key=panel_data.get("reality_public_key"),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    log_audit(db, user.id, "vpn_config_view", {"uuid": profile.uuid})
    await send_admin_log(
        "просмотр VPN конфигурации",
        user.telegram_id,
        user.username,
        {"UUID": profile.uuid},
    )

    return VPNConfigOut(
        uuid=profile.uuid,
        vless_url=profile.vless_url,
        subscription_url=profile.subscription_url,
        reality_public_key=profile.reality_public_key,
    )
