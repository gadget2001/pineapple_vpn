from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import SubscriptionStatus
from app.core.logging import send_admin_log_sync
from app.utils.audit import log_audit

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/status", response_model=SubscriptionStatus)
def subscription_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id)
        .order_by(Subscription.ends_at.desc())
        .first()
    )

    if not sub:
        log_audit(db, user.id, "subscription_status", {"status": "none"})
        send_admin_log_sync(
            "проверка подписки",
            user.telegram_id,
            user.username,
            {"Status": "none"},
        )
        return SubscriptionStatus(status="none", plan=None, ends_at=None, trial=False)

    active = sub.ends_at > now and sub.status == "active"
    trial = sub.plan == "trial" and active
    log_audit(db, user.id, "subscription_status", {"status": "active" if active else "expired"})
    send_admin_log_sync(
        "проверка подписки",
        user.telegram_id,
        user.username,
        {"Status": "active" if active else "expired"},
    )
    return SubscriptionStatus(
        status="active" if active else "expired",
        plan=sub.plan,
        ends_at=sub.ends_at,
        trial=trial,
    )
