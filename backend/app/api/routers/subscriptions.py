from datetime import datetime, timedelta
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import send_admin_log, send_user_bot_message
from app.db.session import get_db
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.user import User
from app.services.vpn_profile import get_or_create_vpn_profile
from app.schemas.subscription import (
    SubscriptionPlan,
    SubscriptionPurchaseRequest,
    SubscriptionStatus,
)
from app.utils.audit import log_audit
from app.utils.plans import PLAN_DAYS, available_plans, plan_prices
from app.utils.trial_state import mark_trial_used

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


def _absolute_subscription_url(raw_url: str | None) -> str:
    if not raw_url:
        return ""
    if raw_url.startswith("http://") or raw_url.startswith("https://"):
        return raw_url
    if not raw_url.startswith("/"):
        return raw_url

    base = (settings.panel_url or "").strip()
    if not (base.startswith("http://") or base.startswith("https://")):
        return raw_url

    parts = urlsplit(base)
    return urlunsplit((parts.scheme, parts.netloc, raw_url, "", ""))


@router.get(
    "/plans",
    response_model=list[SubscriptionPlan],
    summary="Доступные тарифы",
    description="Возвращает тарифные планы для покупки из кошелька.",
)
def list_plans():
    return available_plans()


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
    trial_exists = (
        db.query(Subscription.id)
        .filter(Subscription.user_id == user.id, Subscription.plan == "trial")
        .first()
        is not None
    )
    if user.trial_activated_at or trial_exists:
        if not user.trial_activated_at and trial_exists:
            first_trial = (
                db.query(Subscription)
                .filter(Subscription.user_id == user.id, Subscription.plan == "trial")
                .order_by(Subscription.starts_at.asc())
                .first()
            )
            user.trial_activated_at = (first_trial.starts_at if first_trial else datetime.utcnow())
            db.commit()
            await mark_trial_used(user.telegram_id)
        raise HTTPException(status_code=400, detail="Пробный период уже был активирован.")

    now = datetime.utcnow()
    current_sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.status == "active", Subscription.ends_at > now)
        .order_by(Subscription.ends_at.desc())
        .first()
    )
    if current_sub:
        raise HTTPException(status_code=400, detail="У вас уже есть активная подписка.")

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
    if user.onboarding_step in ("welcome", "trial_offer"):
        user.onboarding_step = "device_select"
    db.add(trial_sub)
    db.commit()
    await mark_trial_used(user.telegram_id)

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
    prices = plan_prices()
    if payload.plan not in prices:
        raise HTTPException(status_code=400, detail="Неизвестный тариф.")

    amount = prices[payload.plan]
    if user.wallet_balance_rub < amount:
        raise HTTPException(status_code=400, detail="Недостаточно средств на кошельке.")

    now = datetime.utcnow()
    current_sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id)
        .order_by(Subscription.ends_at.desc())
        .first()
    )

    is_renewal = bool(current_sub and current_sub.status == "active" and current_sub.ends_at > now)
    start_at = current_sub.ends_at if is_renewal else now
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
    db.add(
        Payment(
            user_id=user.id,
            amount_rub=amount,
            status="paid",
            provider="internal",
            kind="subscription_debit",
            paid_at=now,
            meta={"plan": payload.plan, "renewal": is_renewal},
        )
    )
    db.commit()

    subscription_url = None
    config_sent_to_bot = False

    if not is_renewal:
        try:
            profile, _created = await get_or_create_vpn_profile(db, user)
            subscription_url = _absolute_subscription_url(profile.subscription_url)

            if subscription_url:
                await send_user_bot_message(
                    user_telegram_id=user.telegram_id,
                    text=(
                        f"Новый VPN-ключ готов.\n\nКонфигурация VPN:\n{subscription_url}\n\nСкопируйте ссылку и добавьте ее в VPN-клиент.\nИнструкция: откройте MiniApp → вкладка «Настройка»."
                    ),
                    with_main_menu_button=True,
                )
                config_sent_to_bot = True
        except httpx.HTTPError as exc:
            await send_admin_log(
                "payment_error",
                user.telegram_id,
                user.username,
                {
                    "reason": "subscription_purchased_but_config_issue",
                    "error": str(exc),
                },
            )

    log_audit(
        db,
        user.id,
        "subscription_purchased",
        {
            "plan": payload.plan,
            "price": amount,
            "renewal": is_renewal,
            "config_sent_to_bot": config_sent_to_bot,
        },
    )
    await send_admin_log(
        "subscription_activated",
        user.telegram_id,
        user.username,
        {
            "plan": payload.plan,
            "price": amount,
            "wallet_balance": user.wallet_balance_rub,
            "renewal": is_renewal,
            "config_sent_to_bot": config_sent_to_bot,
        },
    )

    return {
        "status": "ok",
        "ends_at": ends_at,
        "wallet_balance": user.wallet_balance_rub,
        "is_renewal": is_renewal,
        "subscription_url": subscription_url,
    }
