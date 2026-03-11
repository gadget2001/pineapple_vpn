from datetime import datetime

from pydantic import BaseModel


class SubscriptionStatus(BaseModel):
    status: str
    plan: str | None
    ends_at: datetime | None
    trial: bool = False
