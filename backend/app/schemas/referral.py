from pydantic import BaseModel


class ReferralInfo(BaseModel):
    referral_code: str
    referral_link: str
    commission_percent: int = 10
