from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from urllib.parse import quote

from app.core.config import settings
from app.models.vpn_profile import VPNProfile
from app.services.vpn_clients import CLASH_PLATFORMS
from app.services.vpn_subscription import default_subscription_for_platform


def _base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _base64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def _sign(payload: str) -> str:
    secret = settings.vpn_install_link_signing_secret.encode("utf-8")
    return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def make_install_token(profile: VPNProfile, platform: str, ttl_seconds: int | None = None) -> str:
    ttl = int(ttl_seconds or settings.vpn_install_link_ttl_seconds or 3600)
    exp = int(time.time()) + max(ttl, 60)
    payload_obj = {
        "pid": profile.id,
        "platform": platform,
        "ver": int(profile.install_link_version or 1),
        "exp": exp,
    }
    payload = _base64url_encode(json.dumps(payload_obj, separators=(",", ":")).encode("utf-8"))
    signature = _sign(payload)
    return f"{payload}.{signature}"


def parse_install_token(token: str) -> dict | None:
    if not token or "." not in token:
        return None
    payload, signature = token.split(".", 1)
    if not hmac.compare_digest(_sign(payload), signature):
        return None
    try:
        data = json.loads(_base64url_decode(payload).decode("utf-8"))
    except Exception:
        return None
    if int(data.get("exp") or 0) < int(time.time()):
        return None
    return data


def _scheme_template(platform: str) -> str:
    if platform == "iphone":
        return (settings.vpn_ios_install_scheme or "").strip()
    if platform == "android":
        return (settings.vpn_android_hiddify_scheme or "").strip()
    if platform == "macos":
        return settings.vpn_macos_clash_scheme
    if platform == "linux":
        return settings.vpn_linux_clash_scheme
    return settings.vpn_clash_scheme


def build_hiddify_install_link(subscription_url: str, profile_name: str) -> str:
    encoded_url = quote(subscription_url, safe="")
    encoded_name = quote(profile_name or settings.vpn_brand_name, safe="")
    template = _scheme_template("android")
    if template:
        return (
            template.replace("{url}", encoded_url)
            .replace("{name}", encoded_name)
        )
    return f"hiddify://import/{encoded_url}#{encoded_name}"


def build_deep_link(platform: str, subscription_url: str, profile_name: str = "") -> str:
    if platform == "android":
        return build_hiddify_install_link(subscription_url, profile_name or settings.vpn_brand_name)
    if platform == "iphone" and not _scheme_template(platform):
        # iOS safe default: do not assume unsupported deep links.
        return settings.vpn_ios_appstore_url
    encoded_url = quote(subscription_url, safe="")
    template = _scheme_template(platform)
    if "{url}" in template:
        return template.replace("{url}", encoded_url)
    if template.endswith("="):
        return f"{template}{encoded_url}"
    return f"{template}{subscription_url}"


def _base_install_url() -> str:
    base = (settings.vpn_install_base_url or settings.vpn_subscription_base_url or settings.api_base_url or "").strip().rstrip("/")
    return base or "/api"


def build_install_open_url(profile: VPNProfile, platform: str) -> str:
    token = make_install_token(profile, platform)
    return f"{_base_install_url()}/install/open?token={token}"


def build_install_fallback_url(token: str) -> str:
    return f"{_base_install_url()}/install/fallback?token={token}"


def build_platform_install_urls(profile: VPNProfile) -> dict[str, str]:
    return {
        "windows": build_install_open_url(profile, "windows"),
        "android": build_install_open_url(profile, "android"),
        "iphone": build_install_open_url(profile, "iphone"),
        "macos": build_install_open_url(profile, "macos"),
        "linux": build_install_open_url(profile, "linux"),
    }


def render_install_landing_html(
    *,
    brand: str,
    platform: str,
    client_name: str,
    deep_link: str,
    subscription_url: str,
    fallback_url: str,
    title: str,
    client_download_url: str = "",
) -> str:
    qr_data = quote(subscription_url, safe="")
    return f"""<!doctype html>
<html lang=\"ru\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{brand} • Настройка VPN</title>
  <style>
    :root {{ --bg: #f8f6ef; --card: #fff; --line: #e9e1c8; --txt: #18301d; --muted: #4f5d52; --acc: #ffaa00; }}
    body {{ margin:0; font-family: Manrope, -apple-system, Segoe UI, sans-serif; background: radial-gradient(circle at 20% 0%, #fff7df, var(--bg)); color:var(--txt); }}
    .wrap {{ max-width: 560px; margin: 0 auto; padding: 24px 14px; }}
    .card {{ background: var(--card); border:1px solid var(--line); border-radius:16px; padding:16px; }}
    h1 {{ margin:0 0 8px; font-size:22px; }}
    p {{ margin:0 0 10px; color:var(--muted); }}
    .badge {{ display:inline-block; border:1px solid #d6e3c7; background:#f5fbef; border-radius:999px; padding:4px 10px; font-size:12px; margin-bottom:10px; }}
    .btn {{ display:block; text-align:center; text-decoration:none; font-weight:700; border-radius:12px; padding:12px; margin-top:8px; }}
    .btn-main {{ background: var(--acc); color:#2b2600; }}
    .btn-soft {{ background:#f3f7ea; border:1px solid #d7e6c6; color:#215729; }}
    .mono {{ width:100%; min-height:80px; border:1px solid #ddd6bf; border-radius:10px; padding:10px; font-size:12px; box-sizing:border-box; }}
    .steps {{ padding-left:18px; margin:10px 0 0; color:var(--muted); }}
    .qr {{ margin-top:10px; text-align:center; }}
    .qr img {{ border:1px solid var(--line); border-radius:8px; background:#fff; padding:6px; }}
  </style>
  <script>
    function copySub() {{
      const el = document.getElementById('sub');
      el.select();
      navigator.clipboard.writeText(el.value);
      alert('Ссылка подписки скопирована');
    }}
    function reopen() {{ window.location.href = '{deep_link}'; }}
    setTimeout(reopen, 350);
  </script>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
      <span class=\"badge\">Профиль готов</span>
      <h1>{brand}</h1>
      <p>{title}</p>
      <p><strong>{platform}</strong> • клиент: {client_name}</p>
      <a class=\"btn btn-main\" href=\"{deep_link}\">Открыть в {client_name}</a>
      {f'<a class=\"btn btn-soft\" href=\"{client_download_url}\">Установить {client_name}</a>' if client_download_url else ''}
      <a class=\"btn btn-soft\" href=\"{fallback_url}\">Открыть fallback-страницу</a>
      <textarea id=\"sub\" class=\"mono\" readonly>{subscription_url}</textarea>
      <a class=\"btn btn-soft\" href=\"javascript:copySub()\">Скопировать ссылку подписки</a>
      <div class=\"qr\"><img alt=\"QR\" src=\"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={qr_data}\"/></div>
      <ol class=\"steps\">
        <li>Установите {client_name}</li>
        {('<li>Откройте Hiddify, нажмите \"+\" и выберите Add from clipboard или Add manually.</li>' if platform == "android" else '<li>Нажмите кнопку открытия приложения</li>')}
        <li>Если автоимпорт не сработал, используйте копирование ссылки или QR-код</li>
      </ol>
    </div>
  </div>
</body>
</html>"""


def target_subscription_url(profile: VPNProfile, platform: str) -> str:
    return default_subscription_for_platform(profile, platform)


def is_deep_link_primary(platform: str) -> bool:
    if platform in CLASH_PLATFORMS:
        return True
    return True
