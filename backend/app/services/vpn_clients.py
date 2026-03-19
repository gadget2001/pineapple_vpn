from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings

PLATFORMS = ("windows", "android", "iphone", "macos", "linux")
CLASH_PLATFORMS = {"windows", "macos", "linux", "iphone"}


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
        client_name="Koala Clash",
        download_url="https://release-assets.githubusercontent.com/github-production-release-asset/1011075251/eca6652e-716e-42b3-9f98-199855c9df63?sp=r&sv=2018-11-09&sr=b&spr=https&se=2026-03-19T10%3A58%3A22Z&rscd=attachment%3B+filename%3DKoala.Clash_x64-setup.exe&rsct=application%2Foctet-stream&skoid=96c2d410-5711-43a1-aedd-ab1947aa7ab0&sktid=398a6654-997b-47e9-b12b-9515b896b4de&skt=2026-03-19T09%3A57%3A26Z&ske=2026-03-19T10%3A58%3A22Z&sks=b&skv=2018-11-09&sig=j963XNL93sd9qEMHL%2BfLEHHQn5zKfp%2BmL7IAYtsnvNA%3D&jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmVsZWFzZS1hc3NldHMuZ2l0aHVidXNlcmNvbnRlbnQuY29tIiwia2V5Ijoia2V5MSIsImV4cCI6MTc3MzkxODEzMSwibmJmIjoxNzczOTE0NTMxLCJwYXRoIjoicmVsZWFzZWFzc2V0cHJvZHVjdGlvbi5ibG9iLmNvcmUud2luZG93cy5uZXQifQ.vRY8W3NrVwpaQGdTNl_eoDfP11a3Mc6Vcytj387g3eM&response-content-disposition=attachment%3B%20filename%3DKoala.Clash_x64-setup.exe&response-content-type=application%2Foctet-stream",
        install_cta="Открыть в Clash",
        instructions=[
            "Установите Koala Clash для Windows.",
            "Нажмите кнопку автонастройки и разрешите открыть приложение.",
            "Включите TUN-режим и активируйте профиль Pineapple VPN.",
        ],
    ),
    "android": PlatformClientInfo(
        platform="android",
        client_type="hiddify",
        client_name=settings.vpn_android_client_name,
        download_url=settings.vpn_android_store_url,
        install_cta="Открыть в Hiddify",
        instructions=[
            "Установите Hiddify на Android.",
            "Нажмите «Открыть в Hiddify» для автоимпорта подписки.",
            "Если автоимпорт не сработал: скопируйте ссылку и в Hiddify выберите Home -> '+' -> Add from clipboard.",
            "Подключите профиль Pineapple VPN.",
        ],
    ),
    "macos": PlatformClientInfo(
        platform="macos",
        client_type="clash",
        client_name="Clash Mi",
        download_url="https://apps.apple.com/ru/app/clash-mi/id6744321968",
        install_cta="Открыть в Clash",
        instructions=[
            "Установите Clash Mi для macOS.",
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
        client_type="clash",
        client_name=settings.vpn_ios_client_name,
        download_url=settings.vpn_ios_appstore_url,
        install_cta="Открыть в Clash Mi",
        instructions=[
            "Установите Clash Mi на iPhone.",
            "Нажмите «Открыть в Clash Mi» или скопируйте ссылку подписки.",
            "В Clash Mi откройте «Мои конфиги» -> «Добавить конфигурационную ссылку».",
            "Вставьте ссылку, обновите подписку и включите VPN-профиль.",
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
