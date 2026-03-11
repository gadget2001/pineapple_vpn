from datetime import datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.core.config import settings
from app.core.logging import send_admin_log_sync
from app.db.session import SessionLocal
from app.models.connection_log import ConnectionLog
from app.models.subscription import Subscription
from app.models.user import User


@celery_app.task
def check_expired_subscriptions():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        subs = (
            db.query(Subscription)
            .filter(Subscription.status == "active", Subscription.ends_at < now)
            .all()
        )
        for sub in subs:
            sub.status = "expired"
            user = db.query(User).filter(User.id == sub.user_id).first()
            if user:
                send_admin_log_sync(
                    "окончание подписки",
                    user.telegram_id,
                    user.username,
                    {"Subscription": sub.plan},
                )
                disable_vpn_user_task.delay(user.telegram_id)
        db.commit()
    finally:
        db.close()


@celery_app.task
def send_renewal_reminders():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        soon = now + timedelta(days=1)
        subs = (
            db.query(Subscription)
            .filter(Subscription.status == "active", Subscription.ends_at.between(now, soon))
            .all()
        )
        for sub in subs:
            user = db.query(User).filter(User.id == sub.user_id).first()
            if not user:
                continue
            text = (
                "Ваша подписка Pineapple VPN скоро истекает. "
                "Откройте MiniApp и продлите доступ."
            )
            httpx.post(
                f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
                json={"chat_id": user.telegram_id, "text": text},
                timeout=10,
            )
            send_admin_log_sync(
                "напоминание о продлении",
                user.telegram_id,
                user.username,
                {"EndsAt": sub.ends_at.isoformat()},
            )
    finally:
        db.close()


@celery_app.task
def cleanup_connection_logs():
    db: Session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=settings.log_retention_days)
        db.query(ConnectionLog).filter(ConnectionLog.connected_at < cutoff).delete()
        db.commit()
    finally:
        db.close()


@celery_app.task
def disable_vpn_user_task(telegram_id: int):
    httpx.post(
        f"{settings.panel_url}/api/user/disable/tg_{telegram_id}",
        headers={"Authorization": f"Bearer {settings.panel_token}"},
        timeout=15,
    )
