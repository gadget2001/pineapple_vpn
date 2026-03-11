from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import send_admin_log_sync
from app.db.session import get_db
from app.models.device import Device
from app.models.payment import Payment
from app.models.referral import Referral
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_profile import VPNProfile
from app.utils.audit import log_audit

router = APIRouter(prefix="/users", tags=["users"])


class DeviceCreate(BaseModel):
    name: str


@router.get("/me")
def get_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log_audit(db, user.id, "profile_view", {})
    send_admin_log_sync("просмотр профиля", user.telegram_id, user.username, {})
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "referral_code": user.referral_code,
    }


@router.post("/devices")
def add_device(
    payload: DeviceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = Device(user_id=user.id, name=payload.name)
    db.add(device)
    db.commit()
    log_audit(db, user.id, "device_add", {"device": payload.name})
    send_admin_log_sync(
        "добавление устройства",
        user.telegram_id,
        user.username,
        {"Device": payload.name},
    )
    return {"status": "ok"}


@router.get("/devices")
def list_devices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    devices = db.query(Device).filter(Device.user_id == user.id).all()
    log_audit(db, user.id, "device_list", {"count": len(devices)})
    send_admin_log_sync(
        "просмотр устройств",
        user.telegram_id,
        user.username,
        {"Count": len(devices)},
    )
    return [{"id": d.id, "name": d.name, "last_seen_at": d.last_seen_at} for d in devices]


@router.get("/overview")
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

    log_audit(db, user.id, "account_overview", {})
    send_admin_log_sync("открытие личного кабинета", user.telegram_id, user.username, {})

    return {
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "created_at": user.created_at,
        },
        "subscription": {
            "status": "active" if active else "expired" if sub else "none",
            "plan": sub.plan if sub else None,
            "ends_at": sub.ends_at if sub else None,
        },
        "trial": {
            "active": trial_active,
            "days": user.trial_days,
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
    }