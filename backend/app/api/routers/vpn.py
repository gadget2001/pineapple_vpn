from fastapi import APIRouter, Depends, HTTPException
import httpx
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import send_admin_log
from app.db.session import get_db
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.vpn import VPNConfigOut
from app.services.vpn_profile import get_or_create_vpn_profile, marzban_error
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

    try:
        profile, created = await get_or_create_vpn_profile(db, user)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=marzban_error(exc)) from exc

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

    log_audit(db, user.id, "vpn_config_get", {"uuid": profile.uuid})

    return VPNConfigOut(
        uuid=profile.uuid,
        vless_url=profile.vless_url,
        subscription_url=profile.subscription_url,
        reality_public_key=profile.reality_public_key,
    )
