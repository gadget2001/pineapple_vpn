from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import send_admin_log
from app.core.security import verify_webhook_signature
from app.db.session import get_db
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentOut
from app.services.payments_yookassa import create_yookassa_payment
from app.services.referral import apply_referral_commission
from app.utils.audit import log_audit

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/topup",
    response_model=PaymentOut,
    summary="Создать платеж на пополнение кошелька",
    description="Создает платеж ЮKassa на пополнение баланса. Минимальная сумма задается валидатором схемы.",
)
async def create_topup_payment(
    payload: PaymentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    amount = payload.amount_rub

    payment = Payment(user_id=user.id, amount_rub=amount, status="pending", kind="topup")
    db.add(payment)
    db.commit()
    db.refresh(payment)

    response = await create_yookassa_payment(
        amount_rub=amount,
        description=f"Pineapple VPN wallet top-up: {amount} RUB",
        return_url=settings.frontend_url,
    )

    confirmation_url = response.get("confirmation", {}).get("confirmation_url")
    payment.provider_payment_id = response.get("id")
    payment.meta = {"kind": "topup", "yookassa": response}
    db.commit()

    log_audit(db, user.id, "topup_create", {"amount": amount})

    return PaymentOut(id=payment.id, amount_rub=amount, status=payment.status, confirmation_url=confirmation_url)


@router.post(
    "/webhook",
    summary="Webhook ЮKassa",
    description="Точка подтверждения оплаты от ЮKassa. При `payment.succeeded` зачисляет средства в кошелек.",
)
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

    user = db.query(User).filter(User.id == payment.user_id).first()

    if event == "payment.succeeded":
        payment.status = "paid"
        payment.paid_at = datetime.utcnow()

        if payment.kind == "topup" and user:
            user.wallet_balance_rub += payment.amount_rub
            # Referral bonus: inviter receives 10% from referred user's top-up.
            if user.referred_by_id:
                commission = apply_referral_commission(
                    db=db,
                    inviter_id=user.referred_by_id,
                    invitee_id=user.id,
                    amount_rub=payment.amount_rub,
                )
                if commission > 0:
                    inviter = db.query(User).filter(User.id == user.referred_by_id).first()
                    if inviter:
                        inviter.wallet_balance_rub += commission
                        db.add(
                            Payment(
                                user_id=inviter.id,
                                amount_rub=commission,
                                status="paid",
                                provider="internal",
                                kind="referral_bonus",
                                paid_at=datetime.utcnow(),
                                meta={"invitee_user_id": user.id, "source_payment_id": payment.id},
                            )
                        )
            await send_admin_log(
                "wallet_topup",
                user.telegram_id,
                user.username,
                {
                    "amount": payment.amount_rub,
                    "wallet_balance": user.wallet_balance_rub,
                },
            )

        db.commit()
        log_audit(db, payment.user_id, "payment_success", {"amount": payment.amount_rub, "kind": payment.kind})

    elif event == "payment.canceled":
        payment.status = "canceled"
        db.commit()
        if user:
            await send_admin_log(
                "payment_error",
                user.telegram_id,
                user.username,
                {"provider_payment_id": payment.provider_payment_id},
            )

    return {"status": "ok"}


@router.get(
    "/history",
    summary="История платежей",
    description="Возвращает последние платежи пользователя: сумма, статус, тип операции и дата.",
)
def payment_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payments = (
        db.query(Payment)
        .filter(Payment.user_id == user.id, Payment.status == "paid")
        .order_by(Payment.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": p.id,
            "amount_rub": p.amount_rub,
            "status": p.status,
            "kind": p.kind,
            "created_at": p.paid_at or p.created_at,
            "meta": p.meta or {},
        }
        for p in payments
    ]
