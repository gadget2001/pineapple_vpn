from pydantic import BaseModel


class VPNConfigOut(BaseModel):
    uuid: str
    vless_url: str
    subscription_url: str
    subscription_url_clash: str
    subscription_url_v2raytun: str
    raw_vless_url: str
    install_urls: dict[str, str]
    display_title: str
    display_subtitle: str
    reality_public_key: str | None

