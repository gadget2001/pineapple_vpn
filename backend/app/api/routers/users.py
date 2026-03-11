from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.device import Device
from app.models.payment import Payment
from app.models.referral import Referral
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_profile import VPNProfile
from app.utils.audit import log_audit

router = APIRouter(prefix="/users", tags=["Users"])


class DeviceCreate(BaseModel):
    name: str


@router.get("/me", summary="Current user profile")
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
    }


@router.post("/devices", summary="Add user device")
def add_device(
    payload: DeviceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = Device(user_id=user.id, name=payload.name)
    db.add(device)
    db.commit()
    log_audit(db, user.id, "device_add", {"device": payload.name})
    return {"status": "ok"}


@router.get("/devices", summary="List user devices")
def list_devices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    devices = db.query(Device).filter(Device.user_id == user.id).all()
    return [{"id": d.id, "name": d.name, "last_seen_at": d.last_seen_at} for d in devices]


@router.get("/overview", summary="Dashboard overview")
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
    devices_count = (
        db.query(func.count(Device.id))
        .filter(Device.user_id == user.id)
        .scalar()
        or 0
    )
    vpn_profile = db.query(VPNProfile).filter(VPNProfile.user_id == user.id).first()

    referral_link = f"{settings.telegram_miniapp_url}?startapp={user.referral_code}"

    onboarding = {
        "trial_available": user.trial_activated_at is None,
        "wallet_ready": user.wallet_balance_rub >= 74,
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
        },
        "subscription": {
            "status": "active" if active else "expired" if sub else "none",
            "plan": sub.plan if sub else None,
            "ends_at": sub.ends_at if sub else None,
        },
        "trial": {
            "active": trial_active,
            "available": user.trial_activated_at is None,
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
        "devices": {
            "count": devices_count,
        },
        "vpn": {
            "has_profile": bool(vpn_profile),
        },
        "onboarding": onboarding,
    }