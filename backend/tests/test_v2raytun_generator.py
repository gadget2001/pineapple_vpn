from datetime import datetime
from types import SimpleNamespace

from app.services.v2raytun_generator import (
    build_v2raytun_headers,
    build_v2raytun_install_link,
    build_v2raytun_subscription,
)


class _Profile(SimpleNamespace):
    pass


def _make_profile(vless_url: str):
    return _Profile(
        raw_vless_url=vless_url,
        vless_url=vless_url,
        display_title="Pineapple VPN • Russia",
    )


def test_v2raytun_subscription_contains_raw_vless():
    profile = _make_profile("vless://uuid-1@example.com:443?security=none&type=tcp#user")
    payload = build_v2raytun_subscription(profile)
    assert payload.startswith("vless://")
    assert "security=none" in payload


def test_v2raytun_headers_have_required_fields():
    profile = _make_profile("vless://uuid-2@example.com:443?security=none&type=tcp#user")
    headers = build_v2raytun_headers(profile=profile, expire_at=datetime(2026, 12, 31))

    assert "profile-title" in headers
    assert "subscription-userinfo" in headers
    assert "profile-update-interval" in headers
    assert "routing" in headers
    assert headers["update-always"] in {"true", "false"}
    assert "total=" in headers["subscription-userinfo"]
    assert "expire=" in headers["subscription-userinfo"]


def test_v2raytun_install_link_uses_expected_scheme():
    link = build_v2raytun_install_link("https://example.com/api/vpn/subscription/v2raytun?pid=1&v=1&sig=abc")
    assert link.startswith("v2raytun://import/")
    assert "https%3A%2F%2Fexample.com%2Fapi%2Fvpn%2Fsubscription%2Fv2raytun" in link

