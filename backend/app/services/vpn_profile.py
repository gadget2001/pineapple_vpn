import httpx
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.vpn_profile import VPNProfile
from app.services.vpn_panel import create_vpn_user


async def get_or_create_vpn_profile(db: Session, user: User) -> tuple[VPNProfile, bool]:
    profile = db.query(VPNProfile).filter(VPNProfile.user_id == user.id).first()
    if profile:
        return profile, False

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
    return profile, True


def marzban_error(exc: httpx.HTTPStatusError) -> str:
    detail = exc.response.text if exc.response is not None else str(exc)
    return f"Marzban API error: {detail}"
