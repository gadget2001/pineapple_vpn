from datetime import date, datetime, timedelta, timezone
from html import escape
from zoneinfo import ZoneInfo

import httpx
from redis import Redis
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
from app.models.vpn_profile import VPNProfile
from app.services.xray_access_ingest import ingest_xray_access_log
from app.utils.plans import plans_text

redis_sync = Redis.from_url(settings.redis_url, decode_responses=True)
_panel_token_cache: str = settings.panel_token or ""


def _panel_headers(token: str | None = None) -> dict:
    return {"Authorization": f"Bearer {token or _panel_token_cache or settings.panel_token}"}


def _refresh_panel_token_sync() -> str:
    global _panel_token_cache

    if not settings.panel_username or not settings.panel_password:
        return _panel_token_cache or settings.panel_token

    panel_base = settings.panel_url.rstrip("/")
    response = httpx.post(
        f"{panel_base}/api/admin/token",
        data={"username": settings.panel_username, "password": settings.panel_password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    if not response.is_success:
        return _panel_token_cache or settings.panel_token

    payload = response.json() if response.content else {}
    token = payload.get("access_token") or payload.get("token")
    if token:
        _panel_token_cache = str(token)
    return _panel_token_cache or settings.panel_token


def _panel_request(method: str, path: str, *, timeout: int = 15, **kwargs) -> httpx.Response:
    panel_base = settings.panel_url.rstrip("/")
    response = httpx.request(
        method,
        f"{panel_base}{path}",
        headers=_panel_headers(),
        timeout=timeout,
        **kwargs,
    )
    if response.status_code != 401:
        return response

    fresh_token = _refresh_panel_token_sync()
    return httpx.request(
        method,
        f"{panel_base}{path}",
        headers=_panel_headers(fresh_token),
        timeout=timeout,
        **kwargs,
    )


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


def _send_user_message_with_markup(
    telegram_id: int,
    text: str,
    *,
    reply_markup: dict | None = None,
    parse_mode: str | None = None,
) -> str:
    if not settings.bot_token or not telegram_id:
        return "failed"

    payload = {
        "chat_id": telegram_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
            json=payload,
            timeout=10,
        )
        if response.is_success:
            return "sent"

        body = {}
        try:
            body = response.json()
        except Exception:
            body = {}
        description = str(body.get("description") or "").lower()
        if response.status_code in {403, 400} and (
            "bot was blocked by the user" in description
            or "user is deactivated" in description
            or "chat not found" in description
        ):
            return "blocked"
        return "failed"
    except Exception:
        return "failed"


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


def _trial_reminder_markup() -> dict:
    rows: list[list[dict]] = []
    if settings.telegram_miniapp_url:
        rows.append(
            [
                {
                    "text": "🚀 Открыть Pineapple VPN",
                    "web_app": {"url": settings.telegram_miniapp_url},
                }
            ]
        )
    rows.append([{"text": "🏠 Главное меню", "callback_data": "main_menu"}])
    return {"inline_keyboard": rows}


def _trial_reminder_text() -> str:
    return (
        "🍍 <b>Pineapple VPN</b>\n\n"
        "Вы ещё не активировали пробный период.\n"
        "Подключение занимает <b>2–3 минуты</b>, а доступ к нужным сервисам будет стабильным и защищённым.\n"
        "Нажмите кнопку ниже и попробуйте."
    )


def _active_subscriptions(db: Session) -> list[tuple[Subscription, User]]:
    now = datetime.utcnow()
    rows = (
        db.query(Subscription, User)
        .join(User, User.id == Subscription.user_id)
        .filter(Subscription.status == "active", Subscription.ends_at > now)
        .all()
    )
    return rows


def _user_first_start_at_utc(user: User) -> datetime:
    key = f"bot:first_start_at:{user.telegram_id}"
    try:
        raw = redis_sync.get(key)
    except Exception:
        raw = None

    if raw:
        try:
            ts = int(raw)
            return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
        except Exception:
            pass
    return user.created_at


def _start_of_local_day_utc(day: date) -> tuple[datetime, datetime]:
    tz = ZoneInfo(settings.sched_tz)
    start_local = datetime(day.year, day.month, day.day, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def _load_daily_limit_alerted_users(db: Session, today: date) -> set[int]:
    start_utc, end_utc = _start_of_local_day_utc(today)
    rows = (
        db.query(AuditLog.details)
        .filter(
            AuditLog.action == "daily_limit_reached_alert",
            AuditLog.created_at >= start_utc,
            AuditLog.created_at < end_utc,
        )
        .all()
    )

    alerted: set[int] = set()
    for (details,) in rows:
        if not isinstance(details, dict):
            continue
        tid = details.get("telegram_id")
        if isinstance(tid, int):
            alerted.add(tid)
    return alerted


def _panel_get_user(uname: str) -> dict | None:
    state, payload = _panel_get_user_state(uname)
    if state == "found":
        return payload
    return None


def _panel_get_user_state(uname: str) -> tuple[str, dict | None]:
    try:
        response = _panel_request("GET", f"/api/user/{uname}", timeout=15)
        if response.status_code == 404:
            return "missing", None
        if response.is_success:
            return "found", response.json()
    except Exception:
        return "error", None
    return "error", None


def _build_limit_payload(panel_user: dict, uname: str, note: str) -> dict:
    target_limit = max(int(settings.vpn_daily_data_limit_gb or 0), 0) * 1024 * 1024 * 1024
    target_strategy = "day" if target_limit > 0 else "no_reset"

    inbounds = panel_user.get("inbounds") if isinstance(panel_user.get("inbounds"), dict) else {}
    vless = inbounds.get("vless") if isinstance(inbounds, dict) else None
    if not isinstance(vless, list) or not vless:
        vless = [settings.panel_inbound_name] if settings.panel_inbound_name else []

    return {
        "username": uname,
        "note": note,
        "status": panel_user.get("status") or "active",
        "expire": panel_user.get("expire") or 0,
        "data_limit": target_limit,
        "data_limit_reset_strategy": target_strategy,
        "inbounds": {"vless": vless},
        "proxies": panel_user.get("proxies") or {"vless": {}},
    }


def _sync_panel_user_limit(uname: str, panel_user: dict, note: str) -> dict:
    target_limit = max(int(settings.vpn_daily_data_limit_gb or 0), 0) * 1024 * 1024 * 1024
    target_strategy = "day" if target_limit > 0 else "no_reset"

    existing_limit = int(panel_user.get("data_limit") or 0)
    existing_strategy = str(panel_user.get("data_limit_reset_strategy") or "")
    existing_note = str(panel_user.get("note") or "")

    if existing_limit == target_limit and existing_strategy == target_strategy and existing_note == note:
        return panel_user

    payload = _build_limit_payload(panel_user, uname, note)
    try:
        response = _panel_request("PUT", f"/api/user/{uname}", json=payload, timeout=15)
        if response.is_success:
            return response.json()
    except Exception:
        return panel_user

    return panel_user


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

        # Retry cleanup only for users that do not have any active subscription now.
        # This prevents accidental cleanup for users with historical expired records and current active plan.
        stale_expired_ids: list[int] = []
        stale_rows = (
            db.query(Subscription.id, Subscription.user_id)
            .join(VPNProfile, VPNProfile.user_id == Subscription.user_id)
            .filter(Subscription.status == "expired", VPNProfile.is_active.is_(True))
            .all()
        )
        for stale_sub_id, stale_user_id in stale_rows:
            has_active_now = (
                db.query(Subscription.id)
                .filter(
                    Subscription.user_id == stale_user_id,
                    Subscription.status == "active",
                    Subscription.ends_at > now,
                )
                .first()
                is not None
            )
            if not has_active_now:
                stale_expired_ids.append(stale_sub_id)

        for sub_id in sorted(set(expired_ids + stale_expired_ids)):
            disable_vpn_user_task.delay(sub_id)
    finally:
        db.close()


@celery_app.task
def send_trial_activation_reminders():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        users = db.query(User).all()

        for user in users:
            first_start_at = _user_first_start_at_utc(user)
            if (now - first_start_at) < timedelta(days=2):
                continue

            already_sent = (
                db.query(AuditLog.id)
                .filter(
                    AuditLog.user_id == user.id,
                    AuditLog.action == "trial_activation_reminder_sent",
                )
                .first()
            )
            if already_sent:
                continue

            blocked_before = (
                db.query(AuditLog.id)
                .filter(
                    AuditLog.user_id == user.id,
                    AuditLog.action == "trial_activation_reminder_skipped_blocked_bot",
                )
                .first()
            )
            if blocked_before:
                continue

            has_active_subscription = (
                db.query(Subscription.id)
                .filter(
                    Subscription.user_id == user.id,
                    Subscription.status == "active",
                    Subscription.ends_at > now,
                )
                .first()
                is not None
            )
            if has_active_subscription:
                continue

            trial_exists = (
                db.query(Subscription.id)
                .filter(Subscription.user_id == user.id, Subscription.plan == "trial")
                .first()
                is not None
            )
            if trial_exists:
                continue

            has_profile = db.query(VPNProfile.id).filter(VPNProfile.user_id == user.id).first() is not None
            if has_profile:
                continue

            send_result = _send_user_message_with_markup(
                user.telegram_id,
                _trial_reminder_text(),
                reply_markup=_trial_reminder_markup(),
                parse_mode="HTML",
            )

            age_days = max(2, int((now - first_start_at).total_seconds() // 86400))
            if send_result == "sent":
                db.add(
                    AuditLog(
                        user_id=user.id,
                        action="trial_activation_reminder_sent",
                        details={"age_days": age_days, "reason": "no_trial_no_profile_after_2d"},
                    )
                )
                db.commit()
                send_admin_log_sync(
                    "trial_activation_reminder_sent",
                    user.telegram_id,
                    user.username,
                    {"age_days": age_days, "reason": "no_trial_no_profile_after_2d"},
                )
                continue

            if send_result == "blocked":
                db.add(
                    AuditLog(
                        user_id=user.id,
                        action="trial_activation_reminder_skipped_blocked_bot",
                        details={"age_days": age_days, "reason": "bot_blocked_or_chat_deleted"},
                    )
                )
                db.commit()
                send_admin_log_sync(
                    "trial_activation_reminder_skipped_blocked_bot",
                    user.telegram_id,
                    user.username,
                    {"age_days": age_days, "reason": "bot_blocked_or_chat_deleted"},
                )
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
def ingest_xray_access_logs():
    db: Session = SessionLocal()
    try:
        ingest_xray_access_log(db)
    finally:
        db.close()


@celery_app.task
def cleanup_connection_logs():
    db: Session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=settings.vpn_connection_log_retention_days)
        db.query(ConnectionLog).filter(ConnectionLog.connected_at < cutoff).delete()
        db.commit()
    finally:
        db.close()


@celery_app.task
def check_daily_data_limits():
    if not settings.vpn_daily_limit_alerts_enabled:
        return

    db: Session = SessionLocal()
    try:
        target_limit = max(int(settings.vpn_daily_data_limit_gb or 0), 0) * 1024 * 1024 * 1024
        if target_limit <= 0:
            return

        today_local = datetime.now(ZoneInfo(settings.sched_tz)).date()
        alerted_today = _load_daily_limit_alerted_users(db, today_local)

        rows = _active_subscriptions(db)
        for _sub, user in rows:
            if user.telegram_id in alerted_today:
                continue

            uname = f"tg_{user.telegram_id}"
            note = (settings.vpn_connection_name_template or "🍍 Pineapple VPN ({username})").format(
                username=uname,
                telegram_username=user.username or "",
            )

            panel_user = _panel_get_user(uname)
            if not panel_user:
                continue

            panel_user = _sync_panel_user_limit(uname, panel_user, note)

            used_traffic = int(panel_user.get("used_traffic") or 0)
            data_limit = int(panel_user.get("data_limit") or 0)
            strategy = str(panel_user.get("data_limit_reset_strategy") or "")

            if data_limit <= 0 or strategy != "day":
                continue
            if used_traffic < data_limit:
                continue

            send_admin_log_sync(
                "daily_limit_reached",
                user.telegram_id,
                user.username,
                {
                    "panel_username": uname,
                    "limit_bytes": data_limit,
                    "limit_gb": settings.vpn_daily_data_limit_gb,
                    "used_bytes": used_traffic,
                    "used_gb": round(used_traffic / (1024 * 1024 * 1024), 2),
                    "date": today_local.isoformat(),
                },
            )

            db.add(
                AuditLog(
                    user_id=user.id,
                    action="daily_limit_reached_alert",
                    details={
                        "telegram_id": user.telegram_id,
                        "panel_username": uname,
                        "date": today_local.isoformat(),
                        "limit_bytes": data_limit,
                        "used_bytes": used_traffic,
                    },
                )
            )
            db.commit()
            alerted_today.add(user.telegram_id)
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

        now = datetime.utcnow()
        has_active_now = (
            db.query(Subscription.id)
            .filter(
                Subscription.user_id == user.id,
                Subscription.status == "active",
                Subscription.ends_at > now,
            )
            .first()
            is not None
        )
        if has_active_now:
            send_admin_log_sync(
                "vpn_cleanup_skipped_active_subscription",
                user.telegram_id,
                user.username,
                {"subscription_id": sub.id, "reason": "active_subscription_exists"},
            )
            return

        profile = db.query(VPNProfile).filter(VPNProfile.user_id == user.id).first()
        if not profile:
            send_admin_log_sync(
                "vpn_cleanup_skipped_no_profile",
                user.telegram_id,
                user.username,
                {"subscription_id": sub.id, "reason": "no_local_vpn_profile"},
            )
            return

        uname = f"tg_{user.telegram_id}"
        panel_user_exists = None

        disabled = False
        deleted = False
        disable_status_code = None
        delete_status_code = None
        state_before, _ = _panel_get_user_state(uname)
        if state_before == "found":
            panel_user_exists = True
        elif state_before == "missing":
            panel_user_exists = False
        else:
            panel_user_exists = None

        if panel_user_exists is None:
            send_admin_log_sync(
                "vpn_cleanup_failed",
                user.telegram_id,
                user.username,
                {
                    "reason": "panel_unreachable_or_auth_failed",
                    "subscription_id": sub.id,
                    "panel_username": uname,
                },
            )
            return

        try:
            if panel_user_exists:
                resp_disable = _panel_request("POST", f"/api/user/disable/{uname}", timeout=15)
                disable_status_code = resp_disable.status_code
                # 404 here is not success: user existence is already confirmed by GET.
                disabled = resp_disable.is_success
            else:
                disabled = True
        except Exception:
            disabled = False

        try:
            if panel_user_exists:
                resp_delete = _panel_request("DELETE", f"/api/user/{uname}", timeout=15)
                delete_status_code = resp_delete.status_code
                deleted = resp_delete.is_success or resp_delete.status_code == 404
            else:
                deleted = True
        except Exception:
            deleted = False

        state_after, panel_user_after = _panel_get_user_state(uname)
        if state_after == "missing":
            effective_block = True
        elif state_after == "found":
            panel_user_still_active = str(panel_user_after.get("status") or "").lower() == "active"
            effective_block = deleted or (disabled and not panel_user_still_active)
        else:
            # Network/API verification failed: trust only explicit successful delete.
            effective_block = deleted

        if effective_block:
            profile.is_active = False
            profile.last_synced_at = datetime.utcnow()
            db.add(profile)
            db.commit()
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
            "vpn_cleanup_failed",
            user.telegram_id,
            user.username,
            {
                "reason": "vpn_disable_or_delete_failed",
                "subscription_id": sub.id,
                "panel_disable_ok": disabled,
                "panel_delete_ok": deleted,
                "disable_status_code": disable_status_code,
                "delete_status_code": delete_status_code,
                "panel_username": uname,
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
