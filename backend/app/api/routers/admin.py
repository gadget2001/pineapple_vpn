from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.db.session import get_db
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.admin import AdminMetrics

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics", response_model=AdminMetrics)
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


@router.get("/users")
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
