from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.referral import Referral
from app.models.user import User
from app.schemas.referral import ReferralInfo
from app.utils.audit import log_audit

router = APIRouter(prefix="/referral", tags=["Referrals"])


def _build_bot_deep_link(ref_code: str) -> str:
    if settings.telegram_bot_username:
        return f"https://t.me/{settings.telegram_bot_username}?startapp={ref_code}"
    return f"{settings.telegram_miniapp_url}?startapp={ref_code}"


def _build_invite_message(link: str) -> str:
    return (
        "Привет! Пользуюсь Pineapple VPN для защищенного доступа к российским сервисам из-за границы.\n\n"
        "Сервис подходит для банков, Госуслуг и рабочих систем.\n"
        "По моей ссылке тебе дадут увеличенный пробный период 7 дней вместо 3.\n\n"
        f"Открыть: {link}"
    )


@router.get(
    "/info",
    response_model=ReferralInfo,
    summary="Реферальная ссылка",
    description="Возвращает реферальную ссылку, Telegram deep-link и готовый текст приглашения для друга.",
)
def referral_info(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bot_link = _build_bot_deep_link(user.referral_code)
    log_audit(db, user.id, "referral_info", {})
    return ReferralInfo(
        referral_code=user.referral_code,
        referral_link=f"{settings.telegram_miniapp_url}?startapp={user.referral_code}",
        bot_deep_link=bot_link,
        invite_message=_build_invite_message(bot_link),
    )


@router.get(
    "/stats",
    summary="Статистика рефералов",
    description="Показывает количество приглашенных, сумму начислений, ссылку и текст приглашения.",
)
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
    bot_link = _build_bot_deep_link(user.referral_code)

    return {
        "invited_count": invited_count,
        "earned_rub": earned,
        "commission_percent": 10,
        "link": f"{settings.telegram_miniapp_url}?startapp={user.referral_code}",
        "bot_deep_link": bot_link,
        "invite_message": _build_invite_message(bot_link),
    }


@router.get(
    "/list",
    summary="Список приглашенных",
    description="Список пользователей, зарегистрированных по вашей реферальной ссылке.",
)
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

    return [
        {
            "invitee_id": invitee.telegram_id,
            "username": invitee.username,
            "created_at": referral.created_at,
            "earned_rub": referral.total_earned_rub,
        }
        for referral, invitee in rows
    ]
