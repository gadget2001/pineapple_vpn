from datetime import datetime

from pydantic import BaseModel


class SubscriptionStatus(BaseModel):
    status: str
    plan: str | None
    ends_at: datetime | None
    trial: bool = False


class SubscriptionPlan(BaseModel):
    code: str
    title: str
    price_rub: int
    duration_days: int


class SubscriptionPurchaseRequest(BaseModel):
    plan: str