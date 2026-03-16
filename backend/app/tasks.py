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


def _main_menu_markup() -> dict:
    return {
        "inline_keyboard": [
            [
                {
                    "text": "🏠 Главное меню",
                    "callback_data": "main_menu",
                }
            ]
        ]
    }


def _send_user_message(telegram_id: int, text: str, with_main_menu: bool = True) -> bool:
    if not settings.bot_token or not telegram_id:
        return False

    payload = {
        "chat_id": telegram_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if with_main_menu:
        payload["reply_markup"] = _main_menu_markup()

    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
            json=payload,
            timeout=10,
        )
        return response.is_success
    except Exception:
        return False


def _format_end_time_local(ends_at_utc: datetime) -> tuple[str, str]:
    tz = ZoneInfo(settings.sched_tz)
    dt_local = ends_at_utc.replace(tzinfo=timezone.utc).astimezone(tz)
    tz_label = "МСК" if settings.sched_tz == "Europe/Moscow" else settings.sched_tz
    return dt_local.strftime("%d.%m.%Y %H:%M"), tz_label


def _reminder_text(plan: str, ends_at: datetime, hours_left: int) -> str:
    end_text, tz_label = _format_end_time_local(ends_at)
    is_trial = plan == "trial"

    if is_trial:
        title = "⏳ Pineapple VPN\n\nПробный период скоро завершится"
    else:
        title = "⏳ Pineapple VPN\n\nПодписка скоро завершится"

    lead = "через 24 часа" if hours_left == 24 else "через 1 час"

    return (
        f"{title} {lead}.\n"
        f"Окончание: {end_text} ({tz_label}).\n\n"
        "Продлите доступ заранее, чтобы подключение не прервалось.\n\n"
        f"{plans_text()}"
    )


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

        expired_ids: list[int] = []
        for sub in subs:
            sub.status = "expired"
            expired_ids.append(sub.id)

            user = db.query(User).filter(User.id == sub.user_id).first()
            if user:
                send_admin_log_sync(
                    "subscription_expired",
                    user.telegram_id,
                    user.username,
                    {"plan": sub.plan, "ended_at": sub.ends_at.isoformat(), "subscription_id": sub.id},
                )

        db.commit()

        for sub_id in expired_ids:
            disable_vpn_user_task.delay(sub_id)
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
            .filter(Subscription.status == "active", Subscription.ends_at > now, Subscription.ends_at <= soon)
            .all()
        )

        for sub in subs:
            user = db.query(User).filter(User.id == sub.user_id).first()
            if not user:
                continue

            remaining = sub.ends_at - now
            reminder_kind = None
            reminder_text = None

            if remaining <= timedelta(hours=1):
                if sub.reminder_1h_sent_at is None:
                    reminder_kind = "1h"
                    reminder_text = _reminder_text(sub.plan, sub.ends_at, hours_left=1)
            elif remaining <= timedelta(hours=24):
                if sub.reminder_24h_sent_at is None:
                    reminder_kind = "24h"
                    reminder_text = _reminder_text(sub.plan, sub.ends_at, hours_left=24)

            if not reminder_kind or not reminder_text:
                continue

            sent = _send_user_message(user.telegram_id, reminder_text, with_main_menu=True)
            if not sent:
                continue

            if reminder_kind == "24h":
                sub.reminder_24h_sent_at = now
            else:
                sub.reminder_1h_sent_at = now

            send_admin_log_sync(
                "subscription_reminder_sent",
                user.telegram_id,
                user.username,
                {
                    "subscription_id": sub.id,
                    "plan": sub.plan,
                    "reminder": reminder_kind,
                    "ends_at": sub.ends_at.isoformat(),
                },
            )

        db.commit()
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
def disable_vpn_user_task(subscription_id: int):
    db: Session = SessionLocal()
    try:
        sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not sub:
            return

        user = db.query(User).filter(User.id == sub.user_id).first()
        if not user:
            return

        panel_base = settings.panel_url.rstrip("/")
        uname = f"tg_{user.telegram_id}"

        disabled = False
        deleted = False
        try:
            resp_disable = httpx.post(
                f"{panel_base}/api/user/disable/{uname}",
                headers=_panel_headers(),
                timeout=15,
            )
            disabled = resp_disable.is_success
        except Exception:
            disabled = False

        try:
            resp_delete = httpx.delete(
                f"{panel_base}/api/user/{uname}",
                headers=_panel_headers(),
                timeout=15,
            )
            deleted = resp_delete.is_success
        except Exception:
            deleted = False

        if disabled and deleted:
            send_admin_log_sync(
                "vpn_disabled",
                user.telegram_id,
                user.username,
                {"deleted_from_panel": True, "subscription_id": sub.id},
            )

            if sub.expired_user_notified_at is None:
                user_notice = (
                    "⚠️ Pineapple VPN\n\n"
                    "Срок действия подписки истек.\n"
                    "Доступ отключен, текущий VPN-ключ деактивирован.\n\n"
                    "Чтобы продолжить пользоваться сервисом, продлите подписку в MiniApp."
                )
                if _send_user_message(user.telegram_id, user_notice, with_main_menu=True):
                    sub.expired_user_notified_at = datetime.utcnow()
                    db.commit()
            return

        send_admin_log_sync(
            "payment_error",
            user.telegram_id,
            user.username,
            {
                "reason": "vpn_disable_failed",
                "subscription_id": sub.id,
                "panel_disable_ok": disabled,
                "panel_delete_ok": deleted,
            },
        )
    finally:
        db.close()


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
