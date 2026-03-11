from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.referral import ReferralInfo
from app.core.logging import send_admin_log_sync
from app.utils.audit import log_audit

router = APIRouter(prefix="/referral", tags=["referral"])


@router.get("/info", response_model=ReferralInfo)
def referral_info(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    link = f"{settings.telegram_miniapp_url}?startapp={user.referral_code}"
    log_audit(db, user.id, "referral_info", {})
    send_admin_log_sync("переход к реферальной ссылке", user.telegram_id, user.username, {})
    return ReferralInfo(referral_code=user.referral_code, referral_link=link)
