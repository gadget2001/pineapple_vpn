from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
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
from app.services.vpn_profile import get_or_create_vpn_profile, marzban_error
from app.utils.audit import log_audit
from app.utils.trial_state import mark_trial_used

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

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

INSTRUCTIONS = {
    "windows": {
        "app_name": "NekoRay",
        "download_url": "https://github.com/MatsuriDayo/nekoray/releases",
        "steps": [
            "Скачайте архив NekoRay для Windows и распакуйте его в удобную папку.",
            "Запустите клиент от имени пользователя и дождитесь загрузки интерфейса.",
            "На следующем шаге получите ссылку конфигурации и импортируйте ее в NekoRay.",
            "Выберите импортированный профиль и нажмите Подключить.",
        ],
    },
    "iphone": {
        "app_name": "Streisand",
        "download_url": "https://apps.apple.com/app/streisand/id6450534064",
        "steps": [
            "Установите приложение Streisand из App Store.",
            "Откройте приложение и разрешите создание VPN-профиля в iOS.",
            "На следующем шаге получите ссылку конфигурации и импортируйте ее.",
            "Активируйте профиль и проверьте подключение.",
        ],
    },
    "android": {
        "app_name": "v2rayNG",
        "download_url": "https://github.com/2dust/v2rayNG/releases",
        "steps": [
            "Установите приложение v2rayNG из GitHub Releases.",
            "Откройте приложение и разрешите создание VPN-подключения.",
            "На следующем шаге получите ссылку конфигурации и импортируйте ее.",
            "Выберите профиль и нажмите Подключить.",
        ],
    },
    "macos": {
        "app_name": "Streisand",
        "download_url": "https://apps.apple.com/app/streisand/id6450534064",
        "steps": [
            "Установите Streisand на macOS.",
            "Откройте приложение и подготовьте его к импорту конфигурации.",
            "На следующем шаге получите ссылку конфигурации и импортируйте ее.",
            "Активируйте профиль и проверьте подключение к сервисам.",
        ],
    },
}


def _normalize_os(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip().lower()
    if raw == "ios":
        return "iphone"
    return raw


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

    # Respect explicit in-progress states (used by repeat device flow).
    if user.onboarding_step in {"device_select", "install_app", "get_config", "complete"}:
        return user.onboarding_step

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


@router.get(
    "/state",
    response_model=OnboardingStateOut,
    summary="Состояние мастера подключения",
    description="Возвращает текущий шаг onboarding и все флаги, чтобы MiniApp мог продолжить с места остановки.",
)
def onboarding_state(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.onboarding_step:
        user.onboarding_step = _resolve_step(db, user)
        db.commit()

    return _state(db, user)


@router.post(
    "/accept-terms",
    response_model=OnboardingStateOut,
    summary="Подтвердить согласие с правилами",
    description="Фиксирует согласие пользователя с правилами и переводит его к шагу пробного периода.",
)
async def accept_terms(
    payload: AcceptTermsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.accepted:
        raise HTTPException(status_code=400, detail="Consent must be accepted")

    if not user.terms_accepted_at:
        user.terms_accepted_at = datetime.utcnow()
        user.onboarding_step = "trial_offer"
        db.commit()

        log_audit(db, user.id, "terms_accepted", {})
        await send_admin_log(
            "terms_accepted",
            user.telegram_id,
            user.username,
            {"accepted_at": user.terms_accepted_at.isoformat()},
        )

    return _state(db, user)


@router.post(
    "/activate-trial",
    response_model=TrialActivationOut,
    summary="Активировать пробный период",
    description="Однократно активирует trial и переводит пользователя к выбору устройства.",
)
async def activate_trial(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if _trial_used(db, user):
        raise HTTPException(status_code=400, detail="Trial already used")

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


@router.post(
    "/device",
    response_model=OnboardingStateOut,
    summary="Выбрать устройство",
    description="Сохраняет платформу пользователя и переводит на шаг установки приложения.",
)
async def select_device(
    payload: SelectDeviceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.onboarding_os = _normalize_os(payload.os)
    user.onboarding_step = "install_app"
    db.commit()

    log_audit(db, user.id, "onboarding_platform_selected", {"os": payload.os})

    return _state(db, user)


@router.get(
    "/instructions",
    response_model=OnboardingInstructionOut,
    summary="Инструкция установки клиента",
    description="Возвращает пошаговую инструкцию для выбранной платформы.",
)
async def get_instructions(
    os: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_os = _normalize_os(os or user.onboarding_os) or ""
    if target_os not in INSTRUCTIONS:
        raise HTTPException(status_code=400, detail="Choose device first")

    if user.onboarding_os != target_os:
        user.onboarding_os = target_os
        user.onboarding_step = "install_app"
        db.commit()

    info = INSTRUCTIONS[target_os]

    log_audit(db, user.id, "onboarding_instruction_viewed", {"os": target_os})

    return OnboardingInstructionOut(
        os=target_os,
        app_name=info["app_name"],
        download_url=info["download_url"],
        steps=info["steps"],
    )


@router.post(
    "/confirm-install",
    response_model=OnboardingStateOut,
    summary="Подтвердить установку приложения",
    description="Подтверждает установку VPN-клиента и переводит на шаг получения конфигурации.",
)
async def confirm_install(
    payload: InstructionConfirmRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.os:
        user.onboarding_os = _normalize_os(payload.os)

    user.onboarding_install_confirmed_at = datetime.utcnow()
    user.onboarding_step = "get_config"
    db.commit()

    log_audit(db, user.id, "onboarding_app_installed", {"os": user.onboarding_os})

    return _state(db, user)


@router.post(
    "/config",
    response_model=OnboardingConfigOut,
    summary="Получить конфигурацию на шаге onboarding",
    description="Создает (если нужно) и возвращает subscription URL пользователя после проверки активной подписки/trial.",
)
async def get_onboarding_config(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _active_subscription(db, user):
        raise HTTPException(status_code=402, detail="Active subscription required")

    try:
        profile, created = await get_or_create_vpn_profile(db, user)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=marzban_error(exc)) from exc

    # Keep user on config step until manual confirmation
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

    log_audit(db, user.id, "onboarding_config_received", {"uuid": profile.uuid})
    await send_admin_log(
        "onboarding_config_received",
        user.telegram_id,
        user.username,
        {"uuid": profile.uuid},
    )

    return OnboardingConfigOut(
        subscription_url=profile.subscription_url,
        import_help="Скопируйте ссылку и импортируйте ее в VPN-клиент на предыдущем шаге.",
    )


@router.post(
    "/complete",
    response_model=OnboardingStateOut,
    summary="Завершить onboarding",
    description="Помечает первичную настройку как завершенную.",
)
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


@router.post(
    "/restart-device-flow",
    response_model=OnboardingStateOut,
    summary="Повторная настройка для нового устройства",
    description="Запускает укороченный сценарий: выбор устройства -> инструкция -> конфигурация.",
)
async def restart_device_flow(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.terms_accepted_at:
        raise HTTPException(status_code=400, detail="Terms must be accepted first")

    user.onboarding_step = "device_select"
    user.onboarding_os = None
    user.onboarding_install_confirmed_at = None
    db.commit()

    log_audit(db, user.id, "onboarding_restarted", {})
    await send_admin_log(
        "onboarding_restarted",
        user.telegram_id,
        user.username,
        {},
    )

    return _state(db, user)

