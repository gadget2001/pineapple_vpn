from fastapi import APIRouter, Depends, HTTPException
import httpx
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

router = APIRouter(prefix="/vpn", tags=["VPN"])


@router.get(
    "/config",
    response_model=VPNConfigOut,
    summary="Получить или создать VPN-конфиг",
    description=(
        "При активной подписке возвращает VPN-профиль пользователя. "
        "Если профиль отсутствует, создаёт пользователя в Marzban и сохраняет UUID/VLESS/subscription URL."
    ),
)
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
        try:
            panel_data = await create_vpn_user(user.telegram_id, user.username)
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            raise HTTPException(status_code=502, detail=f"Marzban API error: {detail}") from exc
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

    log_audit(db, user.id, "vpn_config_get", {"uuid": profile.uuid})

    return VPNConfigOut(
        uuid=profile.uuid,
        vless_url=profile.vless_url,
        subscription_url=profile.subscription_url,
        reality_public_key=profile.reality_public_key,
    )
