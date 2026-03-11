from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import send_admin_log_sync
from app.db.session import get_db
from app.models.referral import Referral
from app.models.user import User
from app.schemas.referral import ReferralInfo
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


@router.get("/stats")
def referral_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invited_count = (
        db.query(func.count(Referral.id))
        .filter(Referral.inviter_id == user.id)
        .scalar()
        or 0
    )
    earned = (
        db.query(func.coalesce(func.sum(Referral.total_earned_rub), 0))
        .filter(Referral.inviter_id == user.id)
        .scalar()
        or 0
    )
    link = f"{settings.telegram_miniapp_url}?startapp={user.referral_code}"

    log_audit(db, user.id, "referral_stats", {})
    send_admin_log_sync("просмотр реферальной статистики", user.telegram_id, user.username, {})

    return {
        "invited_count": invited_count,
        "earned_rub": earned,
        "commission_percent": 10,
        "link": link,
    }


@router.get("/list")
def referral_list(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Referral, User)
        .join(User, Referral.invitee_id == User.id)
        .filter(Referral.inviter_id == user.id)
        .order_by(Referral.created_at.desc())
        .all()
    )

    log_audit(db, user.id, "referral_list", {"count": len(rows)})
    send_admin_log_sync(
        "просмотр списка рефералов",
        user.telegram_id,
        user.username,
        {"Count": len(rows)},
    )

    return [
        {
            "invitee_id": invitee.telegram_id,
            "username": invitee.username,
            "created_at": referral.created_at,
            "earned_rub": referral.total_earned_rub,
        }
        for referral, invitee in rows
    ]