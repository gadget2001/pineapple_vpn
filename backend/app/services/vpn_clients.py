from __future__ import annotations

from dataclasses import dataclass, field

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
    download_options: list[dict[str, str]] = field(default_factory=list)


PLATFORM_CLIENTS: dict[str, PlatformClientInfo] = {
    "windows": PlatformClientInfo(
        platform="windows",
        client_type="clash",
        client_name="Koala Clash",
        download_url="https://release-assets.githubusercontent.com/github-production-release-asset/1011075251/eca6652e-716e-42b3-9f98-199855c9df63?sp=r&sv=2018-11-09&sr=b&spr=https&se=2026-03-19T10%3A58%3A22Z&rscd=attachment%3B+filename%3DKoala.Clash_x64-setup.exe&rsct=application%2Foctet-stream&skoid=96c2d410-5711-43a1-aedd-ab1947aa7ab0&sktid=398a6654-997b-47e9-b12b-9515b896b4de&skt=2026-03-19T09%3A57%3A26Z&ske=2026-03-19T10%3A58%3A22Z&sks=b&skv=2018-11-09&sig=j963XNL93sd9qEMHL%2BfLEHHQn5zKfp%2BmL7IAYtsnvNA%3D&jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmVsZWFzZS1hc3NldHMuZ2l0aHVidXNlcmNvbnRlbnQuY29tIiwia2V5Ijoia2V5MSIsImV4cCI6MTc3MzkxODEzMSwibmJmIjoxNzczOTE0NTMxLCJwYXRoIjoicmVsZWFzZWFzc2V0cHJvZHVjdGlvbi5ibG9iLmNvcmUud2luZG93cy5uZXQifQ.vRY8W3NrVwpaQGdTNl_eoDfP11a3Mc6Vcytj387g3eM&response-content-disposition=attachment%3B%20filename%3DKoala.Clash_x64-setup.exe&response-content-type=application%2Foctet-stream",
        install_cta="Открыть в Clash",
        instructions=[
            "Установите Koala Clash для Windows.",
            "Перейдите к следующему шагу для активации ВПН конфигурации.",
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
            "Установите Clash Mi для macOS из AppStore",
            "Перейдите к следующему шагу для активации ВПН конфигурации.",
        ],
    ),
    "linux": PlatformClientInfo(
        platform="linux",
        client_type="clash",
        client_name="Koala Clash",
        download_url="https://github.com/coolcoala/clash-verge-rev-lite/releases/latest",
        install_cta="Открыть в Clash",
        instructions=[
            "Выберите пакет под ваш дистрибутив Linux и архитектуру.",
            "Установите Koala Clash (deb/rpm).",
            "Нажмите автонастройку или импортируйте subscription URL вручную.",
            "Активируйте профиль Pineapple VPN и включите TUN.",
        ],
        download_options=[
            {
                "label": "amd64 (.deb)",
                "url": "https://github.com/coolcoala/clash-verge-rev-lite/releases/latest/download/Koala.Clash_amd64.deb",
            },
            {
                "label": "amd64 (.rpm)",
                "url": "https://github.com/coolcoala/clash-verge-rev-lite/releases/latest/download/Koala.Clash.x86_64.rpm",
            },
            {
                "label": "arm64 (.deb)",
                "url": "https://github.com/coolcoala/clash-verge-rev-lite/releases/latest/download/Koala.Clash_arm64.deb",
            },
            {
                "label": "arm64 (.rpm)",
                "url": "https://github.com/coolcoala/clash-verge-rev-lite/releases/latest/download/Koala.Clash.aarch64.rpm",
            },
        ],
    ),
    "iphone": PlatformClientInfo(
        platform="iphone",
        client_type="clash",
        client_name=settings.vpn_ios_client_name,
        download_url=settings.vpn_ios_appstore_url,
        install_cta="Открыть в Clash Mi",
        instructions=[
            "Установите Clash Mi из AppStore",
            "Перейдите к следующему шагу для активации ВПН конфигурации",
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
