from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import send_admin_log, send_admin_log_sync
from app.core.security import verify_webhook_signature
from app.db.session import get_db
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentOut
from app.services.payments_yookassa import create_yookassa_payment
from app.services.referral import apply_referral_commission
from app.utils.audit import log_audit

router = APIRouter(prefix="/payments", tags=["payments"])

PLAN_PRICES = {
    "week": 74,
    "month": 149,
}
PLAN_DAYS = {
    "week": 7,
    "month": 30,
}


@router.post("/create", response_model=PaymentOut)
async def create_payment(
    payload: PaymentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.plan not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail="Unknown plan")

    amount = PLAN_PRICES[payload.plan]
    payment = Payment(user_id=user.id, amount_rub=amount, status="pending")
    db.add(payment)
    db.commit()
    db.refresh(payment)

    response = await create_yookassa_payment(
        amount_rub=amount,
        description=f"Pineapple VPN: {payload.plan}",
        return_url=settings.frontend_url,
    )
    confirmation_url = response.get("confirmation", {}).get("confirmation_url")
    payment.provider_payment_id = response.get("id")
    payment.meta = {"plan": payload.plan, "yookassa": response}
    db.commit()

    log_audit(db, user.id, "payment_create", {"plan": payload.plan, "amount": amount})
    await send_admin_log(
        "создание платежа",
        user.telegram_id,
        user.username,
        {"Plan": payload.plan, "Amount": amount},
    )

    return PaymentOut(id=payment.id, amount_rub=amount, status=payment.status, confirmation_url=confirmation_url)


@router.post("/webhook")
async def yookassa_webhook(
    request: Request,
    x_webhook_signature: str = Header(None),
    db: Session = Depends(get_db),
):
    raw = await request.body()
    if not x_webhook_signature or not verify_webhook_signature(raw, x_webhook_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    event = payload.get("event")
    obj = payload.get("object", {})
    payment_id = obj.get("id")

    payment = db.query(Payment).filter(Payment.provider_payment_id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if event == "payment.succeeded":
        payment.status = "paid"
        payment.paid_at = datetime.utcnow()

        plan = (payment.meta or {}).get("plan", "month")
        add_days = PLAN_DAYS.get(plan, 30)

        sub = (
            db.query(Subscription)
            .filter(Subscription.user_id == payment.user_id)
            .order_by(Subscription.ends_at.desc())
            .first()
        )

        now = datetime.utcnow()
        start = sub.ends_at if sub and sub.ends_at > now else now
        ends_at = start + timedelta(days=add_days)

        new_sub = Subscription(
            user_id=payment.user_id,
            plan=plan,
            status="active",
            price_rub=payment.amount_rub,
            starts_at=start,
            ends_at=ends_at,
        )
        db.add(new_sub)

        # Referral commission
        user = db.query(User).filter(User.id == payment.user_id).first()
        if user and user.referred_by_id:
            apply_referral_commission(db, user.referred_by_id, user.id, payment.amount_rub)

        db.commit()

        log_audit(db, payment.user_id, "payment_success", {"amount": payment.amount_rub})
        await send_admin_log(
            "успешная оплата",
            user.telegram_id if user else None,
            user.username if user else None,
            {"Amount": payment.amount_rub},
        )
    elif event == "payment.canceled":
        payment.status = "canceled"
        db.commit()
        user = db.query(User).filter(User.id == payment.user_id).first()
        log_audit(db, payment.user_id, "payment_canceled", {})
        await send_admin_log(
            "ошибка платежа",
            user.telegram_id if user else None,
            user.username if user else None,
            {"ProviderId": payment.provider_payment_id},
        )

    return {"status": "ok"}


@router.get("/history")
def payment_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payments = (
        db.query(Payment)
        .filter(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc())
        .limit(50)
        .all()
    )
    log_audit(db, user.id, "payment_history", {"count": len(payments)})
    send_admin_log_sync(
        "просмотр истории платежей",
        user.telegram_id,
        user.username,
        {"Count": len(payments)},
    )
    return [
        {
            "id": p.id,
            "amount_rub": p.amount_rub,
            "status": p.status,
            "created_at": p.created_at,
        }
        for p in payments
    ]
