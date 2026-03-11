from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VPNProfile(Base):
    __tablename__ = "vpn_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    uuid: Mapped[str] = mapped_column(String(64))
    vless_url: Mapped[str] = mapped_column(String(512))
    subscription_url: Mapped[str] = mapped_column(String(512))
    reality_public_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="vpn_profile")
