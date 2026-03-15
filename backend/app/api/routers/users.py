import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import send_admin_log
from app.db.session import get_db
from app.models.payment import Payment
from app.models.referral import Referral
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_profile import VPNProfile
from app.utils.audit import log_audit
from app.utils.referral import build_bot_referral_link

router = APIRouter(prefix="/users", tags=["Users"])

EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")


class ConsentAcceptRequest(BaseModel):
    os: str | None = None


class ReceiptEmailUpdateRequest(BaseModel):
    email: str


def _normalize_os(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip().lower()[:32]
    if raw == "ios":
        return "iphone"
    return raw


def _normalize_receipt_email(value: str | None) -> str:
    email = (value or "").strip().lower()
    if not email:
        raise HTTPException(status_code=422, detail="Укажите email для получения кассовых чеков.")
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Укажите корректный email в формате name@example.com.")
    return email


@router.get(
    "/me",
    summary="User profile",
    description="Short profile with Telegram data, referral code and wallet balance.",
)
def get_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log_audit(db, user.id, "profile_view", {})
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "referral_code": user.referral_code,
        "wallet_balance_rub": user.wallet_balance_rub,
        "receipt_email": user.receipt_email,
    }


@router.post(
    "/consent",
    summary="Accept legal consent",
    description="Stores user consent for service rules and legal documents.",
)
async def accept_consent(
    payload: ConsentAcceptRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.terms_accepted_at:
        user.terms_accepted_at = datetime.utcnow()
    user.legal_docs_version_accepted = settings.legal_docs_version

    if payload.os:
        user.onboarding_os = _normalize_os(payload.os)

    user.onboarding_step = "trial_offer"
    db.commit()

    log_audit(db, user.id, "terms_accepted", {"os": user.onboarding_os, "docs_version": settings.legal_docs_version})
    await send_admin_log(
        "terms_accepted",
        user.telegram_id,
        user.username,
        {
            "os": user.onboarding_os or "unknown",
            "accepted_at": user.terms_accepted_at.isoformat(),
            "docs_version": settings.legal_docs_version,
        },
    )

    return {
        "status": "ok",
        "terms_accepted_at": user.terms_accepted_at,
        "os": user.onboarding_os,
        "docs_version": user.legal_docs_version_accepted,
    }


@router.get(
    "/receipt-email",
    summary="Get receipt email",
    description="Returns current email used by YooKassa to deliver fiscal receipts.",
)
def get_receipt_email(user: User = Depends(get_current_user)):
    return {"email": user.receipt_email}


@router.put(
    "/receipt-email",
    summary="Update receipt email",
    description="Updates email used in YooKassa receipt payload.",
)
def update_receipt_email(
    payload: ReceiptEmailUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email = _normalize_receipt_email(payload.email)
    user.receipt_email = email
    db.commit()

    log_audit(db, user.id, "receipt_email_updated", {"email": email})

    return {"status": "ok", "email": email}


@router.get(
    "/overview",
    summary="Account overview",
    description="Unified MiniApp dashboard payload with user, trial, subscription, wallet and onboarding state.",
)
def account_overview(
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
    active = bool(sub and sub.status == "active" and sub.ends_at > now)
    trial_active = bool(active and sub and sub.plan == "trial")
    trial_used = bool(
        user.trial_activated_at
        or db.query(Subscription.id)
        .filter(Subscription.user_id == user.id, Subscription.plan == "trial")
        .first()
    )

    invited_count = (
        db.query(func.count(Referral.id))
        .filter(Referral.inviter_id == user.id)
        .scalar()
        or 0
    )
    referral_earned = (
        db.query(func.coalesce(func.sum(Referral.total_earned_rub), 0))
        .filter(Referral.inviter_id == user.id)
        .scalar()
        or 0
    )
    payments_paid = (
        db.query(func.count(Payment.id))
        .filter(Payment.user_id == user.id, Payment.status == "paid")
        .scalar()
        or 0
    )
    payments_total = (
        db.query(func.coalesce(func.sum(Payment.amount_rub), 0))
        .filter(Payment.user_id == user.id, Payment.status == "paid")
        .scalar()
        or 0
    )
    vpn_profile = db.query(VPNProfile).filter(VPNProfile.user_id == user.id).first()

    normalized_os = _normalize_os(user.onboarding_os)
    if normalized_os != user.onboarding_os:
        user.onboarding_os = normalized_os
        db.commit()

    referral_link = build_bot_referral_link(
        referral_code=user.referral_code,
        bot_username=settings.telegram_bot_username,
        fallback_miniapp_url=settings.telegram_miniapp_url,
    )

    onboarding = {
        "step": user.onboarding_step or "welcome",
        "step_index": {
            "welcome": 1,
            "trial_offer": 2,
            "device_select": 3,
            "install_app": 4,
            "get_config": 5,
            "complete": 6,
            "done": 6,
        }.get(user.onboarding_step or "welcome", 1),
        "total_steps": 6,
        "terms_accepted": user.terms_accepted_at is not None,
        "terms_accepted_at": user.terms_accepted_at,
        "legal_docs_version_current": settings.legal_docs_version,
        "legal_docs_version_accepted": user.legal_docs_version_accepted,
        "os": normalized_os,
        "trial_available": not trial_used,
        "install_confirmed": user.onboarding_install_confirmed_at is not None,
        "completed": user.onboarding_completed_at is not None,
        "completed_at": user.onboarding_completed_at,
        "has_active_subscription": active,
        "vpn_ready": bool(vpn_profile),
    }

    log_audit(db, user.id, "account_overview", {})

    return {
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "created_at": user.created_at,
            "wallet_balance_rub": user.wallet_balance_rub,
            "receipt_email": user.receipt_email,
        },
        "subscription": {
            "status": "active" if active else "expired" if sub else "none",
            "plan": sub.plan if sub else None,
            "ends_at": sub.ends_at if sub else None,
        },
        "trial": {
            "active": trial_active,
            "available": not trial_used,
            "days": user.trial_days,
            "activated_at": user.trial_activated_at,
            "ends_at": sub.ends_at if trial_active else None,
        },
        "referral": {
            "code": user.referral_code,
            "link": referral_link,
            "invited_count": invited_count,
            "earned_rub": referral_earned,
            "commission_percent": 10,
        },
        "payments": {
            "paid_count": payments_paid,
            "paid_total_rub": payments_total,
        },
        "vpn": {
            "has_profile": bool(vpn_profile),
        },
        "onboarding": onboarding,
    }
