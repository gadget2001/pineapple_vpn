from pydantic import BaseModel


class ReferralInfo(BaseModel):
    referral_code: str
    referral_link: str
    bot_deep_link: str
    invite_message: str
    commission_percent: int = 10
