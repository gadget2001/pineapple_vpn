from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
import httpx

from app.api.deps import get_admin_user
from app.core.config import settings
from app.core.logging import send_admin_log
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.connection_log import ConnectionLog
from app.models.device import Device
from app.models.payment import Payment
from app.models.referral import Referral
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_profile import VPNProfile
from app.schemas.admin import AdminMetrics

router = APIRouter(prefix="/admin", tags=["admin"])


class PurgeUserRequest(BaseModel):
    telegram_id: int


@router.get(
    "/metrics",
    response_model=AdminMetrics,
    summary="Ключевые метрики",
    description="Сводные метрики: пользователи, активные подписки, общий оплаченный доход.",
)
def metrics(
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    users_total = db.query(func.count(User.id)).scalar() or 0
    active_subscriptions = (
        db.query(func.count(Subscription.id))
        .filter(Subscription.status == "active")
        .scalar()
        or 0
    )
    revenue_total = (
        db.query(func.coalesce(func.sum(Payment.amount_rub), 0))
        .filter(Payment.status == "paid")
        .scalar()
        or 0
    )
    return AdminMetrics(
        users_total=users_total,
        active_subscriptions=active_subscriptions,
        revenue_total=revenue_total,
    )


@router.get(
    "/users",
    summary="Список пользователей",
    description="Возвращает последних зарегистрированных пользователей для админ-панели.",
)
def list_users(
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.created_at.desc()).limit(200).all()
    return [
        {
            "id": u.id,
            "telegram_id": u.telegram_id,
            "username": u.username,
            "created_at": u.created_at,
            "trial_days": u.trial_days,
        }
        for u in users
    ]


@router.get(
    "/subscriptions",
    summary="Список подписок",
    description="Возвращает последние подписки с планом, статусом, ценой и сроком окончания.",
)
def list_subscriptions(
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    subs = (
        db.query(Subscription)
        .order_by(Subscription.ends_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "plan": s.plan,
            "status": s.status,
            "ends_at": s.ends_at,
            "price_rub": s.price_rub,
        }
        for s in subs
    ]


@router.get(
    "/payments",
    summary="Список платежей",
    description="Возвращает последние платежи пользователей.",
)
def list_payments(
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(200).all()
    return [
        {
            "id": p.id,
            "user_id": p.user_id,
            "amount_rub": p.amount_rub,
            "status": p.status,
            "created_at": p.created_at,
        }
        for p in payments
    ]


@router.get(
    "/referrals",
    summary="Список рефералов",
    description="Возвращает последние реферальные связи и накопленную комиссию.",
)
def list_referrals(
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    rows = db.query(Referral).order_by(Referral.created_at.desc()).limit(200).all()
    return [
        {
            "id": r.id,
            "inviter_id": r.inviter_id,
            "invitee_id": r.invitee_id,
            "total_earned_rub": r.total_earned_rub,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.post(
    "/users/purge",
    summary="Полное удаление пользователя",
    description="Полностью удаляет пользователя по Telegram ID вместе со связанными записями и пытается удалить его из Marzban.",
)
async def purge_user(
    payload: PurgeUserRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.telegram_id == payload.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user.id
    username = user.username

    db.query(ConnectionLog).filter(ConnectionLog.user_id == user_id).delete(synchronize_session=False)
    db.query(AuditLog).filter(AuditLog.user_id == user_id).delete(synchronize_session=False)
    db.query(Device).filter(Device.user_id == user_id).delete(synchronize_session=False)
    db.query(VPNProfile).filter(VPNProfile.user_id == user_id).delete(synchronize_session=False)
    db.query(Subscription).filter(Subscription.user_id == user_id).delete(synchronize_session=False)
    db.query(Payment).filter(Payment.user_id == user_id).delete(synchronize_session=False)
    db.query(Referral).filter(
        (Referral.inviter_id == user_id) | (Referral.invitee_id == user_id)
    ).delete(synchronize_session=False)
    db.delete(user)
    db.commit()

    panel_base = settings.panel_url.rstrip("/")
    marzban_username = f"tg_{payload.telegram_id}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.delete(
                f"{panel_base}/api/user/{marzban_username}",
                headers={"Authorization": f"Bearer {settings.panel_token}"},
            )
    except Exception:
        # Purge in local DB is already done; panel cleanup is best effort.
        pass

    await send_admin_log(
        "user_purged",
        payload.telegram_id,
        username,
        {"by_admin": admin.telegram_id},
    )

    return {"status": "ok", "telegram_id": payload.telegram_id, "username": username}
