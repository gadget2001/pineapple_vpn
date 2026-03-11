from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inviter_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    invitee_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    commission_percent: Mapped[int] = mapped_column(Integer, default=10)
    total_earned_rub: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
