from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConnectionLog(Base):
    __tablename__ = "connection_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)
    panel_username: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(64))
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    source_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_offset: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    event_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    raw_event: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
