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
    template = settings.vpn_profile_name_template or "{brand} - {country}"
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

    security = (query.get("security", [""])[0] or "none").lower()
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
    }


def _build_clash_proxy_block(parsed: dict[str, Any], proxy_name: str) -> list[str]:
    lines = [
        f"  - name: \"{proxy_name}\"",
        "    type: vless",
        f"    server: {parsed['host']}",
        f"    port: {parsed['port']}",
        f"    uuid: {parsed['uuid']}",
        f"    network: {parsed['transport'] or 'tcp'}",
        "    udp: true",
    ]

    if parsed.get("security") == "reality":
        lines.extend(
            [
                "    tls: true",
                f"    servername: {parsed.get('sni') or parsed['host']}",
                "    client-fingerprint: chrome",
                "    reality-opts:",
                f"      public-key: {parsed.get('public_key') or ''}",
                f"      short-id: {parsed.get('short_id') or ''}",
            ]
        )
        if parsed.get("flow"):
            lines.append(f"    flow: {parsed['flow']}")
        return lines

    lines.append("    tls: false")
    return lines


def build_clash_subscription(profile: VPNProfile) -> str:
    raw = _normalize_vless_for_export(profile.raw_vless_url or profile.vless_url)
    parsed = parse_vless(raw)

    proxy_name = f"{settings.vpn_brand_name} {settings.vpn_display_country_name}".strip()
    group_name = (settings.vpn_clash_group_name or settings.vpn_brand_name).strip()
    profile_name = (profile.display_title or render_display_title()).strip()

    nameserver = _split_csv(settings.vpn_primary_dns) or ["77.88.8.8", "1.1.1.1"]
    fallback = _split_csv(settings.vpn_fallback_dns) or ["1.1.1.1", "8.8.8.8"]

    dns_nameserver = "\n".join([f"    - {item}" for item in nameserver])
    dns_fallback = "\n".join([f"    - {item}" for item in fallback])
    proxy_block = "\n".join(_build_clash_proxy_block(parsed, proxy_name))

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
        "  nameserver:\n"
        f"{dns_nameserver}\n"
        "  fallback:\n"
        f"{dns_fallback}\n"
        "  proxy-server-nameserver:\n"
        f"{dns_nameserver}\n"
        "tun:\n"
        "  enable: true\n"
        "  auto-route: true\n"
        "  dns-hijack:\n"
        "    - any:53\n"
        "proxies:\n"
        f"{proxy_block}\n"
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
    raw = _normalize_vless_for_export(profile.raw_vless_url or profile.vless_url)
    if not raw:
        return ""

    lines = [line.strip() for line in raw.splitlines()]
    vless_lines = [line for line in lines if line.startswith("vless://")]

    if vless_lines:
        return "\n".join(vless_lines)
    if raw.startswith("vless://"):
        return raw
    return ""


def default_subscription_for_platform(profile: VPNProfile, platform: str) -> str:
    if (platform or "").strip().lower() == "android":
        return profile.subscription_url_clash or profile.subscription_url
    return profile.subscription_url_clash or profile.subscription_url
