from pydantic import BaseModel


class PaymentCreate(BaseModel):
    plan: str


class PaymentOut(BaseModel):
    id: int
    amount_rub: int
    status: str
    confirmation_url: str | None = None

    class Config:
        from_attributes = True
