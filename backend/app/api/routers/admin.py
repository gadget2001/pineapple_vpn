from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.db.session import get_db
from app.models.payment import Payment
from app.models.referral import Referral
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.admin import AdminMetrics

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/metrics",
    response_model=AdminMetrics,
    summary="Ключевые метрики",
    description="Сводные метрики: пользователи, активные подписки, общий оплаченный доход.",
)
def metrics(
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    users_total = db.query(func.count(User.id)).scalar() or 0
    active_subscriptions = (
        db.query(func.count(Subscription.id))
        .filter(Subscription.status == "active")
        .scalar()
        or 0
    )
    revenue_total = (
        db.query(func.coalesce(func.sum(Payment.amount_rub), 0))
        .filter(Payment.status == "paid")
        .scalar()
        or 0
    )
    return AdminMetrics(
        users_total=users_total,
        active_subscriptions=active_subscriptions,
        revenue_total=revenue_total,
    )


@router.get(
    "/users",
    summary="Список пользователей",
    description="Возвращает последних зарегистрированных пользователей для админ-панели.",
)
def list_users(
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.created_at.desc()).limit(200).all()
    return [
        {
            "id": u.id,
            "telegram_id": u.telegram_id,
            "username": u.username,
            "created_at": u.created_at,
            "trial_days": u.trial_days,
        }
        for u in users
    ]


@router.get(
    "/subscriptions",
    summary="Список подписок",
    description="Возвращает последние подписки с планом, статусом, ценой и сроком окончания.",
)
def list_subscriptions(
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    subs = (
        db.query(Subscription)
        .order_by(Subscription.ends_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "plan": s.plan,
            "status": s.status,
            "ends_at": s.ends_at,
            "price_rub": s.price_rub,
        }
        for s in subs
    ]


@router.get(
    "/payments",
    summary="Список платежей",
    description="Возвращает последние платежи пользователей.",
)
def list_payments(
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(200).all()
    return [
        {
            "id": p.id,
            "user_id": p.user_id,
            "amount_rub": p.amount_rub,
            "status": p.status,
            "created_at": p.created_at,
        }
        for p in payments
    ]


@router.get(
    "/referrals",
    summary="Список рефералов",
    description="Возвращает последние реферальные связи и накопленную комиссию.",
)
def list_referrals(
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    rows = db.query(Referral).order_by(Referral.created_at.desc()).limit(200).all()
    return [
        {
            "id": r.id,
            "inviter_id": r.inviter_id,
            "invitee_id": r.invitee_id,
            "total_earned_rub": r.total_earned_rub,
            "created_at": r.created_at,
        }
        for r in rows
    ]
