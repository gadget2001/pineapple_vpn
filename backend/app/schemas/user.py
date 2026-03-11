from datetime import datetime

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    referral_code: str
    trial_days: int
    created_at: datetime

    class Config:
        from_attributes = True
