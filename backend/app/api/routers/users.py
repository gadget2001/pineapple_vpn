from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.device import Device
from app.models.user import User
from app.core.logging import send_admin_log_sync
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
