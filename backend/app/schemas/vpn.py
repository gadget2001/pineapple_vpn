from pydantic import BaseModel


class VPNConfigOut(BaseModel):
    uuid: str
    vless_url: str
    subscription_url: str
    reality_public_key: str | None
