from types import SimpleNamespace

from app.services.vpn_subscription import build_clash_subscription


class _Profile(SimpleNamespace):
    pass


def _make_profile(vless_url: str):
    return _Profile(
        raw_vless_url=vless_url,
        vless_url=vless_url,
        display_title="Pineapple VPN",
    )


def test_clash_config_security_none_has_tls_false_only():
    profile = _make_profile(
        "vless://uuid-1@example.com:443?security=none&type=tcp#user"
    )

    cfg = build_clash_subscription(profile)

    assert "tls: false" in cfg
    assert "servername:" not in cfg
    assert "client-fingerprint:" not in cfg
    assert "reality-opts:" not in cfg
    assert "flow:" not in cfg


def test_clash_config_security_reality_has_reality_fields():
    profile = _make_profile(
        "vless://uuid-2@example.com:443?security=reality&type=tcp&sni=domain.tld&pbk=pk123&sid=ab12&flow=xtls-rprx-vision#user"
    )

    cfg = build_clash_subscription(profile)

    assert "tls: true" in cfg
    assert "servername: domain.tld" in cfg
    assert "client-fingerprint: chrome" in cfg
    assert "reality-opts:" in cfg
    assert "public-key: pk123" in cfg
    assert "short-id: ab12" in cfg
    assert "flow: xtls-rprx-vision" in cfg
