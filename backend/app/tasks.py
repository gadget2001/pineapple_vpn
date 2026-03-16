from datetime import datetime, timedelta, timezone
from html import escape
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.core.config import settings
from app.core.logging import send_admin_log_sync
from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.connection_log import ConnectionLog
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.user import User
from app.utils.plans import plans_text




def _panel_headers() -> dict:
    return {"Authorization": f"Bearer {settings.panel_token}"}


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
                    "subscription_expired",
                    user.telegram_id,
                    user.username,
                    {"plan": sub.plan, "ended_at": sub.ends_at.isoformat()},
                )
                disable_vpn_user_task.delay(user.telegram_id, user.username)
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

            is_trial = sub.plan == "trial"
            title = "Пробный период заканчивается" if is_trial else "Подписка заканчивается"
            text = (
                f"{title}.\n"
                f"Окончание: {sub.ends_at.strftime('%d.%m.%Y %H:%M')} (UTC).\n"
                "Продлите доступ заранее, чтобы не потерять подключение.\n\n"
                f"{plans_text()}"
            )
            httpx.post(
                f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
                json={"chat_id": user.telegram_id, "text": text},
                timeout=10,
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
def disable_vpn_user_task(telegram_id: int, username: str | None = None):
    panel_base = settings.panel_url.rstrip("/")
    uname = f"tg_{telegram_id}"

    httpx.post(
        f"{panel_base}/api/user/disable/{uname}",
        headers=_panel_headers(),
        timeout=15,
    )

    httpx.delete(
        f"{panel_base}/api/user/{uname}",
        headers=_panel_headers(),
        timeout=15,
    )

    send_admin_log_sync(
        "vpn_disabled",
        telegram_id,
        username,
        {"deleted_from_panel": True},
    )


@celery_app.task
def send_my_nalog_daily_report():
    if not settings.admin_chat_id or not settings.bot_token:
        return

    db: Session = SessionLocal()
    try:
        tz = ZoneInfo(settings.sched_tz)
        now_local = datetime.now(tz)
        report_date = now_local.date()

        day_start_local = datetime(report_date.year, report_date.month, report_date.day, tzinfo=tz)
        day_end_local = day_start_local + timedelta(days=1)

        day_start_utc = day_start_local.astimezone(timezone.utc).replace(tzinfo=None)
        day_end_utc = day_end_local.astimezone(timezone.utc).replace(tzinfo=None)

        already_sent = (
            db.query(AuditLog.id)
            .filter(
                AuditLog.action == "my_nalog_daily_report_sent",
                AuditLog.created_at >= day_start_utc,
                AuditLog.created_at < day_end_utc,
            )
            .first()
        )
        if already_sent:
            return

        rows = (
            db.query(Payment, User)
            .join(User, User.id == Payment.user_id)
            .filter(
                Payment.kind == "topup",
                Payment.status == "paid",
                Payment.paid_at.isnot(None),
                Payment.paid_at >= day_start_utc,
                Payment.paid_at < day_end_utc,
            )
            .order_by(Payment.paid_at.asc(), Payment.id.asc())
            .all()
        )

        if not rows:
            db.add(
                AuditLog(
                    user_id=None,
                    action="my_nalog_daily_report_sent",
                    details={"date": report_date.isoformat(), "count": 0, "total": 0},
                )
            )
            db.commit()
            return

        total = 0
        lines = [
            "<b>[ Pineapple VPN / Мой налог ]</b>",
            "",
            f"Дата отчета: <code>{report_date.strftime('%d.%m.%Y')}</code> (МСК)",
            "",
            "Сегодня необходимо сформировать чеки по следующим оплатам:",
            "",
        ]

        for index, (payment, user) in enumerate(rows, start=1):
            total += int(payment.amount_rub or 0)
            payment_meta = payment.meta or {}
            snapshot_email = str(payment_meta.get("receipt_email") or "").strip().lower()
            email = snapshot_email or str(user.receipt_email or "").strip().lower() or "—"

            lines.extend(
                [
                    f"{index})",
                    f"Сумма: <code>{payment.amount_rub} ₽</code>",
                    f"Email: <code>{escape(email)}</code>",
                    f"Платеж ID: <code>{payment.id}</code>",
                    "",
                ]
            )

        lines.extend(
            [
                f"Итог за день: <code>{total} ₽</code>",
                f"Количество оплат: <code>{len(rows)}</code>",
            ]
        )

        httpx.post(
            f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
            json={
                "chat_id": settings.admin_chat_id,
                "text": "\n".join(lines),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )

        db.add(
            AuditLog(
                user_id=None,
                action="my_nalog_daily_report_sent",
                details={
                    "date": report_date.isoformat(),
                    "count": len(rows),
                    "total": total,
                },
            )
        )
        db.commit()
    finally:
        db.close()
