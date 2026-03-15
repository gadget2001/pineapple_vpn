from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import send_admin_log, send_user_bot_message
from app.core.security import is_ip_allowed, verify_webhook_signature
from app.db.session import get_db
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentOut
from app.services.payments_yookassa import create_yookassa_payment, get_yookassa_payment
from app.services.referral import apply_referral_commission
from app.utils.audit import log_audit

router = APIRouter(prefix="/payments", tags=["Payments"])


def _extract_source_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return ""


def _build_return_url(topup_id: int) -> str:
    parts = urlsplit(settings.frontend_url)
    query_pairs = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "topup_id"]
    query_pairs.append(("topup_id", str(topup_id)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_pairs), parts.fragment))


def _validate_amount_and_currency(payment: Payment, obj: dict) -> tuple[bool, str | None]:
    amount_data = obj.get("amount") or {}
    value_raw = amount_data.get("value")
    currency = str(amount_data.get("currency") or "").upper()

    if value_raw is None:
        return False, "\u0412 webhook \u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0443\u0435\u0442 \u0441\u0443\u043c\u043c\u0430 \u043f\u043b\u0430\u0442\u0435\u0436\u0430."

    try:
        value = Decimal(str(value_raw))
    except (InvalidOperation, TypeError, ValueError):
        return False, "\u041d\u0435\u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u0430\u044f \u0441\u0443\u043c\u043c\u0430 \u043f\u043b\u0430\u0442\u0435\u0436\u0430 \u0432 webhook."

    expected = Decimal(payment.amount_rub).quantize(Decimal("1.00"))
    if value.quantize(Decimal("1.00")) != expected:
        return False, f"\u0421\u0443\u043c\u043c\u0430 webhook ({value}) \u043d\u0435 \u0441\u043e\u0432\u043f\u0430\u0434\u0430\u0435\u0442 \u0441 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0439 ({expected})."

    if currency != "RUB":
        return False, f"\u041d\u0435\u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u0430\u044f \u0432\u0430\u043b\u044e\u0442\u0430 webhook: {currency}."

    return True, None


@router.post("/topup", response_model=PaymentOut, summary="Create wallet top-up payment")
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

    try:
        response = await create_yookassa_payment(
            amount_rub=amount,
            description=f"Pineapple VPN wallet top-up: {amount} RUB",
            return_url=_build_return_url(payment.id),
            idempotence_key=f"topup-{payment.id}",
            metadata={"local_payment_id": str(payment.id), "user_id": str(user.id), "kind": "topup"},
        )
    except Exception as exc:
        payment.status = "failed"
        payment.meta = {
            "kind": "topup",
            "error": str(exc)[:500],
            "stage": "create_yookassa_payment",
        }
        db.commit()
        raise HTTPException(
            status_code=502,
            detail="\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u043e\u0437\u0434\u0430\u0442\u044c \u043f\u043b\u0430\u0442\u0435\u0436 \u0432 \u042eKassa. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u043e\u0437\u0436\u0435.",
        ) from exc

    confirmation_url = response.get("confirmation", {}).get("confirmation_url")
    payment.provider_payment_id = response.get("id")
    payment.meta = {
        "kind": "topup",
        "yookassa": {
            "id": response.get("id"),
            "status": response.get("status"),
            "created_at": response.get("created_at"),
            "amount": response.get("amount"),
            "metadata": response.get("metadata"),
        },
    }
    db.commit()

    log_audit(db, user.id, "topup_create", {"amount": amount, "payment_id": payment.id})

    return PaymentOut(
        id=payment.id,
        amount_rub=amount,
        status=payment.status,
        confirmation_url=confirmation_url,
    )


@router.get("/{payment_id}/status", summary="Get payment status")
def payment_status(
    payment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment = db.query(Payment).filter(Payment.id == payment_id, Payment.user_id == user.id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="\u041f\u043b\u0430\u0442\u0435\u0436 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d.")

    return {
        "id": payment.id,
        "status": payment.status,
        "kind": payment.kind,
        "amount_rub": payment.amount_rub,
        "created_at": payment.created_at,
        "paid_at": payment.paid_at,
    }


@router.post("/webhook", summary="YooKassa webhook")
async def yookassa_webhook(
    request: Request,
    x_webhook_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    raw = await request.body()
    source_ip = _extract_source_ip(request)

    if not is_ip_allowed(source_ip, settings.yookassa_webhook_ips):
        raise HTTPException(
            status_code=403,
            detail="Webhook \u043e\u0442\u043a\u043b\u043e\u043d\u0435\u043d: IP-\u0430\u0434\u0440\u0435\u0441 \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u0430 \u043d\u0435 \u0440\u0430\u0437\u0440\u0435\u0448\u0435\u043d.",
        )

    # Optional compatibility check for setups that pass custom signature header.
    if x_webhook_signature and settings.yookassa_webhook_secret:
        if not verify_webhook_signature(raw, x_webhook_signature):
            raise HTTPException(status_code=403, detail="\u041d\u0435\u0432\u0435\u0440\u043d\u0430\u044f \u043f\u043e\u0434\u043f\u0438\u0441\u044c webhook.")

    payload = await request.json()
    event = payload.get("event")
    obj = payload.get("object") or {}
    provider_payment_id = obj.get("id")

    if not provider_payment_id:
        raise HTTPException(status_code=400, detail="Webhook \u043d\u0435 \u0441\u043e\u0434\u0435\u0440\u0436\u0438\u0442 payment id.")

    try:
        yookassa_payment = await get_yookassa_payment(provider_payment_id)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u0432\u0435\u0440\u0438\u0442\u044c \u043f\u043b\u0430\u0442\u0435\u0436 \u0441 \u042eKassa. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u043e\u0437\u0436\u0435.",
        ) from exc

    if isinstance(yookassa_payment, dict) and yookassa_payment.get("id") == provider_payment_id:
        obj = yookassa_payment

    payment = (
        db.query(Payment)
        .filter(Payment.provider_payment_id == provider_payment_id)
        .with_for_update()
        .first()
    )
    if not payment:
        return {"status": "ignored_unknown_payment", "payment_id": provider_payment_id}

    user = db.query(User).filter(User.id == payment.user_id).with_for_update().first()

    expected_status = {
        "payment.succeeded": "succeeded",
        "payment.canceled": "canceled",
    }.get(event)

    if not expected_status:
        return {"status": "ignored_event", "event": event}

    webhook_obj_status = str(obj.get("status") or "").lower()
    if webhook_obj_status and webhook_obj_status != expected_status:
        return {
            "status": "ignored_status_mismatch",
            "event": event,
            "object_status": webhook_obj_status,
        }

    if payment.status == "paid":
        return {"status": "ok", "already_processed": True}

    if payment.status == "canceled" and event == "payment.canceled":
        return {"status": "ok", "already_processed": True}

    if payment.status in {"failed", "canceled"} and event == "payment.succeeded":
        return {"status": "ignored_terminal_state", "payment_status": payment.status}

    ok_amount, amount_error = _validate_amount_and_currency(payment, obj)
    if not ok_amount:
        if user:
            await send_admin_log(
                "payment_error",
                user.telegram_id,
                user.username,
                {
                    "reason": amount_error,
                    "provider_payment_id": provider_payment_id,
                    "source_ip": source_ip,
                },
            )
        return {"status": "ignored_amount_mismatch"}

    if event == "payment.succeeded":
        payment.status = "paid"
        payment.paid_at = datetime.utcnow()

        if payment.kind == "topup" and user:
            user.wallet_balance_rub += payment.amount_rub

            if user.referred_by_id:
                commission = apply_referral_commission(
                    db=db,
                    inviter_id=user.referred_by_id,
                    invitee_id=user.id,
                    amount_rub=payment.amount_rub,
                )
                if commission > 0:
                    inviter = db.query(User).filter(User.id == user.referred_by_id).with_for_update().first()
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

            try:
                await send_admin_log(
                    "wallet_topup",
                    user.telegram_id,
                    user.username,
                    {
                        "amount": payment.amount_rub,
                        "wallet_balance": user.wallet_balance_rub,
                        "provider_payment_id": payment.provider_payment_id,
                    },
                )
            except Exception:
                pass

        db.commit()
        log_audit(
            db,
            payment.user_id,
            "payment_success",
            {"amount": payment.amount_rub, "kind": payment.kind, "provider_payment_id": provider_payment_id},
        )

        if payment.kind == "topup" and user:
            try:
                await send_user_bot_message(
                    user_telegram_id=user.telegram_id,
                    text=(
                        "? ?????????? ???????? ????????????.\n\n"
                        f"?????: {payment.amount_rub} ?\n"
                        f"??????: {user.wallet_balance_rub} ?"
                    ),
                    with_main_menu_button=True,
                )
            except Exception:
                pass

    elif event == "payment.canceled":
        if payment.status != "pending":
            return {"status": "ok", "already_processed": True}

        payment.status = "canceled"
        db.commit()

        if user:
            await send_admin_log(
                "payment_error",
                user.telegram_id,
                user.username,
                {
                    "reason": "payment_canceled",
                    "provider_payment_id": payment.provider_payment_id,
                },
            )

    return {"status": "ok"}


@router.get("/history", summary="Payment history")
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
