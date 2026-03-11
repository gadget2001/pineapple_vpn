from pydantic import BaseModel


class AdminMetrics(BaseModel):
    users_total: int
    active_subscriptions: int
    revenue_total: int
