from __future__ import annotations

import hashlib
import hmac
from typing import Any
from urllib.parse import parse_qs, urlsplit

from app.core.config import settings
from app.models.vpn_profile import VPNProfile


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def _sign_subscription(pid: int, kind: str, version: int) -> str:
    payload = f"{pid}:{kind}:{version}".encode("utf-8")
    secret = settings.vpn_install_link_signing_secret.encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def verify_subscription_signature(pid: int, kind: str, version: int, signature: str) -> bool:
    expected = _sign_subscription(pid, kind, version)
    return hmac.compare_digest(expected, signature or "")


def resolve_public_base_url() -> str:
    base = (settings.vpn_subscription_base_url or settings.api_base_url or "").strip().rstrip("/")
    return base or "/api"


def build_subscription_url(profile: VPNProfile, kind: str) -> str:
    base = resolve_public_base_url()
    version = int(profile.config_version or 1)
    sig = _sign_subscription(profile.id, kind, version)
    return f"{base}/vpn/subscription/{kind}?pid={profile.id}&v={version}&sig={sig}"


def render_display_title() -> str:
    template = settings.vpn_profile_name_template or "{brand} • {country}"
    title = template.format(
        brand=settings.vpn_brand_name,
        country=settings.vpn_display_country_name,
    ).strip()
    if settings.vpn_enable_emoji_in_profile_names and "[Pineapple]" not in title:
        return f"[Pineapple] {title}"
    return title


def display_subtitle() -> str:
    return f"Premium {settings.vpn_display_country_name}".strip()


def _normalize_vless_for_export(raw: str) -> str:
    return (raw or "").strip()


def parse_vless(vless_url: str) -> dict[str, Any]:
    parsed = urlsplit(vless_url or "")
    query = parse_qs(parsed.query)
    host = parsed.hostname or ""
    port = int(parsed.port or 443)
    uuid = parsed.username or ""
    security = (query.get("security", [""])[0] or "reality").lower()
    transport = (query.get("type", [""])[0] or "tcp").lower()

    return {
        "uuid": uuid,
        "host": host,
        "port": port,
        "transport": transport,
        "security": security,
        "sni": query.get("sni", [""])[0] or query.get("host", [""])[0],
        "short_id": query.get("sid", [""])[0],
        "public_key": query.get("pbk", [""])[0],
        "flow": query.get("flow", [""])[0],
        "fp": query.get("fp", [""])[0] or "chrome",
    }


def build_clash_subscription(profile: VPNProfile) -> str:
    raw = _normalize_vless_for_export(profile.raw_vless_url or profile.vless_url)
    parsed = parse_vless(raw)

    proxy_name = f"{settings.vpn_brand_name} {settings.vpn_display_country_name}".strip()
    group_name = (settings.vpn_clash_group_name or settings.vpn_brand_name).strip()
    profile_name = (profile.display_title or render_display_title()).strip()

    nameserver = _split_csv(settings.vpn_primary_dns) or ["77.88.8.8", "1.1.1.1"]
    fallback = _split_csv(settings.vpn_fallback_dns) or ["1.1.1.1", "8.8.8.8"]

    flow_line = f"    flow: {parsed['flow']}\n" if parsed.get("flow") else ""
    reality_block = ""
    if parsed.get("public_key"):
        reality_block = (
            "    reality-opts:\n"
            f"      public-key: {parsed['public_key']}\n"
            f"      short-id: {parsed.get('short_id') or ''}\n"
        )

    dns_nameserver = "\n".join([f"    - {item}" for item in nameserver])
    dns_fallback = "\n".join([f"    - {item}" for item in fallback])

    return (
        f"# Profile: {profile_name}\n"
        f"mixed-port: {int(settings.vpn_clash_mixed_port)}\n"
        "mode: rule\n"
        "allow-lan: true\n"
        "log-level: info\n"
        "ipv6: false\n"
        "dns:\n"
        "  enable: true\n"
        "  enhanced-mode: fake-ip\n"
        "  listen: 0.0.0.0:1053\n"
        "  default-nameserver:\n"
        f"{dns_nameserver}\n"
        "  nameserver:\n"
        f"{dns_nameserver}\n"
        "  fallback:\n"
        f"{dns_fallback}\n"
        "  proxy-server-nameserver:\n"
        f"{dns_nameserver}\n"
        "tun:\n"
        "  enable: true\n"
        "  stack: system\n"
        "  auto-route: true\n"
        "  auto-detect-interface: true\n"
        "  dns-hijack:\n"
        "    - any:53\n"
        "proxies:\n"
        f"  - name: \"{proxy_name}\"\n"
        "    type: vless\n"
        f"    server: {parsed['host']}\n"
        f"    port: {parsed['port']}\n"
        f"    uuid: {parsed['uuid']}\n"
        f"    network: {parsed['transport'] or 'tcp'}\n"
        "    udp: true\n"
        "    tls: true\n"
        f"    servername: {parsed.get('sni') or parsed['host']}\n"
        "    client-fingerprint: chrome\n"
        f"{flow_line}"
        f"{reality_block}"
        "proxy-groups:\n"
        f"  - name: {group_name}\n"
        "    type: select\n"
        "    proxies:\n"
        f"      - \"{proxy_name}\"\n"
        "      - DIRECT\n"
        "rules:\n"
        f"  - MATCH,{group_name}\n"
    )


def build_hiddify_subscription(profile: VPNProfile) -> str:
    # Hiddify can import a subscription containing one or more raw links.
    title = profile.display_title or settings.vpn_hiddify_profile_name
    raw = _normalize_vless_for_export(profile.raw_vless_url or profile.vless_url)
    return f"# {title}\n{raw}\n"


def default_subscription_for_platform(profile: VPNProfile, platform: str) -> str:
    if platform == "iphone":
        return profile.subscription_url_hiddify or profile.subscription_url
    return profile.subscription_url_clash or profile.subscription_url

