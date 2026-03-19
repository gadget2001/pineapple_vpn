from types import SimpleNamespace

from app.core.config import settings
from app.services.vpn_clients import platform_client
from app.services.vpn_install import build_deep_link, build_hiddify_install_link, render_install_landing_html
from app.services.vpn_subscription import default_subscription_for_platform


class _Profile(SimpleNamespace):
    pass


def _make_profile():
    return _Profile(
        subscription_url="https://example.com/sub/default",
        subscription_url_clash="https://example.com/sub/clash",
        subscription_url_hiddify="https://example.com/sub/hiddify",
    )


def test_android_client_is_hiddify():
    info = platform_client("android")
    assert info.client_type == "hiddify"
    assert "Hiddify" in info.client_name
    assert "Hiddify" in info.install_cta


def test_build_hiddify_install_link_uses_official_format():
    settings.vpn_android_hiddify_scheme = "hiddify://import/{url}#{name}"
    link = build_hiddify_install_link("https://example.com/sub/clash", "Pineapple VPN")
    assert link.startswith("hiddify://import/")
    assert "https%3A%2F%2Fexample.com%2Fsub%2Fclash" in link
    assert "#Pineapple%20VPN" in link


def test_android_deep_link_uses_hiddify_builder():
    settings.vpn_android_hiddify_scheme = "hiddify://import/{url}#{name}"
    link = build_deep_link("android", "https://example.com/sub/clash", "Premium RU")
    assert link.startswith("hiddify://import/")
    assert "#Premium%20RU" in link


def test_android_subscription_prefers_hiddify_url():
    profile = _make_profile()
    assert default_subscription_for_platform(profile, "android") == profile.subscription_url_hiddify


def test_android_subscription_falls_back_to_clash_url():
    profile = _Profile(
        subscription_url="https://example.com/sub/default",
        subscription_url_clash="https://example.com/sub/clash",
        subscription_url_hiddify="",
    )
    assert default_subscription_for_platform(profile, "android") == profile.subscription_url_clash


def test_android_landing_contains_hiddify_fallback_steps():
    html = render_install_landing_html(
        brand="Pineapple VPN",
        platform="android",
        client_name="Hiddify",
        deep_link="hiddify://import/example#Pineapple",
        subscription_url="https://example.com/sub/clash",
        fallback_url="https://example.com/install/fallback",
        title="Pineapple VPN • Russia",
        client_download_url="https://play.google.com/store/apps/details?id=app.hiddify.com",
    )

    assert "Add from clipboard" in html
    assert "Add manually" in html
    assert "Открыть в Hiddify" in html


def test_windows_deep_link_remains_clash():
    settings.vpn_clash_scheme = "clash://install-config?url={url}"
    link = build_deep_link("windows", "https://example.com/sub/clash", "Pineapple")
    assert link.startswith("clash://install-config?url=")
