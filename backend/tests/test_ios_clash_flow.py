from types import SimpleNamespace

from app.core.config import settings
from app.services.vpn_clients import platform_client
from app.services.vpn_install import build_deep_link
from app.services.vpn_subscription import default_subscription_for_platform


class _Profile(SimpleNamespace):
    pass


def _make_profile():
    return _Profile(
        subscription_url="https://example.com/sub/default",
        subscription_url_clash="https://example.com/sub/clash",
    )


def test_iphone_client_is_clash_mi():
    info = platform_client("iphone")
    assert info.client_type == "clash"
    assert "Clash" in info.client_name


def test_iphone_uses_clash_subscription_url():
    profile = _make_profile()
    assert default_subscription_for_platform(profile, "iphone") == profile.subscription_url_clash


def test_iphone_install_link_uses_landing_safe_default_when_scheme_not_set():
    profile = _make_profile()
    settings.vpn_ios_install_scheme = ""
    link = build_deep_link("iphone", profile.subscription_url_clash)
    assert link == settings.vpn_ios_appstore_url


def test_iphone_install_link_uses_configured_scheme_when_confirmed():
    profile = _make_profile()
    settings.vpn_ios_install_scheme = "clash://install-config?url={url}"
    link = build_deep_link("iphone", profile.subscription_url_clash)
    assert link.startswith("clash://install-config?url=")
    assert "https%3A%2F%2Fexample.com%2Fsub%2Fclash" in link


def test_other_platforms_unchanged():
    profile = _make_profile()
    assert default_subscription_for_platform(profile, "windows") == profile.subscription_url_clash
    assert default_subscription_for_platform(profile, "android") == profile.subscription_url_clash
    assert default_subscription_for_platform(profile, "macos") == profile.subscription_url_clash
    assert default_subscription_for_platform(profile, "linux") == profile.subscription_url_clash

