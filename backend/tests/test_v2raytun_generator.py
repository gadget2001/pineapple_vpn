import base64
import json
from datetime import datetime
from types import SimpleNamespace

from app.core.config import settings
from app.services.v2raytun_generator import (
    build_v2raytun_headers,
    build_v2raytun_install_link,
    build_v2raytun_subscription,
)
from app.services.vpn_install import build_deep_link
from app.services.vpn_subscription import default_subscription_for_platform


class _Profile(SimpleNamespace):
    pass


def _make_profile(vless_url: str):
    return _Profile(
        raw_vless_url=vless_url,
        vless_url=vless_url,
        display_title="Pineapple VPN • Russia",
        subscription_url="https://example.com/sub/default",
        subscription_url_clash="https://example.com/sub/clash",
        subscription_url_v2raytun="https://example.com/sub/v2raytun",
    )


def test_v2raytun_subscription_contains_raw_vless():
    profile = _make_profile("vless://uuid-1@example.com:443?security=none&type=tcp#user")
    payload = build_v2raytun_subscription(profile)
    assert payload.startswith("vless://")
    assert "security=none" in payload


def test_v2raytun_headers_have_required_fields():
    profile = _make_profile("vless://uuid-2@example.com:443?security=none&type=tcp#user")
    routing = base64.b64encode(json.dumps({"name": "Pineapple Routing"}).encode("utf-8")).decode("utf-8")
    settings.vpn_v2raytun_routing_base64 = routing

    headers = build_v2raytun_headers(profile=profile, expire_at=datetime(2026, 12, 31))

    assert "profile-title" in headers
    assert "subscription-userinfo" in headers
    assert "profile-update-interval" in headers
    assert "routing" in headers
    assert headers["update-always"] in {"true", "false"}
    assert "total=" in headers["subscription-userinfo"]
    assert "expire=" in headers["subscription-userinfo"]
    assert headers["routing"] == routing


def test_v2raytun_install_link_uses_expected_scheme():
    link = build_v2raytun_install_link("https://example.com/api/vpn/subscription/v2raytun?pid=1&v=1&sig=abc")
    assert link.startswith("v2raytun://import/")
    assert "https%3A%2F%2Fexample.com%2Fapi%2Fvpn%2Fsubscription%2Fv2raytun" in link


def test_iphone_flow_uses_subscription_import_not_raw_json():
    profile = _make_profile("vless://uuid-3@example.com:443?security=none&type=tcp#user")
    deep_link = build_deep_link("iphone", profile.subscription_url_v2raytun)
    assert deep_link.startswith("v2raytun://import/")
    assert "%7B%22" not in deep_link  # no raw JSON payload import


def test_backward_compat_other_platforms_use_clash_subscription():
    profile = _make_profile("vless://uuid-4@example.com:443?security=none&type=tcp#user")
    assert default_subscription_for_platform(profile, "windows") == profile.subscription_url_clash
    assert default_subscription_for_platform(profile, "android") == profile.subscription_url_clash
    assert default_subscription_for_platform(profile, "macos") == profile.subscription_url_clash
    assert default_subscription_for_platform(profile, "linux") == profile.subscription_url_clash
    assert default_subscription_for_platform(profile, "iphone") == profile.subscription_url_v2raytun

