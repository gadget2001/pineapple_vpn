from __future__ import annotations

from dataclasses import dataclass

PLATFORMS = ("windows", "android", "iphone", "macos", "linux")
CLASH_PLATFORMS = {"windows", "android", "macos", "linux"}


@dataclass(frozen=True)
class PlatformClientInfo:
    platform: str
    client_type: str
    client_name: str
    download_url: str
    install_cta: str
    instructions: list[str]


PLATFORM_CLIENTS: dict[str, PlatformClientInfo] = {
    "windows": PlatformClientInfo(
        platform="windows",
        client_type="clash",
        client_name="Clash Meta / Mihomo",
        download_url="https://github.com/MetaCubeX/mihomo/releases",
        install_cta="Открыть в Clash",
        instructions=[
            "Установите Clash-совместимый клиент для Windows.",
            "Нажмите кнопку автонастройки и разрешите открыть приложение.",
            "Включите TUN-режим и активируйте профиль Pineapple VPN.",
        ],
    ),
    "android": PlatformClientInfo(
        platform="android",
        client_type="clash",
        client_name="Clash Meta / Mihomo",
        download_url="https://github.com/MetaCubeX/mihomo/releases",
        install_cta="Открыть в Clash",
        instructions=[
            "Установите Clash-совместимый клиент для Android.",
            "Нажмите кнопку автонастройки и подтвердите импорт подписки.",
            "Включите VPN-профиль Pineapple VPN.",
        ],
    ),
    "macos": PlatformClientInfo(
        platform="macos",
        client_type="clash",
        client_name="Clash Meta / Mihomo",
        download_url="https://github.com/MetaCubeX/mihomo/releases",
        install_cta="Открыть в Clash",
        instructions=[
            "Установите Clash-совместимый клиент для macOS.",
            "Нажмите кнопку автонастройки и импортируйте подписку.",
            "Включите TUN и активируйте профиль Pineapple VPN.",
        ],
    ),
    "linux": PlatformClientInfo(
        platform="linux",
        client_type="clash",
        client_name="Clash Meta / Mihomo",
        download_url="https://github.com/MetaCubeX/mihomo/releases",
        install_cta="Открыть в Clash",
        instructions=[
            "Установите Clash Meta / Mihomo для Linux.",
            "Нажмите автонастройку или импортируйте subscription URL вручную.",
            "Активируйте профиль Pineapple VPN и включите TUN.",
        ],
    ),
    "iphone": PlatformClientInfo(
        platform="iphone",
        client_type="v2raytun",
        client_name="v2RayTun",
        download_url="https://apps.apple.com/app/id6476628951",
        install_cta="Открыть в v2RayTun",
        instructions=[
            "Установите v2RayTun на iPhone.",
            "Нажмите кнопку автонастройки или импортируйте subscription URL в v2RayTun.",
            "Включите Global mode и разрешите создание VPN-профиля iOS.",
            "После импорта активируйте VPN-профиль.",
        ],
    ),
}


def normalize_platform(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip().lower()
    if raw == "ios":
        return "iphone"
    return raw if raw in PLATFORM_CLIENTS else None


def platform_client(platform: str) -> PlatformClientInfo:
    normalized = normalize_platform(platform)
    if not normalized:
        raise ValueError(f"Unsupported platform: {platform}")
    return PLATFORM_CLIENTS[normalized]
