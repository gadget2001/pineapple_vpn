from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    amount_rub: int = Field(ge=50, description="Amount in RUB, minimum 50")


class PaymentOut(BaseModel):
    id: int
    amount_rub: int
    status: str
    confirmation_url: str | None = None

    class Config:
        from_attributes = True