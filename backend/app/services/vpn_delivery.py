from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.vpn_profile import VPNProfile
from app.services.vpn_clients import normalize_platform, platform_client
from app.services.vpn_install import build_platform_install_urls
from app.services.vpn_subscription import build_subscription_url, display_subtitle, parse_vless, render_display_title


@dataclass
class PlatformConfigBundle:
    platform: str
    client_type: str
    client_name: str
    download_url: str
    install_cta: str
    instruction_steps: list[str]
    profile_reused: bool
    message: str
    subscription_url: str
    subscription_url_clash: str
    raw_vless_url: str
    install_url: str
    install_urls: dict[str, str]
    display_title: str
    display_subtitle: str


def _as_list(value: list[str] | None) -> list[str]:
    return list(value or [])


def _device_family(platform: str) -> str:
    if platform in {"windows", "macos", "linux"}:
        return "desktop"
    return "mobile"


def ensure_profile_metadata(profile: VPNProfile) -> None:
    parsed = parse_vless(profile.raw_vless_url or profile.vless_url)
    if not profile.raw_vless_url:
        profile.raw_vless_url = profile.vless_url
    profile.server_host = profile.server_host or parsed.get("host") or ""
    profile.server_port = profile.server_port or parsed.get("port") or 443
    profile.transport_type = profile.transport_type or parsed.get("transport") or "tcp"
    profile.security_type = profile.security_type or parsed.get("security") or "reality"
    profile.reality_short_id = profile.reality_short_id or parsed.get("short_id") or None
    profile.reality_sni = profile.reality_sni or parsed.get("sni") or None
    profile.reality_public_key = profile.reality_public_key or parsed.get("public_key") or None

    profile.profile_name = profile.profile_name or settings.vpn_brand_name
    profile.profile_group = profile.profile_group or settings.vpn_clash_group_name
    profile.display_title = profile.display_title or render_display_title()
    profile.display_subtitle = profile.display_subtitle or display_subtitle()
    profile.is_active = True
    profile.last_synced_at = datetime.utcnow()


def refresh_platform_urls(profile: VPNProfile) -> None:
    profile.subscription_url_clash = build_subscription_url(profile, "clash")
    profile.subscription_url = profile.subscription_url_clash

    install_urls = build_platform_install_urls(profile)
    profile.install_url_windows = install_urls["windows"]
    profile.install_url_android = install_urls["android"]
    profile.install_url_ios = install_urls["iphone"]
    profile.install_url_macos = install_urls["macos"]
    profile.install_url_linux = install_urls["linux"]
    profile.last_install_link_generated_at = datetime.utcnow()


def issue_platform_config(
    db: Session,
    *,
    user: User,
    profile: VPNProfile,
    platform: str | None,
    created: bool,
) -> PlatformConfigBundle:
    normalized_platform = normalize_platform(platform) or "windows"
    info = platform_client(normalized_platform)

    ensure_profile_metadata(profile)
    refresh_platform_urls(profile)

    before_platforms = _as_list(profile.issued_platforms)
    reused = not created
    if normalized_platform in before_platforms:
        profile.reinstall_count = int(profile.reinstall_count or 0) + 1
    else:
        before_platforms.append(normalized_platform)

    profile.issued_platforms = before_platforms
    profile.last_selected_platform = normalized_platform
    profile.last_install_platform = normalized_platform
    profile.last_config_issued_at = datetime.utcnow()
    profile.last_device_flow_at = datetime.utcnow()
    profile.device_family = _device_family(normalized_platform)
    profile.client_type = info.client_type

    db.add(profile)
    db.commit()
    db.refresh(profile)

    install_urls = {
        "windows": profile.install_url_windows or "",
        "android": profile.install_url_android or "",
        "iphone": profile.install_url_ios or "",
        "macos": profile.install_url_macos or "",
        "linux": profile.install_url_linux or "",
    }

    selected_subscription = profile.subscription_url_clash or profile.subscription_url

    message = (
        "Ваш ключ уже создан и активен. Сейчас настроим его для нового устройства."
        if reused
        else "Профиль создан. Можно подключать устройство автоматически."
    )

    return PlatformConfigBundle(
        platform=normalized_platform,
        client_type=info.client_type,
        client_name=info.client_name,
        download_url=info.download_url,
        install_cta=info.install_cta,
        instruction_steps=info.instructions,
        profile_reused=reused,
        message=message,
        subscription_url=selected_subscription,
        subscription_url_clash=profile.subscription_url_clash or "",
        raw_vless_url=profile.raw_vless_url or profile.vless_url,
        install_url=install_urls[normalized_platform],
        install_urls=install_urls,
        display_title=profile.display_title or render_display_title(),
        display_subtitle=profile.display_subtitle or display_subtitle(),
    )
