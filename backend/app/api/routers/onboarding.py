from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import send_admin_log
from app.db.session import get_db
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_profile import VPNProfile
from app.schemas.onboarding import (
    AcceptTermsRequest,
    InstructionConfirmRequest,
    OnboardingConfigOut,
    OnboardingInstructionOut,
    OnboardingStateOut,
    SelectDeviceRequest,
    TrialActivationOut,
)
from app.services.vpn_clients import normalize_platform, platform_client
from app.services.vpn_delivery import issue_platform_config
from app.services.vpn_profile import get_or_create_vpn_profile, marzban_error
from app.utils.audit import log_audit
from app.utils.trial_state import mark_trial_used

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])
AUTO_COMPLETE_GET_CONFIG_AFTER_SECONDS = 3600

TOTAL_STEPS = 6
STEP_INDEX = {
    "welcome": 1,
    "trial_offer": 2,
    "device_select": 3,
    "install_app": 4,
    "get_config": 5,
    "complete": 6,
    "done": 6,
}


def _normalize_os(value: str | None) -> str | None:
    return normalize_platform(value)


def _trial_used(db: Session, user: User) -> bool:
    if user.trial_activated_at:
        return True
    trial_exists = (
        db.query(Subscription.id)
        .filter(Subscription.user_id == user.id, Subscription.plan == "trial")
        .first()
    )
    return trial_exists is not None


def _active_subscription(db: Session, user: User) -> Subscription | None:
    now = datetime.utcnow()
    return (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.status == "active", Subscription.ends_at > now)
        .order_by(Subscription.ends_at.desc())
        .first()
    )


def _resolve_step(db: Session, user: User) -> str:
    normalized_os = _normalize_os(user.onboarding_os)
    if normalized_os != user.onboarding_os:
        user.onboarding_os = normalized_os
        db.commit()

    if user.onboarding_step in {"device_select", "install_app", "complete"}:
        return user.onboarding_step

    if user.onboarding_step == "get_config":
        profile = db.query(VPNProfile).filter(VPNProfile.user_id == user.id).first()
        issued_at = profile.last_config_issued_at if profile else None
        install_confirmed_at = user.onboarding_install_confirmed_at
        # Auto-timeout applies only to the current onboarding run.
        # For repeat flows, older issued_at values from previous runs must not close the step.
        if issued_at and install_confirmed_at and issued_at >= install_confirmed_at:
            elapsed = (datetime.utcnow() - issued_at).total_seconds()
            if elapsed >= AUTO_COMPLETE_GET_CONFIG_AFTER_SECONDS:
                user.onboarding_completed_at = datetime.utcnow()
                user.onboarding_step = "done"
                db.commit()
                log_audit(db, user.id, "onboarding_completed", {"mode": "auto_timeout", "step": "get_config"})
                return "done"
        return "get_config"

    if user.onboarding_completed_at:
        return "done"
    if not user.terms_accepted_at:
        return "welcome"

    active_sub = _active_subscription(db, user)
    if not active_sub and not user.trial_activated_at and not _trial_used(db, user):
        return "trial_offer"

    if not normalized_os:
        return "device_select"

    if not user.onboarding_install_confirmed_at:
        return "install_app"

    has_profile = db.query(VPNProfile.id).filter(VPNProfile.user_id == user.id).first() is not None
    if not has_profile:
        return "get_config"

    return "complete"


def _state(db: Session, user: User) -> OnboardingStateOut:
    step = _resolve_step(db, user)
    active_sub = _active_subscription(db, user)
    has_profile = db.query(VPNProfile.id).filter(VPNProfile.user_id == user.id).first() is not None
    normalized_os = _normalize_os(user.onboarding_os)

    return OnboardingStateOut(
        step=step,
        step_index=STEP_INDEX.get(step, 1),
        total_steps=TOTAL_STEPS,
        terms_accepted=user.terms_accepted_at is not None,
        terms_accepted_at=user.terms_accepted_at,
        legal_docs_version_current=settings.legal_docs_version,
        legal_docs_version_accepted=user.legal_docs_version_accepted,
        trial_available=not _trial_used(db, user),
        trial_activated_at=user.trial_activated_at,
        trial_days=user.trial_days,
        os=normalized_os,
        install_confirmed=user.onboarding_install_confirmed_at is not None,
        has_active_subscription=active_sub is not None,
        vpn_ready=has_profile,
        completed=user.onboarding_completed_at is not None,
        onboarding_completed_at=user.onboarding_completed_at,
    )


@router.get("/state", response_model=OnboardingStateOut)
def onboarding_state(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.onboarding_step:
        user.onboarding_step = _resolve_step(db, user)
        db.commit()

    return _state(db, user)


@router.post("/accept-terms", response_model=OnboardingStateOut)
async def accept_terms(
    payload: AcceptTermsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.accepted:
        raise HTTPException(status_code=400, detail="Необходимо подтвердить согласие с правилами.")

    accepted_version = (payload.docs_version or settings.legal_docs_version).strip()[:32]

    if not user.terms_accepted_at:
        user.terms_accepted_at = datetime.utcnow()
        user.legal_docs_version_accepted = accepted_version
        user.onboarding_step = "trial_offer"
        db.commit()

        log_audit(db, user.id, "terms_accepted", {"docs_version": accepted_version})
        await send_admin_log(
            "terms_accepted",
            user.telegram_id,
            user.username,
            {
                "accepted_at": user.terms_accepted_at.isoformat(),
                "docs_version": accepted_version,
            },
        )
    elif user.legal_docs_version_accepted != accepted_version:
        user.legal_docs_version_accepted = accepted_version
        db.commit()

    return _state(db, user)


@router.post("/activate-trial", response_model=TrialActivationOut)
async def activate_trial(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if _trial_used(db, user):
        raise HTTPException(status_code=400, detail="Пробный период уже использован.")

    if _active_subscription(db, user):
        raise HTTPException(status_code=400, detail="У вас уже есть активная подписка.")

    now = datetime.utcnow()
    ends_at = now + timedelta(days=user.trial_days)
    db.add(
        Subscription(
            user_id=user.id,
            plan="trial",
            status="active",
            price_rub=0,
            starts_at=now,
            ends_at=ends_at,
        )
    )
    user.trial_activated_at = now
    user.onboarding_step = "device_select"
    db.commit()
    await mark_trial_used(user.telegram_id)

    log_audit(db, user.id, "trial_activated", {"days": user.trial_days})
    await send_admin_log(
        "trial_activated",
        user.telegram_id,
        user.username,
        {"days": user.trial_days, "ends_at": ends_at.isoformat()},
    )

    return TrialActivationOut(status="ok", ends_at=ends_at, trial_days=user.trial_days)


@router.post("/device", response_model=OnboardingStateOut)
async def select_device(
    payload: SelectDeviceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    normalized_os = _normalize_os(payload.os)
    if not normalized_os:
        raise HTTPException(status_code=400, detail="Неподдерживаемая платформа.")

    client = platform_client(normalized_os)
    user.onboarding_os = normalized_os
    user.onboarding_step = "install_app"
    db.commit()

    log_audit(db, user.id, "onboarding_platform_selected", {"os": payload.os})
    log_audit(db, user.id, "vpn_client_selected", {"os": payload.os, "client_type": client.client_type})
    await send_admin_log(
        "onboarding_platform_selected",
        user.telegram_id,
        user.username,
        {
            "os": normalized_os,
            "client_type": client.client_type,
            "flow": "repeat_device" if user.onboarding_completed_at else "first_time",
            "step": "device_select",
        },
    )

    return _state(db, user)


@router.get("/instructions", response_model=OnboardingInstructionOut)
async def get_instructions(
    os: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_os = _normalize_os(os or user.onboarding_os)
    if not target_os:
        raise HTTPException(status_code=400, detail="Сначала выберите устройство.")

    if user.onboarding_os != target_os:
        user.onboarding_os = target_os
        user.onboarding_step = "install_app"
        db.commit()

    client = platform_client(target_os)
    log_audit(db, user.id, "onboarding_instruction_viewed", {"os": target_os})

    return OnboardingInstructionOut(
        os=target_os,
        app_name=client.client_name,
        client_type=client.client_type,
        download_url=client.download_url,
        install_cta=client.install_cta,
        steps=client.instructions,
    )


@router.post("/confirm-install", response_model=OnboardingStateOut)
async def confirm_install(
    payload: InstructionConfirmRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.os:
        normalized_os = _normalize_os(payload.os)
        if not normalized_os:
            raise HTTPException(status_code=400, detail="Неподдерживаемая платформа.")
        user.onboarding_os = normalized_os

    user.onboarding_install_confirmed_at = datetime.utcnow()
    user.onboarding_step = "get_config"
    db.commit()

    log_audit(db, user.id, "onboarding_app_installed", {"os": user.onboarding_os})

    return _state(db, user)


@router.post("/config", response_model=OnboardingConfigOut)
async def get_onboarding_config(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _active_subscription(db, user):
        raise HTTPException(status_code=402, detail="Для получения конфигурации нужен активный тариф или пробный период.")

    selected_platform = _normalize_os(user.onboarding_os) or "windows"

    try:
        profile, created = await get_or_create_vpn_profile(db, user)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=marzban_error(exc)) from exc

    bundle = issue_platform_config(
        db,
        user=user,
        profile=profile,
        platform=selected_platform,
        created=created,
    )

    user.onboarding_step = "get_config"
    db.commit()

    if created:
        await send_admin_log(
            "vpn_config_created",
            user.telegram_id,
            user.username,
            {
                "uuid": profile.uuid,
                "vless_url": profile.vless_url,
                "subscription_url": profile.subscription_url,
                "reality_public_key": profile.reality_public_key,
            },
        )

    generation_action = "vpn_profile_generated_clash"
    log_audit(db, user.id, generation_action, {"platform": bundle.platform, "uuid": profile.uuid})
    log_audit(db, user.id, "vpn_platform_config_issued", {"platform": bundle.platform, "client_type": bundle.client_type})
    log_audit(db, user.id, "vpn_install_link_generated", {"platform": bundle.platform, "install_url": bundle.install_url})
    if bundle.platform == "iphone":
        log_audit(db, user.id, "vpn_install_link_generated_ios", {"install_url": bundle.install_url})
    if bundle.profile_reused:
        log_audit(db, user.id, "vpn_profile_reused_for_new_device", {"platform": bundle.platform})
        log_audit(db, user.id, "vpn_profile_reused", {"platform": bundle.platform})

    await send_admin_log(
        "onboarding_config_received",
        user.telegram_id,
        user.username,
        {
            "uuid": profile.uuid,
            "platform": bundle.platform,
            "client_type": bundle.client_type,
            "profile_reused": bundle.profile_reused,
        },
    )

    import_help = (
        "Нажмите автонастройку. Если приложение не открылось, используйте копирование ссылки или QR."
    )

    return OnboardingConfigOut(
        platform=bundle.platform,
        client_type=bundle.client_type,
        client_name=bundle.client_name,
        profile_reused=bundle.profile_reused,
        message=bundle.message,
        display_title=bundle.display_title,
        display_subtitle=bundle.display_subtitle,
        subscription_url=bundle.subscription_url,
        subscription_url_clash=bundle.subscription_url_clash,
        raw_vless_url=bundle.raw_vless_url,
        install_url=bundle.install_url,
        install_urls=bundle.install_urls,
        import_help=import_help,
    )


@router.post("/complete", response_model=OnboardingStateOut)
async def complete_onboarding(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.onboarding_completed_at:
        user.onboarding_completed_at = datetime.utcnow()
    user.onboarding_step = "done"
    db.commit()

    log_audit(db, user.id, "onboarding_completed", {})
    await send_admin_log(
        "onboarding_completed",
        user.telegram_id,
        user.username,
        {"completed_at": user.onboarding_completed_at.isoformat()},
    )

    return _state(db, user)


@router.post("/restart-device-flow", response_model=OnboardingStateOut)
async def restart_device_flow(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.terms_accepted_at:
        raise HTTPException(status_code=400, detail="Сначала примите правила сервиса.")

    if not _active_subscription(db, user):
        raise HTTPException(status_code=400, detail="Для повторной настройки нужен активный тариф или пробный период.")

    user.onboarding_step = "device_select"
    user.onboarding_os = None
    user.onboarding_install_confirmed_at = None
    db.commit()

    log_audit(db, user.id, "onboarding_restarted", {})
    log_audit(db, user.id, "vpn_repeat_device_setup_started", {})
    await send_admin_log(
        "onboarding_restarted",
        user.telegram_id,
        user.username,
        {},
    )

    return _state(db, user)


@router.post("/cancel-device-flow", response_model=OnboardingStateOut)
async def cancel_device_flow(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.onboarding_completed_at:
        raise HTTPException(status_code=400, detail="Завершите первичную настройку перед закрытием мастера.")

    user.onboarding_step = "done"
    user.onboarding_os = None
    user.onboarding_install_confirmed_at = None
    db.commit()

    log_audit(db, user.id, "onboarding_cancelled", {})
    return _state(db, user)

