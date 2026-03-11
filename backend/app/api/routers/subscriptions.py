from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import send_admin_log
from app.db.session import get_db
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import (
    SubscriptionPlan,
    SubscriptionPurchaseRequest,
    SubscriptionStatus,
)
from app.utils.audit import log_audit

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

PLAN_PRICES = {
    "week": 74,
    "month": 149,
}

PLAN_DAYS = {
    "week": 7,
    "month": 30,
}


@router.get(
    "/plans",
    response_model=list[SubscriptionPlan],
    summary="Доступные тарифы",
    description="Возвращает тарифные планы для покупки из кошелька.",
)
def list_plans():
    return [
        SubscriptionPlan(code="week", title="Week", price_rub=74, duration_days=7),
        SubscriptionPlan(code="month", title="Month", price_rub=149, duration_days=30),
    ]


@router.get(
    "/status",
    response_model=SubscriptionStatus,
    summary="Статус подписки",
    description="Показывает текущий статус: active/expired/none, план, дату окончания и признак trial.",
)
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
        return SubscriptionStatus(status="none", plan=None, ends_at=None, trial=False)

    active = sub.ends_at > now and sub.status == "active"
    trial = sub.plan == "trial" and active
    return SubscriptionStatus(
        status="active" if active else "expired",
        plan=sub.plan,
        ends_at=sub.ends_at,
        trial=trial,
    )


@router.post(
    "/trial/activate",
    summary="Активировать пробный период",
    description="Однократно активирует trial (3 или 7 дней при регистрации по рефералу), если нет активной подписки.",
)
async def activate_trial(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.trial_activated_at:
        raise HTTPException(status_code=400, detail="Trial already activated")

    now = datetime.utcnow()
    current_sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.status == "active", Subscription.ends_at > now)
        .order_by(Subscription.ends_at.desc())
        .first()
    )
    if current_sub:
        raise HTTPException(status_code=400, detail="Active subscription already exists")

    ends_at = now + timedelta(days=user.trial_days)
    trial_sub = Subscription(
        user_id=user.id,
        plan="trial",
        status="active",
        price_rub=0,
        starts_at=now,
        ends_at=ends_at,
    )
    user.trial_activated_at = now
    db.add(trial_sub)
    db.commit()

    log_audit(db, user.id, "trial_activated", {"days": user.trial_days})
    await send_admin_log(
        "trial_activated",
        user.telegram_id,
        user.username,
        {"days": user.trial_days, "ends_at": ends_at.isoformat()},
    )

    return {"status": "ok", "ends_at": ends_at}


@router.post(
    "/purchase",
    summary="Купить подписку из кошелька",
    description="Списывает средства с кошелька и активирует/продлевает выбранный тариф.",
)
async def purchase_subscription(
    payload: SubscriptionPurchaseRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.plan not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail="Unknown plan")

    amount = PLAN_PRICES[payload.plan]
    if user.wallet_balance_rub < amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")

    now = datetime.utcnow()
    current_sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id)
        .order_by(Subscription.ends_at.desc())
        .first()
    )
    start_at = current_sub.ends_at if current_sub and current_sub.ends_at > now else now
    ends_at = start_at + timedelta(days=PLAN_DAYS[payload.plan])

    user.wallet_balance_rub -= amount
    sub = Subscription(
        user_id=user.id,
        plan=payload.plan,
        status="active",
        price_rub=amount,
        starts_at=start_at,
        ends_at=ends_at,
    )
    db.add(sub)
    db.commit()

    log_audit(db, user.id, "subscription_purchased", {"plan": payload.plan, "price": amount})
    await send_admin_log(
        "subscription_activated",
        user.telegram_id,
        user.username,
        {
            "plan": payload.plan,
            "price": amount,
            "wallet_balance": user.wallet_balance_rub,
        },
    )

    return {"status": "ok", "ends_at": ends_at, "wallet_balance": user.wallet_balance_rub}
