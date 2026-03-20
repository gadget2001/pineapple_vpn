from types import SimpleNamespace

from app.core.config import settings
from app.services.vpn_clients import platform_client
from app.services.vpn_install import build_android_flclash_install_link, build_deep_link, render_install_landing_html
from app.services.vpn_subscription import default_subscription_for_platform


class _Profile(SimpleNamespace):
    pass


def _make_profile():
    return _Profile(
        subscription_url="https://example.com/sub/default",
        subscription_url_clash="https://example.com/sub/clash",
        subscription_url_hiddify="https://example.com/sub/hiddify",
    )


def test_android_client_is_flclash():
    info = platform_client("android")
    assert info.client_type == "flclash"
    assert "FlClash" in info.client_name
    assert "FlClash" in info.install_cta


def test_build_android_flclash_install_link_uses_configured_template():
    settings.vpn_android_flclash_scheme = "clash://install-config?url={url}"
    link = build_android_flclash_install_link("https://example.com/sub/clash", "Pineapple VPN")
    assert link == "clash://install-config?url=https%3A%2F%2Fexample.com%2Fsub%2Fclash"


def test_android_deep_link_uses_flclash_builder():
    settings.vpn_android_flclash_scheme = "clash://install-config?url={url}"
    link = build_deep_link("android", "https://example.com/sub/clash", "Premium RU")
    assert link == "clash://install-config?url=https%3A%2F%2Fexample.com%2Fsub%2Fclash"


def test_android_subscription_uses_clash_url_as_primary():
    profile = _make_profile()
    assert default_subscription_for_platform(profile, "android") == profile.subscription_url_clash


def test_android_subscription_falls_back_to_default_url():
    profile = _Profile(
        subscription_url="https://example.com/sub/default",
        subscription_url_clash="",
        subscription_url_hiddify="",
    )
    assert default_subscription_for_platform(profile, "android") == profile.subscription_url


def test_android_landing_contains_flclash_fallback_steps():
    html = render_install_landing_html(
        brand="Pineapple VPN",
        platform="android",
        client_name="FlClash",
        deep_link="clash://install-config?url=https%3A%2F%2Fexample.com%2Fsub",
        subscription_url="https://example.com/sub/clash",
        fallback_url="https://example.com/install/fallback",
        title="Pineapple VPN - Russia",
        client_download_url="https://example.com/flclash.apk",
    )

    assert "FlClash" in html
    assert "subscription link" in html


def test_windows_deep_link_remains_clash():
    settings.vpn_clash_scheme = "clash://install-config?url={url}"
    link = build_deep_link("windows", "https://example.com/sub/clash", "Pineapple")
    assert link.startswith("clash://install-config?url=")
